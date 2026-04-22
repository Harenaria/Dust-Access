import asyncio
import os
from typing import override, Any

from flet import app
from flet.core.column import Column
from flet.core.page import Page
from flet.core.progress_bar import ProgressBar
from flet.core.ref import Ref
from flet.core.snack_bar import SnackBar
from flet.core.text import Text
from flet.core.types import ThemeMode, AppView, FontWeight, MainAxisAlignment, CrossAxisAlignment
from flet.core.view import View

from client_views.fletapp.locals.locale import Locale
from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.locals.en_US import en_US
from client_views.fletapp.views.game_views import BoardView
from client_views.fletapp.views.lobby_views import HomeView, DeployView
from client_views.view_interface import ViewInterface
from core.enums import Actions
from core.game import Game
from networking.utils import CSActions, setup_logging, get_opponent_name


class FletClient(ViewInterface):
    def __init__(self, page:Page, uri: str):
        super().__init__(uri)
        self._page = page
        self.last_lobby_data = {}
        self._last_chose_deck:int|None = None
        self.localization:Locale = en_US
        #UI Setup
        self._page.theme_mode = ThemeMode.DARK
        self._page.bgcolor = AppTheme.COLOR_BG
        self._page.title = "Dust Access"
        self._page.fonts = {
            "Noto Sans": "fonts/NotoSans.ttf",
        }

        # Lifecycle Handlers
        self._page.on_connect = self._handle_reconnection
        self._page.on_disconnect = self._on_browser_close
        self._page.on_route_change = self._route_change
        self._page.on_view_pop = self._view_pop

        self._latest_game_state: Game | None = None

        # VIew injector hooks for dynamic partial view updating.
        self._opponent_name_ref:Ref[Text] = Ref[Text]()


        self._page.views.append(
            View(
                "/",
                [
                    Column(
                        [
                            ProgressBar(width=400),
                            Text("Synchronizing Session...", font_family='Noto Sans', weight=FontWeight.W_200),
                        ],
                        alignment= MainAxisAlignment.CENTER,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    )
                ],
                vertical_alignment=MainAxisAlignment.CENTER,
                horizontal_alignment=CrossAxisAlignment.CENTER,
            )
        )
        self._page.update()

        self._page.run_task(self._initialize_app)

    async def _handle_reconnection(self, e):
        # Use an internal flag to prevent concurrent initialization tasks
        if getattr(self, "_initializing", False):
            return

        if not self.client.running:
            self._initializing = True
            try:
                await self._initialize_app()
            finally:
                self._initializing = False

    async def _initialize_app(self):
        print("[INIT] Syncing state with server...")

        # Restore persistent session
        rid = await self._page.client_storage.get_async("room_name")
        cid = await self._page.client_storage.get_async("client_id")

        if rid and cid:
            self.client.room_name = rid
            self.client.client_id = cid
            is_reconnecting = True
        else:
            is_reconnecting = False

        # START networking (The loop in client_base.py)
        # Note: start() sets self.running = True internally
        self._page.run_task(self.client.start)

        # Handshake Grace Period
        if is_reconnecting:
            # Wait for interpret_message to receive ROOM_JOINED or 3 s timeout
            for _ in range(15):  # 15 * 0.2 = 3 seconds
                if self._page.route != "/": return
                await asyncio.sleep(0.2)

        # Final Fallback
        if self._page.route == "/":
            self._page.go("/home")

    async def _on_browser_close(self, e=None):
        # Wait a few seconds before fully disconnecting the game client.
        # If the user refreshed, 'on_connect' will trigger before this finishes.
        await asyncio.sleep(5)
        if not self.client.connected:
            print("Session truly lost. Cleaning up networking.")
            await self.client.disconnect()

    def _route_change(self, e):
        """
        Standard Flet Router.
        """
        route = self._page.route
        print(f"[ROUTE] Navigating to: {route}")

        self._page.views.clear()
        self._page.bgcolor = AppTheme.COLOR_BG

        # ROUTE: HOME
        if route == "/home" or route == "/":
            self._page.views.append(
                HomeView(self._page,
                         localization=self.localization,
                         on_quick_match=self.search_quick_match,
                         on_create=self.create_private_room,
                         on_join=self.send_join_request)
            )

        # ROUTE: DEPLOY / LOBBY
        elif route == "/deploy":
            current_opp = get_opponent_name(self.last_lobby_data, self.client.client_id)
            deploy_view = DeployView(self._page, localization=self.localization, room_code=self.client.room_name,
                       set_name=self.set_name, set_deck=self.set_deck,
                       set_spec=self.set_spec, on_deploy=self.confirm_ready,
                       on_start_game=self.start_game,
                       opp_ref=self._opponent_name_ref, opp_name=current_opp)
            self._page.views.append(deploy_view)
            # We need to fetch decks immediately
            self._page.run_task(self.get_decks)
        elif route == "/game":
            i = 0
            if self.last_lobby_data and "players" in self.last_lobby_data:
                for p in self.last_lobby_data["players"]:
                    if p["id"] == self.client.client_id:
                        i = p["index"]
                        break
            board_view = BoardView(
                self._page,
                localization=self.localization,
                room_code=self.client.room_name,
                on_action=self.handle_game_action,
                initial_state=self._latest_game_state,
                p_id= i
            )
            self._page.views.append(board_view)

        self._page.update()

    def _view_pop(self, view):
        self._page.views.pop()
        top_view = self._page.views[-1]
        self._page.go(top_view.route)


    async def handle_game_action(self, action: Actions, payload: dict[str, Any]):
        """
        Receives actions and forwards them to the Server.
        """
        print(f"[CONTROLLER] Sending Action: {action.name} | Payload: {payload}")
        # We use the generic send_action from ViewInterface.
        await self.send_action(
            room=self.client.room_name,
            action_type=CSActions.ACTION_EXECUTED,
            game_action=action,
            args=payload
        )

    async def send_join_request(self, room_code: str):
        await self.send_action(room_code, CSActions.JOIN,None, self.client.client_id)
    async def search_quick_match(self, e=None):
        await self.send_action(self.client.room_name, CSActions.QUICK_MATCH, None, None)
    async def create_private_room(self, e=None):
        await self.send_action(self.client.room_name, CSActions.CREATE_ROOM, None, "private")
    async def set_name(self, name: str):
        await self.send_action(self.client.room_name, CSActions.SET_NAME, None, name)
    async def get_decks(self, e=None):
        await self.send_action(self.client.room_name, CSActions.GET_DECK, None, en_US.language)
        return
    async def get_specs(self, deck_id:int):
        await self.send_action(self.client.room_name, CSActions.GET_SPEC, None, deck_id)
    async def set_deck(self, deck_id:int):
        await self.send_action(self.client.room_name, CSActions.SEND_DECK, None, deck_id)
    async def set_spec(self, spec_name:str):
        await self.send_action(self.client.room_name, CSActions.SEND_SPEC, None, spec_name)
    async def confirm_ready(self, e=None):
        await self.send_action(self.client.room_name, CSActions.PLAYER_READY, None, self.client.client_id)
    async def start_game(self, e=None):
        await self.send_action(self.client.room_name, CSActions.START_GAME, None, None)

    async def update_lobby(self, lobby_data):
        self.last_lobby_data = lobby_data
        opp_name = get_opponent_name(lobby_data, self.client.client_id)
        if self._opponent_name_ref.current:
            self._opponent_name_ref.current.value = f"vs. {opp_name}" if opp_name else self.localization['waiting_opponent']
            self._opponent_name_ref.current.update()
        current_view = self._page.views[-1]
        if isinstance(current_view, DeployView):
            current_view.update_lobby_status(lobby_data, self.client.client_id)
    async def update_to_state(self, game_state: Game):
        self._latest_game_state = game_state
        if self._page.route == "/deploy":
            self._page.go("/game")
            return
        if self._page.route == "/game":
            current_view = self._page.views[-1]
            if isinstance(current_view, BoardView):
                current_view.update_game(game_state)
        self._page.update()

    # messages to be processed by this function are:
    # - CSActions.ROOM_JOINED (show room and deck configuration)
    # - CSActions.DECKS_AVAILABLE (to construct deck selection dropdown)
    # - CSActions.DECK_ISVALID (to be received after deck selection)
    # - CSActions.SPECS_AVAILABLE (to construct spec selection dropdown)
    # - CSActions.SPEC_ISVALID (to be received after spec selection)
    async def interpret_message(self, message: dict):
        m_type = CSActions(message.get("type"))
        content = message.get("content")

        match m_type:
            case CSActions.ROOM_JOINED:
                # Save to browser storage for next refresh
                await self._page.client_storage.set_async("room_name", self.client.room_name)
                await self._page.client_storage.set_async("client_id", self.client.client_id)

                # Navigate away from the Loading screen
                self._page.go("/deploy")

            case CSActions.ERROR:
                # If rejoining failed, clear storage and go home
                if self._page.route == "/":
                    await self._page.client_storage.clear_async()
                    self._page.go("/home")
            case CSActions.DECKS_AVAILABLE:
                # Locate the active view and update it with data
                current_view = self._page.views[-1]
                if isinstance(current_view, DeployView):
                    current_view.update_deck_list(content)
            case CSActions.DECK_ISVALID:
                #TODO: Get deck id and check specs available
                await self.get_specs(content)
            case CSActions.SPECS_AVAILABLE:
                # Locate the active view and update it with data
                current_view = self._page.views[-1]
                if isinstance(current_view, DeployView):
                    current_view.update_spec_list(content)
            case CSActions.SPEC_ISVALID:
                current_view = self._page.views[-1]
                if isinstance(current_view, DeployView):
                    current_view.enable_ready_button()
            case _:
                pass
    async def handle_error(self, error: str):
        if error == "RELOAD_REQUIRED":
            print("Protocol mismatch detected. Forcing browser reload...")
            self._page.update()
            return
        elif "no longer exists" in error:
            # Instead of just an error, clear the stale room from storage
                await self._page.client_storage.remove_async("room_name")
                self.client.room_name = None

                self._page.go("/home")

        snack = SnackBar(
            content=Text(error, color=AppTheme.COLOR_FG, font_family='Noto Sans', weight=FontWeight.BOLD),
            bgcolor=AppTheme.RED,  # Changed to RED for better error visibility
            open=True
        )

        self._page.open(snack)
        self._page.update()

    async def show_info(self, info_msg: str): pass

    @override
    async def on_handshake_complete(self, content):
        await super().on_handshake_complete(content)
        # Persistent storage update
        await self._page.client_storage.set_async("client_id", self.client.client_id)
        await self._page.client_storage.set_async("session_secret", self.client.session_secret)

# INIT SCRIPTS
async def start_client(page:Page):
        setup_logging()
        uri = os.getenv("SERVER_URL", "ws://localhost:8765")
        flet_client = FletClient(page, uri)

def app_runner():
    app(target=start_client, view=AppView.WEB_BROWSER, assets_dir=AppTheme.ASSET_DIR)

if __name__ == "__main__":
    app_runner()