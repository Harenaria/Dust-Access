import random
from typing import List

from core.card import Card
from core.deck import Deck
from dataclasses import dataclass
import pandas as pd

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
class Player:
    isFirstPlayer:bool
    deck: Deck
    hand: List[Card]
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
        random.shuffle(self.deck.cards)
        self.currentHP = self.specialization.durability
        self.currentDurability = self.specialization.durability
        self.currentPower = self.specialization.power
        self.currentEfficiency = self.specialization.efficiency
        self.currentTenacity = self.specialization.tenacity
        self.currentSensitivity = self.specialization.sensitivity
        self.hasTacticalAction = True
        self.hasCombatAction = True
