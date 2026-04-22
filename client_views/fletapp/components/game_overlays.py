import asyncio

from flet.core import border
from flet.core.container import Container
from flet.core.column import Column
from flet.core.row import Row
from flet.core.text import Text
from flet.core.stack import Stack
from flet.core import alignment
from flet.core.colors import Colors
from flet.core.types import FontWeight, MainAxisAlignment, CrossAxisAlignment, Padding
from flet.core.text_style import TextStyle
from flet.core.text_button import TextButton
from flet.core.ref import Ref

from client_views.fletapp.apptheme import AppTheme

class LogTicker(Column):
    def __init__(self, on_click=None):
        self.log_text_ref = Ref[Text]()
        super().__init__(
            spacing=5,
            controls=[
                Text("LOG", size=10, weight=FontWeight.W_600, color=AppTheme.COLOR_FG, font_family='Noto Sans'),
                Container(
                    border=border.all(2, AppTheme.COLOR_FG),
                    padding=Padding(10, 8, 10, 8),
                    bgcolor=Colors.with_opacity(0.5, AppTheme.COLOR_BG),
                    on_click=on_click,
                    content=Text(
                        "waiting for server...",
                        ref=self.log_text_ref,
                        size=12,
                        weight=FontWeight.W_400,
                        color=AppTheme.COLOR_FG,
                        font_family='Noto Sans Mono'
                    )
                )
            ]
        )

    def update_log(self, text: str):
        if self.log_text_ref.current:
            self.log_text_ref.current.value = text
            if self.page:
                self.log_text_ref.current.update()

class DamageSplashes(Stack):
    def __init__(self):
        super().__init__(expand=True, controls=[])

    async def show_splash(self, amount: int, is_opponent: bool, page_width: float):
        splash = Text(
            f"-{amount}",
            color=AppTheme.RED,
            size=48,
            weight=FontWeight.W_800,
            font_family='Noto Sans',
            style=TextStyle(height=1),
            top=100 if is_opponent else 400,
            left=page_width / 2 - 20,
            opacity=1,
            animate_opacity=400,
            animate_offset=600,
            offset=(0, 0)
        )
        self.controls.append(splash)
        if self.page:
            self.update()
        
        await asyncio.sleep(0.1)
        splash.opacity = 0
        splash.offset = (0, -2) # Move up
        if self.page:
            splash.update()
        
        await asyncio.sleep(1)
        if splash in self.controls:
            self.controls.remove(splash)
            if self.page:
                self.update()

class ActionAnnouncementOverlay(Container):
    def __init__(self, on_rematch=None, on_leave=None):
        self._on_rematch = on_rematch
        self._on_leave = on_leave
        self.announcement_text_ref = Ref[Text]()
        self._queue = []
        self._is_announcing = False
        self._locked = False

        self.actions_row = Row(
            alignment=MainAxisAlignment.CENTER,
            visible=False,
            spacing=20,
            controls=[
                TextButton(
                    content=Text("REMATCH", size=24, weight=FontWeight.W_600, color=AppTheme.YELLOW),
                    on_click=lambda _: self._on_rematch() if self._on_rematch else None
                ),
                TextButton(
                    content=Text("LEAVE", size=24, weight=FontWeight.W_600, color=AppTheme.COLOR_FG),
                    on_click=lambda _: self._on_leave() if self._on_leave else self.page.go("/home")
                )
            ]
        )

        super().__init__(
            visible=False,
            expand=True,
            bgcolor=Colors.with_opacity(0.8, AppTheme.COLOR_BG),
            alignment=alignment.center,
            content=Column(
                alignment=MainAxisAlignment.CENTER,
                horizontal_alignment=CrossAxisAlignment.CENTER,
                controls=[
                    Text("", ref=self.announcement_text_ref, size=48, weight=FontWeight.W_200, 
                         font_family='Noto Sans', color=AppTheme.COLOR_FG, style=TextStyle(letter_spacing=-1)),
                    self.actions_row
                ],
                spacing=30
            )
        )

    async def announce(self, message: str, persistent: bool = False):
        if self._locked and not persistent: return
        
        if not persistent:
            self._queue.append(message)
            if self._is_announcing: return
            self._is_announcing = True
            
            while self._queue:
                msg = self._queue.pop(0)
                if self.announcement_text_ref.current:
                    self.announcement_text_ref.current.value = msg.lower()
                    self.visible = True
                    if self.page:
                        self.update()
                    await asyncio.sleep(1.2)
                    self.visible = False
                    if self.page:
                        self.update()
                    await asyncio.sleep(0.1)
            
            self._is_announcing = False
        else:
            self._locked = True
            if self.announcement_text_ref.current:
                self.announcement_text_ref.current.value = message.lower()
                self.actions_row.visible = True
                self.visible = True
                if self.page:
                    self.update()
