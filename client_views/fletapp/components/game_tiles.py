#Tile(on_click, text:str, content:str|Icons, color, color1 = None)
from flet.core import alignment, animation
from flet.core.alignment import Alignment
from flet.core.animation import AnimationCurve
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.icon import Icon
from flet.core.icons import Icons
from flet.core.row import Row
from flet.core.stack import Stack
from flet.core.text import Text
from flet.core.text_style import TextOverflow, TextStyle
from flet.core.types import FontWeight, TextAlign, MainAxisAlignment

from client_views.fletapp.apptheme import AppTheme
from core.card import WeaponCard, EquipCard, SkillCard
from core.enums import Stats, CardType

TILE_BASE = 60
SPACING = 4

def _basic_tile(width_units, height_units, bgcolor, content, on_click=None, data=None):
    width = (TILE_BASE * width_units) + (SPACING * (width_units - 1))
    height = (TILE_BASE * height_units) + (SPACING * (height_units - 1))

    return Container(
        width=width,
        height=height,
        bgcolor=bgcolor,
        padding=4,
        on_click=on_click,
        data=data,
        content=content,
        animate_scale=animation.Animation(100, AnimationCurve.EASE_OUT),
    )


def _lbl(text: str, size: int = 9, color: str = AppTheme.COLOR_FG):
    return Text(text.lower(), font_family='Noto Sans', size=size, weight=FontWeight.W_200, color=Colors.with_opacity(0.8, color), no_wrap=True)


def _val(text: str, size: int = 13, color: str = AppTheme.COLOR_FG, weight: FontWeight = FontWeight.BOLD):
    return Text(text, font_family='Noto Sans', size=size, weight=weight, color=color, no_wrap=True, text_align=TextAlign.CENTER)

def WeaponGroup(main: WeaponCard | None, off: EquipCard | None, on_click_main, on_click_off):
    if main:
        is_dual = getattr(main, 'cardType', None) == CardType.DUAL
        w_units = 2 if is_dual else 1
        content = Column(
            alignment=MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                _lbl("WPN", 8),
                _val(main.name, size=11 if is_dual else 10),
                Container(alignment=Alignment(1, 0), content=_lbl(f"{getattr(main, 'AtkStat', 'PWR')}", 8))
            ]
        )
        main_tile = _basic_tile(w_units, 1, AppTheme.RED, content, on_click_main, {"type": "WEAPON", "card": main})
    else:
        main_tile = _basic_tile(1, 1, Colors.with_opacity(0.1, AppTheme.RED),
                                Container(alignment=Alignment(0, 0), content=_lbl("MAIN")), on_click=on_click_main)

    if main and getattr(main, 'cardType', None) == CardType.DUAL:
        return Row([main_tile], spacing=SPACING)

    if off:
        content = Column(alignment=MainAxisAlignment.CENTER, controls=[_lbl("OFF", 8), _val(off.name[:6], 10)])
        off_tile = _basic_tile(1, 1, AppTheme.RED_DARK, content, on_click_off, {"type": "OFFHAND", "card": off})
    else:
        off_tile = _basic_tile(1, 1, Colors.with_opacity(0.1, AppTheme.RED),
                               Container(alignment=Alignment(0, 0), content=_lbl("OFF")), on_click=on_click_off)

    return Row([main_tile, off_tile], spacing=SPACING)

def StatTile(stat:Stats, value:int):
    color:str = AppTheme.PURPLE
    match stat:
        case Stats.POWER:
            color = AppTheme.RED
        case Stats.EFFICIENCY:
            color = AppTheme.BLUE_2
        case Stats.TENACITY:
            color = AppTheme.GREY
        case Stats.SENSITIVITY:
            color = AppTheme.PINK_DARK
        case _:
            color = AppTheme.PURPLE #this should never happen

    icon:Icons = Icons.CIRCLE
    match stat:
        case Stats.POWER:
            icon = Icons.SPORTS_MMA
        case Stats.EFFICIENCY:
            icon = Icons.BOLT_SHARP
        case Stats.TENACITY:
            icon = Icons.SHIELD_SHARP
        case Stats.SENSITIVITY:
            icon = Icons.FACE

    return Container(
        width=42,
        height=42,
        bgcolor=color,
        content=Stack(
            expand=True,
            controls=[
                Container(
                    content=Icon(name=icon,expand=True),
                    opacity=0.3,
                    expand=True,
                    alignment=alignment.center
                ),
                Container(content=Text(value=str(value), font_family='Noto Sans', size=20, weight=FontWeight.W_200,
                                       text_align=TextAlign.LEFT,
                                       no_wrap=True, overflow=TextOverflow.FADE), alignment=alignment.center),
                Container(content=Text(value=stat.name, font_family='Noto Sans', size=8, weight=FontWeight.W_400, text_align=TextAlign.LEFT,
                     no_wrap=True, overflow=TextOverflow.FADE), alignment=alignment.bottom_left),
            ]
        ),
        padding=2
    )

