from flet.core import border, alignment
from flet.core.box import BoxShape
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.icon import Icon
from flet.core.icons import Icons
from flet.core.row import Row
from flet.core.text import Text
from flet.core.text_style import TextStyle
from flet.core.textfield import TextField, TextCapitalization
from flet.core.padding import Padding
from flet.core.types import FontWeight, CrossAxisAlignment

from client_views.fletapp.apptheme import AppTheme


def StyledTextInput(localization:dict[str,str], on_submit, hint_text_localization_id:str, title_localization_id:str, isCapitalized:bool):
    async def handle_submit(e):
        await on_submit(text_input.value)
    text_input = TextField(
        border_width=3,
        border_color=AppTheme.COLOR_FG,
        cursor_color=AppTheme.COLOR_FG,
        text_style=TextStyle(color=AppTheme.COLOR_FG, size=16, font_family='Noto Sans'),
        content_padding=Padding(10, 5, 10, 5),
        height=36,
        expand=True,
        border_radius=0,
        hint_text=localization[hint_text_localization_id],
        hint_style=TextStyle(color=Colors.with_opacity(0.7, AppTheme.COLOR_FG), size=16, font_family='Noto Sans'),
        capitalization=TextCapitalization.CHARACTERS if isCapitalized else None,
        # Handle "Enter" key press
        on_submit=handle_submit
    )

    action_button = Container(
        width=36,
        height=36,
        border=border.all(3, AppTheme.COLOR_FG),
        shape=BoxShape.CIRCLE,
        alignment=alignment.center,
        content=Icon(
            name=Icons.ARROW_FORWARD,
            color=AppTheme.COLOR_FG,
            expand=True
        ),
        # We make the container clickable
        on_click=handle_submit,
    )

    return Column(
        spacing=10,
        width=300,
        controls=[
            Text(
                localization[title_localization_id],
                size=20,
                font_family='Noto Sans',
                weight=FontWeight.W_600,
                color=AppTheme.COLOR_FG
            ),
            # The Input Row
            Row(
                spacing=15,  # Gap between input and button
                vertical_alignment=CrossAxisAlignment.CENTER,
                controls=[
                    text_input,
                    action_button
                ]
            )
        ]
    )