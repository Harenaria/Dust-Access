from enum import Enum, StrEnum, auto
#ENUMS
class Phases(Enum):
    SETUP = -1
    START = 0
    LOOT = 1
    PREPARATION = 2
    DUEL = 3
    END = 4

class Actions(Enum):
    PASS_PHASE = auto()
    MULLIGAN = auto()
    DISCARD = auto()
    DRAW = auto()
    PLAY = auto()
    EQUIP = auto()
    ACTIVATE = auto()
    ATTACK = auto()
    END_TURN = auto()

class Winner(Enum):
    NONE = 0
    PLAYER1 = 1
    PLAYER2 = 2
    DRAW = 3
class AccessorClass(StrEnum):
    HEAVY = 'Heavy'
    MEDIUM = 'Medium'
    LIGHT = 'Light'
class CardType(StrEnum):
    BASE = 'Base'
    ADVANCED = 'Advanced'
    WEAPON = 'Weapon'
    DUAL = 'Dual'
    OFF_HAND = 'Off-Hand'
    HEAD = 'Head'
    CHEST = 'Chest'
    BRACERS = 'Bracers'
    BOOTS = 'Boots'
    SKILL = 'Skill'
    INSTANT = 'Instant'
    CANTRIP = 'Cantrip'
class Stats(StrEnum):
    DURABILITY = 'Durability'
    POWER = 'Power'
    EFFICIENCY = 'Efficiency'
    TENACITY = 'Tenacity'
    SENSITIVITY = 'Sensitivity'
class Scaling(StrEnum):
    LINEAR = 'LINEAR'
    MULTIPLICATIVE = 'MULTIPLICATIVE'
class Counter(StrEnum):
    KAI = 'Kai'
    RAGE = 'Rage'
    MOMENTUM = 'Momentum'
#---------------------------