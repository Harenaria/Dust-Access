import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any

import pandas as pd

from core.deck import Deck
from core.enums import Counter, CardType
from core.serialization import DataclassJSONCapable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
_SPEC_DB = None


def get_spec_db():
    global _SPEC_DB
    if _SPEC_DB is None:
        path = os.path.join(DATA_DIR, "Specializations.csv")
        if os.path.exists(path):
            _SPEC_DB = pd.read_csv(path, index_col="Name")
    return _SPEC_DB


@dataclass
class Specialization(DataclassJSONCapable):
    name: str
    isBase: bool = False
    accessorClass: str = "Heavy"
    durability: int = 30
    power: int = 0
    efficiency: int = 0
    tenacity: int = 0
    sensitivity: int = 0
    onGameBegins: str = ""

    @classmethod
    def from_name(cls, name: str):
        """Factory to create a Spec object from the CSV database."""
        db = get_spec_db()
        if db is None or name not in db.index:
            # Fallback default
            return cls(name=name)

        row = db.loc[name]
        return cls(
            name=name,
            isBase=bool(row.get('isBase', 0)),
            accessorClass=str(row.get('Class', 'Heavy')),
            durability=int(row.get('Durability', 30)),
            power=int(row.get('Power', 0)),
            efficiency=int(row.get('Efficiency', 0)),
            tenacity=int(row.get('Tenacity', 0)),
            sensitivity=int(row.get('Sensitivity', 0)),
            onGameBegins=str(row.get('OnGameBegins', ""))
        )

@dataclass
class Player(DataclassJSONCapable):
    # --- Fields that must exist in JSON ---
    isFirstPlayer: bool
    accessorName: str
    deck: Deck
    specialization: Specialization

    # Defaults and State
    level: int = 1
    currentHP: int = 30
    currentDurability: int = 30
    currentPower: int = 0
    currentEfficiency: int = 0
    currentTenacity: int = 0
    currentSensitivity: int = 0

    hasTacticalAction: bool = True
    hasCombatAction: bool = True

    hand: list = field(default_factory=list)
    counters: List[Counter] = field(default_factory=list)
    temp_stats: Dict[str, int] = field(default_factory=lambda: {
        'Power': 0, 'Tenacity': 0, 'Efficiency': 0, 'Sensitivity': 0, 'Durability': 0
    })

    pending_discard: int = 0
    choice_pending: bool = False
    choice_candidates: list = field(default_factory=list)
    statuses: List[str] = field(default_factory=list)
    shield_active: bool = False
    deflect_val: int = 0
    tactical_silenced: bool = False
    chainedSkillName: str = ""
    pending_effects: List[Dict[str, Any]] = field(default_factory=list)

    equippedCards: Dict[CardType, Any] = field(default_factory=lambda: {
        CardType.HEAD: None, CardType.CHEST: None, CardType.BRACERS: None, CardType.BOOTS: None,
        CardType.WEAPON: None, CardType.OFF_HAND: None
    })

    skillSlots: list = field(default_factory=lambda: [None] * 4)

    def __post_init__(self):
        """
        Hydration Logic: Converts Dictionaries back into Objects
        when loading from JSON.
        """
        # Hydrate Deck
        if isinstance(self.deck, dict):
            self.deck = Deck(**self.deck)

        # Hydrate Specialization
        if isinstance(self.specialization, dict):
            self.specialization = Specialization(**self.specialization)

        # Hydrate Hand (List of Cards)
        # using the static helper we added to Deck in the previous step
        if self.hand and isinstance(self.hand[0], dict):
            self.hand = [Deck.deserialize_card(c) for c in self.hand]

        # Hydrate Choice Candidates
        if self.choice_candidates and isinstance(self.choice_candidates[0], dict):
            self.choice_candidates = [Deck.deserialize_card(c) for c in self.choice_candidates]

        # Hydrate Equipped Cards
        for slot, card_data in self.equippedCards.items():
            if isinstance(card_data, dict):
                self.equippedCards[slot] = Deck.deserialize_card(card_data)

        # Hydrate Skills
        self.skillSlots = [
            Deck.deserialize_card(c) if isinstance(c, dict) else c
            for c in self.skillSlots
        ]

    @classmethod
    def create_new(cls, isFirstPlayer: bool, accessorName: str, deckID: int, specName: str):
        """
        Factory method to create a NEW player from scratch.
        Replaces the old custom __init__ logic.
        """
        # 1. Load Data
        deck = Deck(deckID)
        spec = Specialization.from_name(specName)

        # 2. Shuffle Deck
        random.shuffle(deck.cards)

        # 3. Instantiate Player with derived stats
        return cls(
            isFirstPlayer=isFirstPlayer,
            accessorName=accessorName,
            deck=deck,
            specialization=spec,
            currentHP=spec.durability,
            currentDurability=spec.durability,
            currentPower=spec.power,
            currentEfficiency=spec.efficiency,
            currentTenacity=spec.tenacity,
            currentSensitivity=spec.sensitivity
        )

    def clone(self):
        new_p = Player(
            isFirstPlayer=self.isFirstPlayer,
            accessorName=self.accessorName,
            deck=self.deck.clone(),
            specialization=self.specialization,
            level=self.level,
            currentHP=self.currentHP,
            currentDurability=self.currentDurability,
            currentPower=self.currentPower,
            currentEfficiency=self.currentEfficiency,
            currentTenacity=self.currentTenacity,
            currentSensitivity=self.currentSensitivity,
            hasTacticalAction=self.hasTacticalAction,
            hasCombatAction=self.hasCombatAction,
            hand=[c.clone() for c in self.hand],
            counters=list(self.counters),
            temp_stats=dict(self.temp_stats),
            pending_discard=self.pending_discard,
            choice_pending=self.choice_pending,
            choice_candidates=[c.clone() for c in self.choice_candidates],
            statuses=list(self.statuses),
            shield_active=self.shield_active,
            deflect_val=self.deflect_val,
            tactical_silenced=self.tactical_silenced,
            chainedSkillName=self.chainedSkillName,
            pending_effects=[dict(e) for e in self.pending_effects],
            equippedCards={k: (v.clone() if v else None) for k, v in self.equippedCards.items()},
            skillSlots=[(s.clone() if s else None) for s in self.skillSlots]
        )
        return new_p