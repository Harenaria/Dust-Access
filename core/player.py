import random
from typing import List, Dict

from core.card import Card
from core.deck import Deck
from core.enums import Counter
from dataclasses import dataclass, field
import pandas as pd

from core.serialization import DataclassJSONCapable

SPECIALIZATIONS_DB = pd.read_csv("./data/Specializations.csv", index_col="Name")

@dataclass(init=False)
class Specialization:
    def __init__(self, name: str):
        if name not in SPECIALIZATIONS_DB.index:
            raise ValueError(f"Specialization {name} not found")

        self.name = name
        # Leggi dalla memoria, non dal disco
        self.isBase = SPECIALIZATIONS_DB.loc[name, 'isBase']
        self.accessorClass = SPECIALIZATIONS_DB.loc[name, 'Class']
        self.durability = SPECIALIZATIONS_DB.loc[name, 'Durability']
        self.power = SPECIALIZATIONS_DB.loc[name, 'Power']
        self.efficiency = SPECIALIZATIONS_DB.loc[name, 'Efficiency']
        self.tenacity = SPECIALIZATIONS_DB.loc[name, 'Tenacity']
        self.sensitivity = SPECIALIZATIONS_DB.loc[name, 'Sensitivity']


@dataclass(init=False)
class Player(DataclassJSONCapable):
    isFirstPlayer:bool
    deck: Deck
    hand: List[Card]
    counters: List[Counter]
    accessorName:str
    specialization:Specialization
    level:int
    currentHP:int
    currentDurability:int
    currentPower:int
    currentEfficiency:int
    currentTenacity:int
    currentSensitivity:int
    hasTacticalAction:bool
    hasCombatAction:bool
    temp_stats: Dict[str, int] = field(default_factory=lambda: {
        'Power': 0, 'Tenacity': 0, 'Efficiency': 0, 'Sensitivity': 0
    })
    pending_discard: int = 0
    statuses: List[str] = field(default_factory=list)  # For flags like "Shield", "Kai"
    shield_active: bool = False
    deflect_val: int = 0
    tactical_silenced: bool = False
    def __init__(self, isFirstPlayer:bool, accessorName:str, deckID:int, specName:str):
        self.level = 1
        self.equippedCards = {
            'Head': None,
            'Chest': None,
            'Bracers': None,
            'Boots': None,
            'Weapon': None,
            'Dual': None,
            'Off-Hand': None
        }
        self.skillSlots = [None] * 4
        self.isFirstPlayer = isFirstPlayer
        self.accessorName = accessorName
        self.specialization = Specialization(specName)
        self.deck = Deck(deckID)
        self.hand = list()
        self.counters = list()
        random.shuffle(self.deck.cards)
        self.currentHP = self.specialization.durability
        self.currentDurability = self.specialization.durability
        self.currentPower = self.specialization.power
        self.currentEfficiency = self.specialization.efficiency
        self.currentTenacity = self.specialization.tenacity
        self.currentSensitivity = self.specialization.sensitivity
        self.hasTacticalAction = True
        self.hasCombatAction = True
        self.temp_stats = {'Power': 0, 'Tenacity': 0, 'Efficiency': 0, 'Sensitivity': 0, 'Durability': 0}
        self.pending_discard = 0
        self.statuses = []
        self.shield_active = False
        self.deflect_val = 0
        self.tactical_silenced = False

