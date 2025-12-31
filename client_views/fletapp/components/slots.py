from flet.core import animation, border
from flet.core.alignment import Alignment
from flet.core.animation import AnimationCurve
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.icon import Icon
from flet.core.icons import Icons
from flet.core.row import Row
from flet.core.text import Text
from flet.core.types import FontWeight, MainAxisAlignment, TextAlign

from client_views.fletapp.apptheme import AppTheme
from core.card import SkillCard, WeaponCard, EquipCard, Card
from core.enums import CardType

# Metro Design Constants
TILE_BASE = 60
SPACING = 4


def _metro_container(width_units, height_units, bgcolor, content, on_click=None, data=None,
                     border_color=Colors.TRANSPARENT, selected=False):
    width = (TILE_BASE * width_units) + (SPACING * (width_units - 1))
    height = (TILE_BASE * height_units) + (SPACING * (height_units - 1))

    # Selection Border Logic
    final_border_color = AppTheme.YELLOW if selected else border_color
    final_border_width = 3 if selected else 2

    return Container(
        width=width,
        height=height,
        bgcolor=bgcolor,
        padding=4,
        on_click=on_click,
        data=data,
        border=border.all(final_border_width, final_border_color) if final_border_color != Colors.TRANSPARENT else None,
        content=content,
        animate_scale=animation.Animation(100, AnimationCurve.EASE_OUT),
        ink=True,
    )


def _lbl(text: str, size: int = 9, color: str = AppTheme.COLOR_FG):
    return Text(text.upper(), size=size, weight=FontWeight.W_300, color=Colors.with_opacity(0.8, color), no_wrap=True)


def _val(text: str, size: int = 13, color: str = AppTheme.COLOR_FG, weight: FontWeight = FontWeight.BOLD):
    return Text(text, size=size, weight=weight, color=color, no_wrap=True, text_align=TextAlign.CENTER)


# --- PUBLIC COMPONENTS ---

def StatTile(label: str, value: int, color: str):
    return Container(
        width=35, height=35,
        bgcolor=Colors.with_opacity(0.2, color),
        border=border.all(1, Colors.with_opacity(0.5, color)),
        content=Column(
            alignment=MainAxisAlignment.CENTER,
            spacing=0,
            controls=[
                Text(str(value), size=12, weight=FontWeight.BOLD, color=AppTheme.COLOR_FG, text_align=TextAlign.CENTER),
                Text(label.upper(), size=6, color=Colors.with_opacity(0.8, AppTheme.COLOR_FG),
                     text_align=TextAlign.CENTER)
            ]
        )
    )


def SkillSlot(index: int, card: SkillCard | None, on_click, selected=False):
    if card is None:
        content = Container(alignment=Alignment(0, 0), content=_lbl(f"{index + 1}", size=12))
        return _metro_container(1, 1, Colors.with_opacity(0.05, AppTheme.COLOR_FG), content, selected=selected,
                                on_click=on_click, data={"index": index, "card": None})

    cooldown = getattr(card, 'current_cooldown', 0) if hasattr(card, 'current_cooldown') else getattr(card, 'currentCD',
                                                                                                      0)
    is_ready = cooldown <= 0
    bg_color = AppTheme.BLUE_2 if is_ready else AppTheme.GREY

    content = Column(
        alignment=MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            Row([_lbl("INSTANT" if getattr(card, 'isInstant', False) else "SKILL", 7)],
                alignment=MainAxisAlignment.SPACE_BETWEEN),
            _val(card.name[:9], size=11),
            Container(
                alignment=Alignment(1, 0),
                content=Text(str(cooldown) if not is_ready else "R", size=10, weight=FontWeight.BOLD,
                             color=AppTheme.YELLOW if not is_ready else AppTheme.COLOR_FG)
            )
        ]
    )

    return _metro_container(
        1, 1, bg_color, content,
        on_click=on_click,
        data={"type": "SKILL", "index": index, "card": card},
        border_color=AppTheme.YELLOW if not is_ready else Colors.TRANSPARENT,
        selected=selected
    )


def EquipSlot(slot_name: str, card: EquipCard | None, on_click, selected=False):
    if card is None:
        content = Container(alignment=Alignment(0, 0), content=_lbl(slot_name[:2]))
        return _metro_container(1, 1, Colors.with_opacity(0.05, AppTheme.COLOR_FG), content)

    content = Column(
        alignment=MainAxisAlignment.CENTER,
        spacing=2,
        controls=[_lbl(slot_name[:3], 7), _val(card.name[:6], size=10)]
    )

    return _metro_container(
        1, 1, AppTheme.PURPLE, content,
        on_click=on_click,
        data={"type": "EQUIP", "slot": slot_name, "card": card},
        selected=selected
    )


def WeaponGroup(main: WeaponCard | None, off: EquipCard | None, on_click_main, on_click_off, selected_main=False,
                selected_off=False):
    # 1. Main Hand
    if main:
        is_dual = getattr(main, 'cardType', None) == CardType.DUAL
        w_units = 2 if is_dual else 1
        content = Column(
            alignment=MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                _lbl("DUAL" if is_dual else "MAIN", 8),
                _val(main.name, size=11 if is_dual else 10),
                Container(alignment=Alignment(1, 0), content=_lbl(f"{getattr(main, 'AtkStat', 'PWR')}", 8))
            ]
        )
        main_tile = _metro_container(w_units, 1, AppTheme.RED, content, on_click_main, {"type": "WEAPON", "card": main},
                                     selected=selected_main)
    else:
        main_tile = _metro_container(1, 1, Colors.with_opacity(0.1, AppTheme.RED),
                                     Container(alignment=Alignment(0, 0), content=_lbl("MAIN")), on_click=on_click_main)

    if main and getattr(main, 'cardType', None) == CardType.DUAL:
        return Row([main_tile], spacing=SPACING)

    # 3. Off Hand
    if off:
        content = Column(alignment=MainAxisAlignment.CENTER, controls=[_lbl("OFF", 8), _val(off.name[:6], 10)])
        off_tile = _metro_container(1, 1, AppTheme.RED_DARK, content, on_click_off, {"type": "OFFHAND", "card": off},
                                    selected=selected_off)
    else:
        off_tile = _metro_container(1, 1, Colors.with_opacity(0.1, AppTheme.RED),
                                    Container(alignment=Alignment(0, 0), content=_lbl("OFF")), on_click=on_click_off)

    return Row([main_tile, off_tile], spacing=SPACING)


def HandCard(index: int, card: Card, on_click, selected=False):
    c_map = {
        CardType.WEAPON: AppTheme.RED, CardType.DUAL: AppTheme.RED,
        CardType.SKILL: AppTheme.BLUE_2, CardType.INSTANT: AppTheme.BLUE_2,
        CardType.CANTRIP: AppTheme.PURPLE
    }
    bg = c_map.get(card.cardType, AppTheme.GREEN_DARK)

    content = Column(
        spacing=0,
        controls=[
            Row([_lbl(f"LVL {card.level}"),
                 Icon(Icons.FLASH_ON if getattr(card, 'isInstant', False) else Icons.CIRCLE, size=8)],
                alignment=MainAxisAlignment.SPACE_BETWEEN),
            Container(expand=True, alignment=Alignment(-1, 0),
                      content=_val(card.name, size=11, weight=FontWeight.NORMAL)),
            _lbl(str(card.cardType.value))
        ]
    )
    # Hand cards are slightly taller (1.3)
    return _metro_container(1.8, 1.3, bg, content, on_click, {"index": index, "card": card}, selected=selected)