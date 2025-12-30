from flet.core.colors import Colors
from flet.core.container import Container
from flet.core.text import Text
from flet.core.types import FontWeight
from flet.core.row import Row
from client_views.fletapp.locals.locale import Locale

from client_views.fletapp.apptheme import AppTheme
from core.card import SkillCard, WeaponCard, EquipCard
from core.enums import CardType


def SkillSlot(localization:Locale, slot_index: int, card: SkillCard|None = None):
    index = slot_index + 1
    size = 64
    if card is None:
        return Container(
            width=size,
            height=size,
            bgcolor=Colors.with_opacity(0.3, AppTheme.BLUE_2),
            content= Text(localization['skill']+f" {index}", font_family='Noto Sans', weight=FontWeight.W_200, color=Colors.with_opacity(0.7, AppTheme.COLOR_FG), size=24),
        )
    else:
        #TODO: What is shown by a skill slot?
        return Container(
            width=size,
            height=size,
            bgcolor=Colors.with_opacity(1, AppTheme.BLUE_2)
        )

def WieldSlots(localization:Locale, main_card: WeaponCard = None, off_hand: EquipCard = None):
    size = 64
    if main_card is None:
        main_slot = Container(
            key="weapon_slot",
            width=size,
            height=size,
            bgcolor=Colors.with_opacity(0.3, AppTheme.RED),
            content=Text(localization['weapon'], font_family='Noto Sans', weight=FontWeight.W_400,
                         color=Colors.with_opacity(0.7, AppTheme.COLOR_FG), size=12),
        )
    else:
        main_slot = Container(
            # TODO: What is shown by a equip slot?
            key="weapon_slot",
            width=size,
            height=size,
            bgcolor=Colors.with_opacity(1, AppTheme.RED),
        )
    if off_hand is None:
        off_hand_slot = Container(
            key="off_hand_slot",
            width=size,
            height=size,
            bgcolor=Colors.with_opacity(0.3, AppTheme.RED),
            content=Text(localization['off-hand'], font_family='Noto Sans', weight=FontWeight.W_400,
                         color=Colors.with_opacity(0.7, AppTheme.COLOR_FG), size=12),
        )
    else:
        off_hand_slot = Container(
            key="off_hand_slot",
            width=size,
            height=size,
            bgcolor=Colors.with_opacity(1, AppTheme.RED),
        )
    if main_card and main_card.cardType == CardType.DUAL:
        main_slot.width = size * 2
        return Row(controls=[main_slot])
    else:
        main_slot.width = size
        return Row(controls=[main_slot, off_hand_slot])