from flet.core import alignment
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.text import Text
from flet.core.text_button import TextButton
from flet.core.text_style import TextStyle
from flet.core.types import FontWeight, MainAxisAlignment, CrossAxisAlignment

from client_views.fletapp.apptheme import AppTheme


def ChoiceModal(title: str, choices: list[str], on_choice, on_dismiss):
    
    def _create_choice_handler(idx):
        return lambda e: on_choice(idx)

    choice_ctls = []
    for i, label in enumerate(choices):
        choice_ctls.append(
            TextButton(
                content=Text(label, font_family='Noto Sans', size=24, weight=FontWeight.W_200, 
                             color=AppTheme.COLOR_FG, style=TextStyle(letter_spacing=-1)),
                on_click=_create_choice_handler(i)
            )
        )

    # Full screen overlay
    return Container(
        expand=True,
        bgcolor=Colors.with_opacity(0.75, AppTheme.COLOR_BG),
        alignment=alignment.center,
        on_click=on_dismiss, # Dismiss if clicking background
        content=Column(
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                Text(title.lower(), font_family='Noto Sans', size=32, weight=FontWeight.W_200, 
                     style=TextStyle(letter_spacing=-1), color=AppTheme.COLOR_FG),
                Column(
                    spacing=10,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    controls=choice_ctls
                )
            ]
        )
    )
