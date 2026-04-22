from flet.core import border
from flet.core.colors import Colors
from flet.core.container import Container
from flet.core.row import Row
from flet.core.text import Text
from flet.core.types import FontWeight, Padding
from client_views.fletapp.apptheme import AppTheme

class CounterBadge(Container):
    def __init__(self, name: str, count: int = 1, is_activable: bool = False, on_click=None):
        label = f"{name.upper()}" if count <= 1 else f"{name.upper()} x{count}"
        color = AppTheme.BLUE_1 if is_activable else AppTheme.YELLOW
        
        super().__init__(
            padding=Padding(4, 2, 4, 2),
            bgcolor=Colors.with_opacity(0.1, color),
            border=border.all(1, color),
            content=Text(label, size=9, weight=FontWeight.W_600, color=color),
            data={"name": name, "is_activable": is_activable},
            on_click=on_click
        )

class EffectRow(Row):
    def __init__(self, statuses: list, counters: list, on_badge_click):
        super().__init__(spacing=5)
        self.on_badge_click = on_badge_click
        self.update_effects(statuses, counters)

    def update_effects(self, statuses: list, counters: list):
        # Unify and aggregate
        effects = {} # name -> count
        
        for s in statuses:
            if not s: continue
            effects[s] = effects.get(s, 0) + 1
            
        for c in counters:
            if not c: continue
            c_name = str(c)
            effects[c_name] = effects.get(c_name, 0) + 1
            
        # Activables
        activables = ["Momentum"]
        
        controls = []
        # Sort by name for stability
        for name in sorted(effects.keys()):
            count = effects[name]
            is_activable = name in activables
            controls.append(CounterBadge(name, count, is_activable, self._on_click_wrapper))
            
        self.controls = controls

    def _on_click_wrapper(self, e):
        if self.on_badge_click:
            self.on_badge_click(e)
