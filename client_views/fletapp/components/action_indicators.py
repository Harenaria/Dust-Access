from flet.core.row import Row
from flet.core.container import Container
from flet.core.icons import Icons
from flet.core.icon import Icon
from client_views.fletapp.apptheme import AppTheme

class ActionIndicators(Row):
    def __init__(self, hasTactical: bool, hasCombat: bool):
        super().__init__()
        self.spacing = 5
        self.vertical_alignment = "center"
        
        self.tactical_icon = Icon(
            name=Icons.BOLT_SHARP,
            size=16,
            color=AppTheme.BLUE_2 if hasTactical else AppTheme.GREY,
            opacity=1.0 if hasTactical else 0.4
        )
        
        self.combat_icon = Icon(
            name=Icons.GAVEL_SHARP,
            size=16,
            color=AppTheme.RED if hasCombat else AppTheme.GREY,
            opacity=1.0 if hasCombat else 0.4
        )
        
        self.controls = [
            Container(content=self.tactical_icon, tooltip="Tactical Action"),
            Container(content=self.combat_icon, tooltip="Combat Action")
        ]

    def update_actions(self, hasTactical: bool, hasCombat: bool):
        self.tactical_icon.color = AppTheme.BLUE_2 if hasTactical else AppTheme.GREY
        self.tactical_icon.opacity = 1.0 if hasTactical else 0.4
        self.combat_icon.color = AppTheme.RED if hasCombat else AppTheme.GREY
        self.combat_icon.opacity = 1.0 if hasCombat else 0.4
        if self.page:
            self.update()