def SkillSlot(index: int, card: SkillCard | None, on_click):
    if card is None:
        content = Container(alignment=Alignment(0, 0), content=_lbl(f"{index + 1}", size=12))
        return _basic_tile(1, 1, Colors.with_opacity(0.05, AppTheme.COLOR_FG), content,
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
                content=Text(str(cooldown) if not is_ready else "R", font_family='Noto Sans', size=10, weight=FontWeight.BOLD,
                             color=AppTheme.YELLOW if not is_ready else AppTheme.COLOR_FG)
            )
        ]
    )

    return _basic_tile(
        1, 1, bg_color, content,
        on_click=on_click,
        data={"type": "SKILL", "index": index, "card": card},
    )

def EquipSlot(slot_type: CardType, card: EquipCard | None, on_click):
    labels = {
        CardType.HEAD: "H",
        CardType.CHEST: "C",
        CardType.BRACERS: "BR",
        CardType.BOOTS: "BT"
    }
    short_lbl = labels.get(slot_type, "?")
    
    if card is None:
        content = Container(alignment=Alignment(0, 0), content=_lbl(short_lbl, size=12))
        return _basic_tile(1, 1, Colors.with_opacity(0.05, AppTheme.BLUE_1), content,
                                on_click=on_click, data={"type": "EQUIP", "slot": slot_type, "card": None})

    content = Column(
        alignment=MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            _lbl(short_lbl, 8),
            _val(card.name[:6], size=10),
            Container() # Spacer
        ]
    )

    return _basic_tile(
        1, 1, AppTheme.BLUE_1, content,
        on_click=on_click,
        data={"type": "EQUIP", "slot": slot_type, "card": card},
    )

def CardTile(card, on_click):
    """
    Tile representing a card in hand.
    Displays: Name, Level, Type, and Key Stat.
    """
    if not card: return Container()
    
    # Extract data
    name = getattr(card, 'name', 'Unknown')
    level = getattr(card, 'level', 0)
    c_type = getattr(card, 'cardType', None)
    
    # Determine Style & Stats based on type
    accent_color = AppTheme.GREY
    type_lbl = "CARD"
    stat_txt = ""
    
    if c_type in [CardType.WEAPON, CardType.DUAL]:
        accent_color = AppTheme.RED
        is_2h = getattr(card, 'is2Handed', False)
        type_lbl = "2H" if is_2h else "WPN"
        atk = getattr(card, 'AtkStat', Stats.POWER)
        coeff = getattr(card, 'AtkCoeff', 1)
        stat_txt = f"{coeff} {atk.name[:3]}"
        
    elif c_type in [CardType.HEAD, CardType.CHEST, CardType.BRACERS, CardType.BOOTS, CardType.OFF_HAND]:
        accent_color = AppTheme.BLUE_1
        type_lbl = "EQP"
        # Find highest stat increase for display
        stats = []
        if getattr(card, 'PowerIncrease', 0): stats.append("PWR")
        if getattr(card, 'TenacityIncrease', 0): stats.append("TEN")
        if getattr(card, 'EfficiencyIncrease', 0): stats.append("EFN")
        if getattr(card, 'SensitivityIncrease', 0): stats.append("SEN")
        
        if len(stats) == 1:
            stat_txt = f"+{stats[0]}"
        elif len(stats) > 1:
            stat_txt = f"+{len(stats)}"
        
    elif c_type in [CardType.SKILL, CardType.INSTANT]:
        accent_color = AppTheme.PURPLE
        is_inst = getattr(card, 'isInstant', False) or c_type == CardType.INSTANT
        type_lbl = "INST" if is_inst else "SKL"
        cd = getattr(card, 'cd', 0)
        stat_txt = f"{cd} CD"
        
    elif c_type == CardType.CANTRIP:
        accent_color = AppTheme.PINK_LIGHT
        type_lbl = "TRICK"
        
    content = Column(
        alignment=MainAxisAlignment.SPACE_BETWEEN,
        spacing=2,
        controls=[
            # Top: Type Marker + Level
            Row(
                alignment=MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                     Container(content=_lbl(type_lbl, size=8, color=accent_color)),
                     _lbl(f"LVL {level}" if level > 0 else "", size=8, color=AppTheme.COLOR_FG)
                ]
            ),
            # Middle: Name
            Text(
                name.lower(), # Metro style: lowercase titles often used
                font_family='Noto Sans',
                size=11, 
                weight=FontWeight.W_400, 
                color=AppTheme.COLOR_FG,
                no_wrap=False, 
                max_lines=2, 
                overflow=TextOverflow.ELLIPSIS,
                style=TextStyle(height=1.1)
            ),
            # Bottom: Stat
            Container(
                alignment=Alignment(1, 0),
                content=Text(stat_txt, font_family='Noto Sans', size=10, weight=FontWeight.BOLD, color=accent_color)
            )
        ]
    )
    
    return Container(
        width=72, # Basic card width
        height=96, # Aspect ratio
        bgcolor=AppTheme.GREY, # Card BG
        padding=6,
        on_click=on_click,
        data={"type": "HAND", "card": card},
        border_radius=0, # Flat
        border=None,
        content=content
    )