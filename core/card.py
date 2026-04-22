from dataclasses import dataclass, field
from typing import Set

from core.enums import AccessorClass, CardType, Stats, Scaling, CardTag
from core.serialization import DataclassJSONCapable


#A card can contain lots of things.
#But we don't want always anything.
#So we define a hierarchy:
# Card
#   |_ SkillCard
#   |_ EquipCard
#       |_ WeaponCard
# That way we make the card easily understandable without having to search for the basic things!


@dataclass(kw_only=True)
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
    tags: Set[CardTag] = field(default_factory=set)
    called_methods: Set[str] = field(default_factory=set)



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

    def compute_tags(self):
        """Categorizes a card into functional tags by analyzing its effects and attributes."""
        self.tags = set()
        self.called_methods = set()
        
        # 1. Gather all effect strings from all possible fields
        all_effect_lists = [
            getattr(self, 'OnPlay', []),
            getattr(self, 'OnActivate', []),
            getattr(self, 'OnChainActivate', [])
        ]
        if hasattr(self, 'OnHit'): all_effect_lists.append([getattr(self, 'OnHit', '')])
        
        all_effects = []
        for item in all_effect_lists:
            if isinstance(item, list):
                all_effects.extend([str(e) for e in item if e])
            elif isinstance(item, str) and item:
                all_effects.append(item)

        # 2. Extract methods being called to avoid matching flavor text or random keywords
        for effect in all_effects:
            if '(' in effect:
                method = effect.split('(', 1)[0].strip()
                self.called_methods.add(method)

        # GENERATOR: Produces resources
        if "playCounter" in self.called_methods:
            # We could check specifically for Rage/Kai here if needed,
            # but usually playing counters is a generative/scaling action.
            self.tags.add(CardTag.GENERATOR)
        if any(m in self.called_methods for m in ["DrawThenDiscard", "ifUsedBonusRegain", "DrawFromDeck", "LearnFromDeck"]):
            self.tags.add(CardTag.GENERATOR)
        
        # CONSUMER: Usually weapons or cards with offensive scaling
        if hasattr(self, 'AtkStat'):
            self.tags.add(CardTag.CONSUMER)
            
        # FINISHER: High level or destructive effects
        if self.level >= 5:
            self.tags.add(CardTag.FINISHER)
        if "Damage" in self.called_methods:
            self.tags.add(CardTag.FINISHER) # Primary damage source
            
        # DEFENSIVE: Survival effects
        if any(m in self.called_methods for m in ["HealSelf", "Shield", "Cover", "Deflect"]):
            self.tags.add(CardTag.DEFENSIVE)
            
        # COUNTER: Disruption
        if any(m in self.called_methods for m in ["SkullSplitter", "NullifyFirstAction", "removeAllCounters"]):
            self.tags.add(CardTag.COUNTER)
            
        # SCALER: Stat increases
        # Check attributes first (Equipment)
        inc_stats = ['PowerIncrease', 'TenacityIncrease', 'EfficiencyIncrease', 'SensitivityIncrease', 'DurabilityIncrease']
        if any(getattr(self, s, 0) > 0 for s in inc_stats):
            self.tags.add(CardTag.SCALER)
        if "TempStat" in self.called_methods:
            self.tags.add(CardTag.SCALER)
            
        # COMBO: Synergistic cards
        if getattr(self, 'ChainsWith', None) or "checkEquipSet" in self.called_methods:
            self.tags.add(CardTag.COMBO)


@dataclass(kw_only=True)
class EquipCard(Card):
    DurabilityIncrease:int
    PowerIncrease:int
    EfficiencyIncrease:int
    TenacityIncrease:int
    SensitivityIncrease:int
    


@dataclass(kw_only=True)
class WeaponCard(EquipCard):
    is2Handed:bool
    AtkStat:Stats
    AtkFunc:Scaling
    AtkCoeff:int
    OnHit:str
    OnMiss:str
    


@dataclass(kw_only=True)
class SkillCard(Card):
    isInstant:bool
    ChainsWith:str
    OnChainActivate: list
    OnHit:str
    OnMiss:str
    


@dataclass(kw_only=True)
class CantripCard(Card):
    OnHit:str
    OnMiss:str