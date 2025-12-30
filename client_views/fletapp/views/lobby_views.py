from flet.core import alignment
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.divider import Divider
from flet.core.icons import Icons
from flet.core.page import Page
from flet.core.ref import Ref
from flet.core.row import Row
from flet.core.text import Text
from flet.core.text_button import TextButton
from flet.core.text_style import TextStyle
from flet.core.icon import Icon
from flet.core.types import MainAxisAlignment, CrossAxisAlignment, FontWeight, ScrollMode
from flet.core.view import View

from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.lobby_tiles import DeckTile, SpecTile
from client_views.fletapp.components.styled_text_input import StyledTextInput


#It is stateless, so a function is enough
def HomeView(page: Page, localization: dict[str, str], on_quick_match, on_create, on_join):
    #we define the layouts and populate them here,
    #then we put them together in the return statement
    header = Container(
        height=148,
        content=Row(
            controls=[
                Column(
                    controls=[
                        Text("DUST ACCESS", size=14,
                             color=AppTheme.COLOR_FG, font_family='Noto Sans', weight=FontWeight.W_800, style=TextStyle(height=1)),
                        Text("access", size=72,
                             color=AppTheme.BROWN, font_family='Noto Sans', weight=FontWeight.W_200,
                             style=TextStyle(height=1, letter_spacing=-2)),
                        Text(
                            localization['welcome'], size=36,
                            color=Colors.with_opacity(0.7, AppTheme.COLOR_FG), font_family='Noto Sans',
                            weight=FontWeight.W_200, style=TextStyle(height=1, letter_spacing=-2)
                        ),
                    ],
                    spacing=0,
                    expand=True
                )
            ],
            spacing=0,
            expand=True
        )
    )

    main = Container(
        alignment=alignment.center,
        expand=True,
        content=Column(
            controls=[
                #Image(),
                TextButton(
                    content=Text(
                        localization['quick_match'], size=48,
                        font_family='Noto Sans', weight=FontWeight.W_200
                    ),
                    on_click= on_quick_match,
                ),
                Divider(thickness=1, color=Colors.with_opacity(0.7, AppTheme.COLOR_FG)),
                Container(
                    height=200,
                    content=Column(
                        controls=[
                            TextButton(
                                content=Text(
                                    localization['create_room'], size=48,
                                    font_family='Noto Sans', weight=FontWeight.W_200
                                ),
                                on_click=on_create,
                            ),
                            Text(localization['or'], size=24, font_family='Noto Sans', weight=FontWeight.W_200),
                            StyledTextInput(localization, on_join, 'enter_code', 'join_room', True)
                        ],
                        horizontal_alignment=CrossAxisAlignment.CENTER
                    )
                )
            ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER
        )
    )

    return View(
        route="/home",
        controls=[
            Column(
                expand=True,
                controls=[header, main]
            )
        ]
    )


class DeployView(View):
    def __init__(self, page: Page, localization: dict[str, str], room_code: str, set_name, set_deck,
                 set_spec, on_deploy, on_start_game, opp_ref: Ref[Text], opp_name: str | None = None):
        super().__init__(route="/deploy")
        self._page = page
        self._localization = localization
        self._set_deck = set_deck
        self._set_spec = set_spec
        self._on_deploy = on_deploy
        self._on_start_game = on_start_game
        self.scroll = None

        # --- Header ---
        opponent_text: str = localization['waiting_opponent'] if opp_name is None else f"vs. {opp_name}"
        header = Container(
            height=148,
            content=Row(
                controls=[
                    Column(
                        controls=[
                            Text("LOBBY", size=14, color=AppTheme.COLOR_FG, font_family='Noto Sans',
                                 weight=FontWeight.W_800, style=TextStyle(height=1)),
                            Text(f"{room_code}", size=72, color=AppTheme.BROWN, font_family='Noto Sans',
                                 weight=FontWeight.W_200, style=TextStyle(height=1, letter_spacing=-2)),
                            Text(opponent_text, size=36, ref=opp_ref, color=Colors.with_opacity(0.7, AppTheme.COLOR_FG),
                                 font_family='Noto Sans', weight=FontWeight.W_200,
                                 style=TextStyle(height=1, letter_spacing=-2)),
                        ],
                        spacing=0,
                        expand=True
                    )
                ],
                spacing=0,
                expand=True
            )
        )

        # --- Content Definitions ---
        self._adaptive_deck_list_size = 640
        self.adaptive_deck_list = Row(
            wrap=True,
            alignment=MainAxisAlignment.START,
            run_spacing=10,
            spacing=10,
            controls=[]
        )

        self.deck_section = Column(
            scroll=ScrollMode.AUTO,
            expand=True,
            controls=[
                Text(localization['decks'], font_family='Noto Sans', size=24, weight=FontWeight.W_200),
                self.adaptive_deck_list
            ]
        )

        self.adaptive_spec_list_size = 300

        # The inner list handles its own scrolling
        self.adaptive_spec_list = Column(
            scroll=ScrollMode.AUTO,
            expand=True,
            spacing=2,
            horizontal_alignment=CrossAxisAlignment.CENTER,  # Centers the tiles inside the list
            controls=[]
        )

        # Wrapper handles layout and centering of the input/title
        self.spec_section = Column(
            expand=True,
            spacing=10,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            controls=[
                StyledTextInput(localization, set_name, 'empty', 'accessor_name', False),
                # We wrap the Text in a Row and align it to the left
                Row(
                    controls=[
                        Text(localization['specs'], font_family='Noto Sans', size=24, weight=FontWeight.W_200)
                    ],
                    alignment=MainAxisAlignment.START
                ),
                self.adaptive_spec_list
            ]
        )

        # --- Main Layout ---
        self.main_container = Container(
            expand=True,
            padding=10,
            content=Row()
        )
        dimmed = Colors.with_opacity(0.7, AppTheme.YELLOW)
        self.btn_ready = TextButton(
            content=Row(
                controls=[
                    Text(localization['deploy'], font_family='Noto Sans', size=36, weight=FontWeight.W_400, color=dimmed, style=TextStyle(letter_spacing=-2)),
                    Icon(Icons.CHECK_CIRCLE_OUTLINE_SHARP, color=dimmed, size=36),
                ],
                alignment=MainAxisAlignment.CENTER,
                vertical_alignment=CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            disabled=True,
            on_click=self.on_ready_click
        )

        self.btn_start = TextButton(
            content=Row(
                controls=[
                    Text(localization['start_game'], font_family='Noto Sans', size=36, weight=FontWeight.W_400,
                         color=AppTheme.YELLOW, style=TextStyle(letter_spacing=-2)),
                    Icon(Icons.ARROW_FORWARD, color=AppTheme.YELLOW, size=36),
                ],
                alignment=MainAxisAlignment.CENTER,
                vertical_alignment=CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            visible=False,
            disabled=True,
            on_click=lambda e: self._page.run_task(self._on_start_game)
        )
        # --- Actions ---
        actions = Container(
            content=Column(
                horizontal_alignment=CrossAxisAlignment.STRETCH,
                controls=[
                    Divider(thickness=1, color=AppTheme.COLOR_FG),
                    Row(
                        expand=True,
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                        controls=[self.btn_ready, self.btn_start]
                    )
                ]
            )
        )

        self.controls = [
            Column(
                expand=True,
                horizontal_alignment=CrossAxisAlignment.STRETCH,
                controls=[
                    header,
                    self.main_container,
                    actions
                ]
            )
        ]

        self._page.on_resized = self.handle_resize
        self.handle_resize(None)

    def update_deck_list(self, decks: dict) -> None:
        self.adaptive_deck_list.controls.clear()
        for d_id, d_meta in decks.items():
            tile = DeckTile(deck_id=int(d_id), deck_meta=d_meta,
                            on_click=lambda e, index=int(d_id): self.on_deck_tile_clicked(index))
            self.adaptive_deck_list.controls.append(tile)

        if self.main_container.page:
            self.main_container.update()  # Update the main container to catch all changes

    def on_deck_tile_clicked(self, deck_id):
        print(f"Deck {deck_id} clicked")
        self._page.run_task(self._set_deck, deck_id)

    def on_spec_tile_clicked(self, spec_name):
        print(f"Spec {spec_name} clicked")
        self._page.run_task(self._set_spec, spec_name)

    def update_spec_list(self, specs: dict[str, str]) -> None:
        self.adaptive_spec_list.controls.clear()
        for s_name, s_class in specs.items():
            tile = SpecTile(s_name, s_class, on_click=lambda e, name=s_name: self.on_spec_tile_clicked(name))
            self.adaptive_spec_list.controls.append(tile)

        # Update the container to refresh the layout.
        if self.main_container.page:
            self.main_container.update()

    def enable_ready_button(self):
        """Called when server confirms SPEC_ISVALID"""
        self.btn_ready.disabled = False
        self.btn_ready.content = Row(
            controls=[
                Text("deploy", size=36, font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.YELLOW, style=TextStyle(letter_spacing=-2)),
                Icon(Icons.CHECK_CIRCLE_OUTLINE_SHARP, color=AppTheme.YELLOW, size=36),
            ],
            alignment=MainAxisAlignment.CENTER,
            spacing=4
        )
        self.btn_ready.update()

    def on_ready_click(self, e):
        """Disables button to prevent spam, sends ready signal"""
        dimmed = Colors.with_opacity(0.7, AppTheme.YELLOW)
        self.btn_ready.disabled = True

        # Update content to show the client is waiting for the start of the game
        self.btn_ready.content = Row(
            controls=[
                Text("waiting...", size=36, color=dimmed, font_family='Noto Sans', style=TextStyle(letter_spacing=-2)),
            ],
            alignment=MainAxisAlignment.CENTER,
            spacing=4
        )
        self.btn_ready.update()
        self._page.run_task(self._on_deploy)

    def update_lobby_status(self, lobby_data: dict, my_client_id: str):
        """
        Called when LOBBY_UPDATE arrives.
        Determines if I am host and if the game can start.
        """
        players = lobby_data.get("players", [])

        # Check if I am Host (Index 0 is always host)
        if players and players[0]['id'] == my_client_id:
            self.btn_start.visible = True

            # Check if all players are ready and there are at least 2 players
            all_ready = all(p['ready'] for p in players)
            can_start = len(players) >= 2 and all_ready

            self.btn_start.disabled = not can_start
            self.btn_start.opacity = 1.0 if can_start else 0.7
        else:
            self.btn_start.visible = False

        # Only update the action row if the page is mounted
        if self.btn_start.page:
            self.btn_start.update()

    def handle_resize(self, e):
        threshold = self._adaptive_deck_list_size + self.adaptive_spec_list_size + 50

        if self._page.width < threshold:
            # Narrow Mode
            self.main_container.content = Column(
                expand=True,
                spacing=20,
                horizontal_alignment=CrossAxisAlignment.CENTER,
                controls=[
                    self.deck_section,
                    self.spec_section
                ]
            )
            self.adaptive_deck_list.wrap = True
        else:
            # Wide Mode
            self.main_container.content = Row(
                expand=True,
                alignment=MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=CrossAxisAlignment.START,
                spacing=10,
                controls=[
                    Container(expand=True, content=self.deck_section),
                    Container(width=self.adaptive_spec_list_size, expand=True, content=self.spec_section)
                ]
            )
            self.adaptive_deck_list.wrap = True

        if self.main_container.page:
            self.main_container.update()