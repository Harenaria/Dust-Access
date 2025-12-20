from dataclasses import dataclass

from typing_extensions import override

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



@dataclass #it gens a default __init__ (+ other cool things like __repr__, a sort of toString) and makes attributes look like... attributes. And that's good!
class Card(DataclassJSONCapable):
    name:str
    Text:str
    Flavor:str
    
    acClass:AccessorClass
    cardType:CardType
    level:int
    cd:int
    currentCD:int
    OnPlay:str
    OnActivate:str
    OnNextTurn:str
    OnNextPlayerTurn:str
    OnRemove:str
    WhileinPlay:str

    @classmethod
    @override
    def dict_deserializer(cls, data):
        # 1. Peek at the 'cardType' field in the raw data
        c_type_str = data.get('cardType')

        # 2. Determine the correct subclass
        target_cls = Card
        if c_type_str in [CardType.WEAPON, CardType.DUAL]:
            target_cls = WeaponCard
        elif c_type_str in [CardType.SKILL, CardType.INSTANT]:
            target_cls = SkillCard
        # ... etc ...

        # 3. Call the parent implementation, but binding it to the specific subclass
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
    OnChainActivate:str
    OnHit:str
    OnMiss:str

@dataclass
class CantripCard(Card):
    OnHit:str
    OnMiss:str