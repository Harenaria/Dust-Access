import asyncio
from abc import abstractmethod, ABC
from datetime import datetime
from typing import Any

from core.enums import Actions
from core.game import Game
from networking.client_base import WsClient
from networking.utils import CSActions


class ViewInterface(ABC):
    def __init__(self, uri:str):
        self.client = WsClient(uri, self)

    async def send_action(self, room:str, action_type: CSActions, game_action: Actions | None = None, args:Any = None):
        """
        Sends a message to the server. Handles both game moves and simple requests.
        :param room: Room ID. Needed to execute correctly CSActions.JOIN
        :param action_type: The client/server interaction descriptor (e.g., CSActions.ACTION_EXECUTED, CSActions.GET_DECK)
        :param game_action: The game logic action, only required for ACTION_EXECUTED.
        :param args: Optional arguments for the action.
        """

        message: dict[str, Any] = {
            "type": action_type.value,
            "room": room,
            "from": self.client.client_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Logic to include and/or require the 'content' field
        match action_type:
            case CSActions.ACTION_EXECUTED:
                if game_action is None:
                    raise ValueError("ACTION_EXECUTED requires a game_action.")
                message["content"] = (game_action.value, args or {})

            case _:
                # These actions may use the 'content' field as a simple payload (ID, name, etc.)
                message["content"] = args

        await self.client.send_message(message)


    # When a new game state is received, this function is called:
    # the View has to implement their own logic to update the UI
    @abstractmethod
    async def update_to_state(self, game_state:Game):
        """
        messages to be processed by this function are:
            - CSActions.ROOM_JOINED (show room and deck configuration)
            - CSActions.DECKS_AVAILABLE (to construct deck selection dropdown)
            - CSActions.DECK_ISVALID (to be received after deck selection)
            - CSActions.SPECS_AVAILABLE (to construct spec selection dropdown)
            - CSActions.SPEC_ISVALID (to be received after spec selection)
        """
    pass

    @abstractmethod
    async def interpret_message(self, message:dict): pass

    @abstractmethod
    async def handle_error(self, error:str):
        """Player should know that something went wrong"""
        pass

    @abstractmethod
    async def show_info(self, info_msg:str):
        """Show a Toast or any form of feedback"""
        pass

    async def start_client(self):
        # Start receiving messages in another task while continuing execution
        receive_task = asyncio.create_task(self.client.start())
        # Keep running
        await receive_task

    async def on_handshake_complete(self, data: dict):
        """Called by WsClient after a successful handshake."""
        self.client.client_id = data["client_id"]
        self.client.session_secret = data["session_secret"]
        print(f"Handshake successful. ID: {self.client.client_id}")

    @abstractmethod
    async def update_lobby(self, lobby_data: dict[str, Any]):
        """
        :param lobby_data: { "room_id": room_id, "players": []}

        'players' is a list of dicts containing:
            {
                "id": cid,

                "index": i, with 0 = Host, 1 = Challenger

                "name": name,

                "ready": is_ready
            }
        """
        pass