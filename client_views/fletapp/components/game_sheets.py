from flet.core.bottom_sheet import BottomSheet
from flet.core.container import Container
from flet.core.column import Column
from flet.core.row import Row
from flet.core.text import Text
from flet.core.divider import Divider
from flet.core.colors import Colors
from flet.core.text_style import TextStyle
from flet.core.types import FontWeight, ScrollMode, MainAxisAlignment
from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.game_tiles import CardTile

class GameSheet(BottomSheet):
    def __init__(self, title: str, content_controls: list):
        self.title_text = Text(
            title.lower(), 
            font_family='Noto Sans', 
            size=24, 
            weight=FontWeight.W_200, 
            style=TextStyle(letter_spacing=-1), 
            color=AppTheme.COLOR_FG
        )
        self.main_col = Column(
            controls=[
                self.title_text,
                Divider(color=Colors.TRANSPARENT, height=10),
                *content_controls
            ]
        )
        super().__init__(
            content=Container(
                padding=20,
                bgcolor=AppTheme.GREY,
                content=self.main_col
            ),
            dismissible=True
        )

    def set_title(self, title: str):
        self.title_text.value = title.lower()
        if self.page:
            self.title_text.update()

class HandSheet(GameSheet):
    def __init__(self, on_card_click):
        self.hand_row = Row(scroll=ScrollMode.AUTO, spacing=5)
        self.on_card_click = on_card_click
        super().__init__("hand", [self.hand_row])

    def update_hand(self, title: str, cards: list):
        self.set_title(title)
        self.hand_row.controls = [CardTile(c, self.on_card_click) for c in cards]
        if self.page:
            self.hand_row.update()

class DetailSheet(GameSheet):
    def __init__(self):
        self.detail_container = Column(scroll=ScrollMode.AUTO, controls=[], expand=True)
        super().__init__("", [self.detail_container])

    def show_card(self, card):
        self.set_title(card.name)
        
        self.detail_container.controls = [
            Row(alignment=MainAxisAlignment.SPACE_BETWEEN, controls=[
                # Self title is already above
                Container(padding=5, bgcolor=AppTheme.BLUE_1,
                            content=Text(f"LVL {getattr(card, 'level', 1)}", 
                                       font_family='Noto Sans', weight=FontWeight.W_600, size=12))
            ]),
            Divider(),
            Text(getattr(card, 'Text', ''), size=16, font_family='Noto Sans', weight=FontWeight.W_400),
            Text(f"\n{getattr(card, 'Flavor', '')}", size=12, font_family='Noto Sans', weight=FontWeight.W_200,
                    italic=True,
                    color=Colors.with_opacity(0.7, AppTheme.COLOR_FG))
        ]
        if self.page:
            self.detail_container.update()
            self.update()

class LogSheet(GameSheet):
    def __init__(self, logs: list[str]):
        self.log_col = Column(spacing=2, scroll=ScrollMode.AUTO)
        super().__init__("history", [self.log_col])
        self.update_logs(logs)

    def update_logs(self, logs: list[str]):
        self.log_col.controls = [
            Text(
                f"> {msg}", 
                size=12, 
                font_family='Noto Sans Mono', 
                color=AppTheme.COLOR_FG,
                style=TextStyle(height=1.2)
            ) for msg in logs
        ]
        if self.page:
            self.log_col.update()

class DeckSelectionSheet(GameSheet):
    def __init__(self, on_card_click):
        self.on_card_click = on_card_click
        self.cards_row = Row(wrap=True, spacing=10, scroll=ScrollMode.AUTO)
        super().__init__("select a card", [self.cards_row])
        self.dismissible = False

    def update_selection(self, title: str, cards: list):
        self.set_title(title)
        self.cards_row.controls = [
            CardTile(c, self.on_card_click) for c in cards
        ]
        if self.page:
            self.cards_row.update()
