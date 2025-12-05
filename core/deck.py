import random
import pandas as pd
from core import card
from core import enums


def validate_deck(deck_id: int):
    """Validates a deck: must have exactly 60 cards and max 3 copies per card.
    Returns (is_valid, error_message) tuple."""
    try:
        df = pd.read_csv(f"./data/{deck_id}.csv")
        if 'in_deck' not in df.columns or 'Name' not in df.columns:
            return False, "Deck file missing required columns"
        
        # Filter out specialization entries (they don't count toward 60 cards)
        loot_cards_df = df[~df['Type'].isin([enums.CardType.BASE, enums.CardType.ADVANCED])]
        
        total_cards = loot_cards_df['in_deck'].sum()
        if total_cards != 60:
            return False, f"Deck must have exactly 60 cards, found {total_cards}"
        
        # Check max 3 copies per card
        max_copies = loot_cards_df['in_deck'].max()
        if max_copies > 3:
            return False, f"Deck has cards with more than 3 copies (max: {max_copies})"
        
        return True, "Valid"
    except Exception as e:
        return False, f"Error validating deck: {e}"


def get_deck_specializations(deck_id: int):
    """Extracts available specializations from a deck file.
    Returns list of specialization names that are marked as available (in_deck > 0)."""
    try:
        df = pd.read_csv(f"./data/{deck_id}.csv")
        
        # Look for specialization entries (Type is "Base", "Advanced", or "SPE")
        spec_df = df[df['Type'].isin(['Base', 'Advanced'])]
        
        # Filter to only those with in_deck > 0 (available)
        available_specs = spec_df[spec_df['in_deck'] > 0]['Name'].tolist()
        
        return available_specs
    except Exception as e:
        # If no specializations found or error, return empty list
        return []


