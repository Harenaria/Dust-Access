from flet.core import alignment, padding
from flet.core.border_radius import horizontal
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.divider import Divider
from flet.core.page import Page
from flet.core.row import Row
from flet.core.text import Text
from flet.core.text_button import TextButton
from flet.core.text_style import TextStyle
from flet.core.types import MainAxisAlignment, CrossAxisAlignment, FontWeight
from flet.core.view import View

from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.styled_text_input import StyledTextInput


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
                             style=TextStyle(height=1, letter_spacing=-4)),
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
                            StyledTextInput(localization, on_join)
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


def DeployView(page: Page, localization: dict[str, str], room_code: str, set_name, get_decks, set_deck, get_specs, set_spec, on_deploy, opp_name:str|None = None):
    opponent_text:str = localization['waiting_opponent'] if opp_name is None else f"vs. {opp_name}"

    header = Container(
        height=148,
        content=Row(
            controls=[
                Column(
                    controls=[
                        Text("LOBBY", size=14,
                             color=AppTheme.COLOR_FG, font_family='Noto Sans', weight=FontWeight.W_800,
                             style=TextStyle(height=1)),
                        Text(f"{room_code}", size=72,
                             color=AppTheme.BROWN, font_family='Noto Sans', weight=FontWeight.W_200,
                             style=TextStyle(height=1, letter_spacing=-4)),
                        Text(
                            opponent_text, size=36, key="opponent_control",
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
    main = Container()
    actions = Container()
    return View(
        route="/deploy",
        controls=[header, main, actions]
    )
