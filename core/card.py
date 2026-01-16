from dataclasses import dataclass

from core.enums import AccessorClass, CardType, Stats, Scaling
from core.serialization import DataclassJSONCapable


#A card can contain lots of things.
#But we don't want always anything.
#So we define a hierarchy:
# Card
#   |_ SkillCard
#   |_ EquipCard
#       |_ WeaponCard
# That way we make the card easily understandable without having to search for the basic things!


@dataclass  # it gens a default __init__ (+ other cool things like __repr__, a sort of toString) and makes attributes look like... attributes. And that's good!
class Card(DataclassJSONCapable):
    name: str
    Text: str
    Flavor: str

    acClass: AccessorClass
    cardType: CardType
    level: int
    cd: int
    currentCD: int
    OnPlay: list  # List of effect strings (split by ||)
    OnActivate: list  # List of effect strings (split by ||)
    ChoiceLabels: list  # Labels for multi-choice effects (split by ||)
    OnNextTurn: str
    OnNextPlayerTurn: str
    OnRemove: str
    WhileinPlay: str
    Requires: str  # Declarative prerequisites DSL (e.g., "2H", "Equip:OFF_HAND", "UsedAction:Tactical")

    def clone(self):
        import copy
        return copy.copy(self)

    @classmethod
    # @override removed to avoid dependency
    def dict_deserializer(cls, data):
        # Peek at the 'cardType' field in the raw data
        c_type_str = data.get('cardType')

        # Determine the correct subclass
        target_cls = Card
        if c_type_str in [CardType.WEAPON, CardType.DUAL]:
            target_cls = WeaponCard
        elif c_type_str in [CardType.HEAD, CardType.CHEST, CardType.BRACERS, CardType.BOOTS, CardType.OFF_HAND]:
            target_cls = EquipCard
        elif c_type_str in [CardType.SKILL, CardType.INSTANT]:
            target_cls = SkillCard
        elif c_type_str == CardType.CANTRIP:
            target_cls = CantripCard

        # Call the parent implementation, but binding it to the specific subclass
        # This effectively calls WeaponCard.from_dict(data) using the logic we defined in the Mixin
        return super(Card, target_cls).dict_deserializer(data)


@dataclass
class EquipCard(Card):
    DurabilityIncrease:int
    PowerIncrease:int
    EfficiencyIncrease:int
    TenacityIncrease:int
    SensitivityIncrease:int

@dataclass
class WeaponCard(EquipCard):
    is2Handed:bool
    AtkStat:Stats
    AtkFunc:Scaling
    AtkCoeff:int
    OnHit:str
    OnMiss:str

@dataclass
class SkillCard(Card):
    isInstant:bool
    ChainsWith:str
    OnChainActivate: list
    OnHit:str
    OnMiss:str

@dataclass
class CantripCard(Card):
    OnHit:str
    OnMiss:str