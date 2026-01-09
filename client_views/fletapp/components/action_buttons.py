from flet.core import border
from flet.core.column import Column
from flet.core.container import Container
from flet.core.icon_button import IconButton
from flet.core.icons import Icons
from flet.core.stack import Stack
from flet.core.text import Text
from flet.core.types import MainAxisAlignment, FontWeight, CrossAxisAlignment

from client_views.fletapp.apptheme import AppTheme


from core.enums import Actions

class ActionButton(Container):
    def __init__(self, on_click, icon:Icons, text:str, action: Actions = None, color=AppTheme.COLOR_FG, cost: str = None):
        super().__init__()
        
        # Indicator for cost
        cost_indicator = None
        if cost == "tactical":
            cost_indicator = Container(width=8, height=8, border_radius=4, bgcolor=AppTheme.BLUE_2, tooltip="Consumes Tactical Action")
        elif cost == "combat":
            cost_indicator = Container(width=8, height=8, border_radius=4, bgcolor=AppTheme.RED, tooltip="Consumes Combat Action")

        self.content = Column(
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=0,
            controls = [
                Stack(
                    controls=[
                        Container(
                            width=48, height=48,
                            border_radius=24,
                            border= border.all(2, color),
                            content=IconButton(
                                expand=True,
                                icon=icon,
                                on_click=on_click,
                                icon_color=color,
                                data=action # Stores the action Enum
                            )
                        ),
                        # Position the cost indicator at the top right of the button
                        Container(content=cost_indicator, top=2, right=2) if cost_indicator else Container()
                    ]
                ),
                Text(text, font_family='Noto Sans', size=12, color=AppTheme.COLOR_FG, weight=FontWeight.W_400)
            ]
        )

class KeepButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.CHECK, "Keep", Actions.PASS_PHASE)
class MulliganButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.SYNC, "Mulligan", Actions.MULLIGAN)

class ShowHandButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.PAN_TOOL, "Hand", None) # UI Action
class PlaceButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.DOWNLOAD, "Place", Actions.PLAY)
class EquipButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.ACCESSIBILITY, "Equip", Actions.EQUIP, cost="tactical")
class CantripButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.WHATSHOT_SHARP, "Cantrip", Actions.PLAY)
class ActivateButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.BOLT_SHARP, "Activate", Actions.ACTIVATE, cost="tactical")
class AttackButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.GAVEL_SHARP, "Attack", Actions.ATTACK, cost="combat")
class PassButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.SKIP_NEXT, "Pass", Actions.PASS_PHASE)
class DiscardButton(ActionButton):
    def __init__(self, on_click):
        super().__init__(on_click, Icons.DELETE_OUTLINE, "Discard", Actions.DISCARD)