# noinspection PyTypeChecker
class Deck:
    def __init__(self, deckID:int):
        self.cards = list()
        df = pd.read_csv("".join(['./data/', str(deckID), '.csv']))
        df = df.fillna({
            'PowerIncrease': 0,
            'TenacityIncrease': 0,
            'EfficiencyIncrease': 0,
            'SensitivityIncrease': 0,
            'DurabilityIncrease': 0,
            'AtkCoeff': 0,
            'CD': 0,
            'Level': 1,  # Default if empty
            'is2Handed': 0,  # Default 0 (False)
            'Text': '',
            'Flavor': ''
        })

        # Floats to int (we don't need them)
        cols_to_int = ['PowerIncrease', 'TenacityIncrease', 'EfficiencyIncrease',
                       'SensitivityIncrease', 'DurabilityIncrease', 'CD', 'Level']
        for col in cols_to_int:
            if col in df.columns:
                df[col] = df[col].astype(int)

        
        # Filter out specialization entries - they're not part of the loot deck
        loot_df = df[~df['Type'].isin(['Base', 'Advanced', 'SPE'])]
        
        equip_df = loot_df.query('Type == "Head" or Type == "Chest" or Type == "Bracers" or Type == "Boots" or Type == "Off-Hand"', inplace=False)
        weapon_df = loot_df.query('Type == "Weapon" or Type == "Dual"', inplace=False)
        skill_df = loot_df.query('Type == "Skill" or Type == "Instant"', inplace=False)
        cantrip_df = loot_df.query('Type == "Cantrip"', inplace=False)
        for i in range(len(equip_df)):
            for n in range(int(equip_df['in_deck'].iloc[i])):
                self.cards.append(card.EquipCard(
                    equip_df['Name'].iloc[i],
                    equip_df['Text'].iloc[i],
                    equip_df['Flavor'].iloc[i],
                    enums.AccessorClass(equip_df['Class'].iloc[i]),
                    enums.CardType(equip_df['Type'].iloc[i]),
                    equip_df['Level'].iloc[i],
                    equip_df['CD'].iloc[i],
                    equip_df['CD'].iloc[i],
                    equip_df['OnPlay'].iloc[i],
                    equip_df['OnActivate'].iloc[i],
                    equip_df['OnNextTurn'].iloc[i],
                    equip_df['OnNextPlayerTurn'].iloc[i],
                    equip_df['OnRemove'].iloc[i],
                    equip_df['WhileinPlay'].iloc[i],
                    equip_df['DurabilityIncrease'].iloc[i],
                    equip_df['PowerIncrease'].iloc[i],
                    equip_df['EfficiencyIncrease'].iloc[i],
                    equip_df['TenacityIncrease'].iloc[i],
                    equip_df['SensitivityIncrease'].iloc[i],
                ))
        for i in range(len(weapon_df)):
            for n in range(int(weapon_df['in_deck'].iloc[i])):
                self.cards.append(card.WeaponCard(
                    weapon_df['Name'].iloc[i],
                    weapon_df['Text'].iloc[i],
                    weapon_df['Flavor'].iloc[i],
                    enums.AccessorClass(weapon_df['Class'].iloc[i]),
                    enums.CardType(weapon_df['Type'].iloc[i]),
                    weapon_df['Level'].iloc[i],
                    weapon_df['CD'].iloc[i],
                    weapon_df['CD'].iloc[i],
                    weapon_df['OnPlay'].iloc[i],
                    weapon_df['OnActivate'].iloc[i],
                    weapon_df['OnNextTurn'].iloc[i],
                    weapon_df['OnNextPlayerTurn'].iloc[i],
                    weapon_df['OnRemove'].iloc[i],
                    weapon_df['WhileinPlay'].iloc[i],
                    weapon_df['DurabilityIncrease'].iloc[i],
                    weapon_df['PowerIncrease'].iloc[i],
                    weapon_df['EfficiencyIncrease'].iloc[i],
                    weapon_df['TenacityIncrease'].iloc[i],
                    weapon_df['SensitivityIncrease'].iloc[i],
                    weapon_df['is2Handed'].iloc[i],
                    enums.Stats(weapon_df['AtkStat'].iloc[i]),
                    enums.Scaling(weapon_df['AtkFunc'].iloc[i]),
                    weapon_df['AtkCoeff'].iloc[i],
                    weapon_df['OnHit'].iloc[i],
                    weapon_df['OnMiss'].iloc[i]
                ))
        
        for i in range(len(skill_df)):
            isInstant = 1 if (skill_df['Type'].iloc[i] == "Instant") else 0
            for n in range(int(skill_df['in_deck'].iloc[i])):
                self.cards.append(card.SkillCard(
                    skill_df['Name'].iloc[i],
                    skill_df['Text'].iloc[i],
                    skill_df['Flavor'].iloc[i],
                    enums.AccessorClass(skill_df['Class'].iloc[i]),
                    enums.CardType(skill_df['Type'].iloc[i]),
                    skill_df['Level'].iloc[i],
                    skill_df['CD'].iloc[i],
                    skill_df['CD'].iloc[i],
                    skill_df['OnPlay'].iloc[i],
                    skill_df['OnActivate'].iloc[i],
                    skill_df['OnNextTurn'].iloc[i],
                    skill_df['OnNextPlayerTurn'].iloc[i],
                    skill_df['OnRemove'].iloc[i],
                    skill_df['WhileinPlay'].iloc[i],
                    isInstant,
                    skill_df['ChainsWith'].iloc[i],
                    skill_df['OnHit'].iloc[i],
                    skill_df['OnMiss'].iloc[i]
                ))
        for i in range(len(cantrip_df)):
            for n in range(int(cantrip_df['in_deck'].iloc[i])):
                self.cards.append(card.CantripCard(
                    cantrip_df['Name'].iloc[i],
                    cantrip_df['Text'].iloc[i],
                    cantrip_df['Flavor'].iloc[i],
                    enums.AccessorClass(cantrip_df['Class'].iloc[i]),
                    enums.CardType(cantrip_df['Type'].iloc[i]),
                    cantrip_df['Level'].iloc[i],
                    cantrip_df['CD'].iloc[i],
                    cantrip_df['CD'].iloc[i],
                    cantrip_df['OnPlay'].iloc[i],
                    cantrip_df['OnActivate'].iloc[i],
                    cantrip_df['OnNextTurn'].iloc[i],
                    cantrip_df['OnNextPlayerTurn'].iloc[i],
                    cantrip_df['OnRemove'].iloc[i],
                    cantrip_df['WhileinPlay'].iloc[i],
                    cantrip_df['OnHit'].iloc[i],
                    cantrip_df['OnMiss'].iloc[i]
                ))
        
        random.shuffle(self.cards)
        print(len(self.cards))
