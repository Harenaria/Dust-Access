from dataclasses import dataclass

from core.enums import AccessorClass, CardType, Stats, Scaling


#A card can contain lots of things.
#But we don't want always anything.
#So we define a hierarchy:
# Card
#   |_ SkillCard
#   |_ EquipCard
#       |_ WeaponCard
# That way we make the card easily understandable without having to search for the basic things!



@dataclass #it gens a default __init__ (+ other cool things like __repr__, a sort of toString) and makes attributes look like... attributes. And that's good!
class Card:
    name:str
    Text:str
    Flavor:str
    
    acClass:AccessorClass
    cardType:CardType
    level:int
    cd:int
    currentCD:int

    #The next attributes are to be used with: 
    #   gettattr(cardEffects, <attrName>)(<attrValue>)
    #Example:
    #   gettattr(cardEffects, <attrName>)(<attrValue>)
    OnPlay:str
    OnActivate:str
    OnNextTurn:str
    OnNextPlayerTurn:str
    OnRemove:str
    WhileinPlay:str


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
    
    # to use with gettattr(cardEffects, <attrName>)(<attrValue>)
    OnHit:str
    OnMiss:str

@dataclass
class SkillCard(Card):
    isInstant:bool
    ChainsWith:str
    # to use with gettattr(cardEffects, <attrName>)(<attrValue>)
    OnHit:str
    OnMiss:str

@dataclass
class CantripCard(Card):
    # to use with gettattr(cardEffects, <attrName>)(<attrValue>)
    OnHit:str
    OnMiss:str