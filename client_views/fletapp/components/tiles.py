from flet.core import alignment
from flet.core.column import Column
from flet.core.container import Container
from flet.core.icons import Icons
from flet.core.icon import Icon
from flet.core.image import Image
from flet.core.text import Text
from flet.core.text_style import TextOverflow
from flet.core.types import FontWeight, MainAxisAlignment, TextAlign, CrossAxisAlignment

from client_views.fletapp.apptheme import AppTheme


def Tile(on_click, text:str, content:str|Icons, color, color1 = None):
    if isinstance(content, Icons):
        main_element = Icon(name=content, size=48, color= AppTheme.COLOR_FG)
    elif isinstance(content, str):
        main_element = Image(src=content)
    else:
        main_element = None


    return Container(
        width=96,
        height=96,
        bgcolor=color, #TODO: What should happen with color1?
        on_click=on_click,
        #TODO: Substitute Column with Stack to center Icon or put Image on tile start
        content=Column(
            expand= True,
            spacing= 0,
            alignment= MainAxisAlignment.END,
            horizontal_alignment= CrossAxisAlignment.START,
            controls= [
                Container(
                    content=main_element,
                    expand= True,
                    alignment= alignment.center
                ),
                Text(value=text, font_family='Noto Sans', size=14, weight=FontWeight.W_400, text_align=TextAlign.LEFT, no_wrap=True, overflow=TextOverflow.ELLIPSIS),
            ]
        ),
        padding=2
    )