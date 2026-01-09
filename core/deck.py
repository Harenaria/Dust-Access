import random
from dataclasses import dataclass, field

import pandas as pd
import os
import logging

from pandas import DataFrame
from core import card
from core import enums
from core.serialization import DataclassJSONCapable

# Logging
logger = logging.getLogger("DeckBuilder")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

_CARDS_DB: DataFrame | None = None
_SPEC_DB: DataFrame | None = None


def get_cards_db() -> pd.DataFrame:
    global _CARDS_DB
    if _CARDS_DB is None:
        path = os.path.join(DATA_DIR, "Cards.csv")
        if not os.path.exists(path):
            logger.error(f"CRITICAL: Cards DB not found at {path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(path)
            df.set_index("Name", inplace=True)

            defaults = {
                'PowerIncrease': 0, 'TenacityIncrease': 0, 'EfficiencyIncrease': 0,
                'SensitivityIncrease': 0, 'DurabilityIncrease': 0, 'AtkCoeff': 0,
                'CD': 0, 'Level': 1, 'is2Handed': 0,
                'Text': '', 'Flavor': '', 'OnPlay': '', 'OnActivate': '',
                'OnHit': '', 'OnMiss': '', 'ChainsWith': '', 'OnChainActivate': '',
                'WhileinPlay': '', 'ChoiceLabels': ''
            }
            df.fillna(defaults, inplace=True)
            _CARDS_DB = df
            logger.info(f"Loaded Cards DB with {len(df)} cards.")
        except Exception as e:
            logger.error(f"Error loading Cards.csv: {e}")
            return pd.DataFrame()

    return _CARDS_DB


def get_specializations_db() -> pd.DataFrame:
    global _SPEC_DB
    if _SPEC_DB is None:
        path = os.path.join(DATA_DIR, "Specializations.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        df.set_index("Name", inplace=True)
        _SPEC_DB = df
    return _SPEC_DB


def get_base_specializations_db() -> pd.DataFrame:
    df = get_specializations_db()
    if df.empty: return df
    return df[df['isBase'] == 1]

@dataclass
class Deck(DataclassJSONCapable):
    id:int
    cards:list = field(default_factory=list)

    def __post_init__(self):
        # If 'cards' is empty, it means we are creating a NEW deck.
        # If 'cards' is NOT empty, it means we are deserializing a saved deck/game,
        # so we skip the CSV building process.
        if not self.cards:
            self._build_from_csv()
        elif self.cards and isinstance(self.cards[0], dict):
            self.cards = [self.deserialize_card(c) for c in self.cards]

    @staticmethod
    def deserialize_card(data: dict):
        """Reconstructs a Card object from a dictionary."""
        # Convert string Enums back to Enum objects
        if 'cardType' in data and isinstance(data['cardType'], str):
            try:
                data['cardType'] = enums.CardType(data['cardType'])
            except ValueError:
                pass  # Keep as string or handle error

        if 'acClass' in data and isinstance(data['acClass'], str):
            try:
                data['acClass'] = enums.AccessorClass(data['acClass'])
            except ValueError:
                pass

        c_type = data.get('cardType')

        # Instantiate based on type
        # Note: We filter kwargs to avoid 'unexpected argument' errors if JSON has extra fields
        try:
            if c_type in [enums.CardType.WEAPON, enums.CardType.DUAL]:
                # Handle nested Enums for Weapons
                if 'AtkStat' in data and isinstance(data['AtkStat'], str): data['AtkStat'] = enums.Stats(
                    data['AtkStat'])
                if 'AtkFunc' in data and isinstance(data['AtkFunc'], str): data['AtkFunc'] = enums.Scaling(
                    data['AtkFunc'])
                return card.WeaponCard(**data)

            elif c_type in [enums.CardType.HEAD, enums.CardType.CHEST, enums.CardType.BRACERS,
                            enums.CardType.BOOTS, enums.CardType.OFF_HAND]:
                return card.EquipCard(**data)

            elif c_type in [enums.CardType.SKILL, enums.CardType.INSTANT]:
                return card.SkillCard(**data)

            elif c_type == enums.CardType.CANTRIP:
                return card.CantripCard(**data)

            elif c_type == enums.CardType.COUNTER:
                return card.Card(**data)

            else:
                return card.Card(**data)
        except TypeError:
            # Fallback if strict typing fails, return generic Card
            return card.Card(**data)


    def _build_from_csv(self):
        # Converting DataFrame to Dictionary once for O(1) lookup and correct typing
        db_df = get_cards_db()
        cards_library = db_df.to_dict(orient='index')

        deck_path = os.path.join(DATA_DIR, f"{self.id}.csv")

        logger.info(f"Building Deck {self.id}...")

        if not os.path.exists(deck_path):
            logger.error(f"Deck file {deck_path} not found.")
            return

        try:
            deck_list_df = pd.read_csv(deck_path)

            if 'isSpec' not in deck_list_df.columns:
                deck_list_df['isSpec'] = 0

            deck_list_df['isSpec'] = pd.to_numeric(deck_list_df['isSpec'].fillna(0), errors='coerce').astype(int)

            for _, row in deck_list_df.iterrows():
                if row['isSpec'] == 1:
                    continue

                card_name = row['Name']

                try:
                    in_deck = int(float(row['in_deck']))
                except:
                    in_deck = 1

                card_data = cards_library.get(card_name)

                if not card_data:
                    logger.warning(f"Skipping unknown card '{card_name}' in deck {self.id}")
                    continue

                for _ in range(in_deck):
                    try:
                        instance = self._create_card_instance(card_name, card_data)
                        self.cards.append(instance)
                    except Exception as e:
                        logger.error(f"Failed to create card '{card_name}': {e}")

            random.shuffle(self.cards)
            logger.info(f"Deck {self.id} ready: {len(self.cards)} cards.")

        except Exception as e:
            logger.error(f"Critical error building deck {self.id}: {e}")

    @staticmethod
    def _create_card_instance(name, data):
        def safe_int(val, default=0):
            try:
                return int(float(val))
            except:
                return default

        def safe_str(val):
            if pd.isna(val): return ""
            return str(val)

        def safe_list(val, separator='||'):
            """Parse ||-separated string into list of effects"""
            if pd.isna(val) or not val:
                return []
            s = str(val).strip()
            if not s:
                return []
            return [part.strip() for part in s.split(separator) if part.strip()]

        try:
            c_type = enums.CardType(data['Type'])
        except:
            c_type = enums.CardType.BASE

        try:
            c_class = enums.AccessorClass(data['Class'])
        except:
            c_class = enums.AccessorClass.HEAVY

        base_args = {
            'name': name,
            'Text': safe_str(data.get('Text')),
            'Flavor': safe_str(data.get('Flavor')),
            'acClass': c_class,
            'cardType': c_type,
            'level': safe_int(data.get('Level'), 1),
            'cd': safe_int(data.get('CD'), 0),
            'currentCD': 0,
            'OnPlay': safe_list(data.get('OnPlay')),
            'OnActivate': safe_list(data.get('OnActivate')),
            'ChoiceLabels': safe_list(data.get('ChoiceLabels')),
            'OnNextTurn': safe_str(data.get('OnNextTurn')),
            'OnNextPlayerTurn': safe_str(data.get('OnNextPlayerTurn')),
            'OnRemove': safe_str(data.get('OnRemove')),
            'WhileinPlay': safe_str(data.get('WhileinPlay'))
        }

        equip_args = {
            'DurabilityIncrease': safe_int(data.get('DurabilityIncrease')),
            'PowerIncrease': safe_int(data.get('PowerIncrease')),
            'EfficiencyIncrease': safe_int(data.get('EfficiencyIncrease')),
            'TenacityIncrease': safe_int(data.get('TenacityIncrease')),
            'SensitivityIncrease': safe_int(data.get('SensitivityIncrease')),
        }

        if c_type in [enums.CardType.WEAPON, enums.CardType.DUAL]:
            try:
                stat = enums.Stats(data.get('AtkStat'))
            except:
                stat = enums.Stats.POWER
            try:
                func = enums.Scaling(data.get('AtkFunc'))
            except:
                func = enums.Scaling.LINEAR

            return card.WeaponCard(
                **base_args, **equip_args,
                is2Handed=(c_type == enums.CardType.DUAL),
                AtkStat=stat,
                AtkFunc=func,
                AtkCoeff=safe_int(data.get('AtkCoeff')),
                OnHit=safe_str(data.get('OnHit')),
                OnMiss=safe_str(data.get('OnMiss'))
            )

        elif c_type in [enums.CardType.HEAD, enums.CardType.CHEST, enums.CardType.BRACERS,
                        enums.CardType.BOOTS, enums.CardType.OFF_HAND]:
            return card.EquipCard(**base_args, **equip_args)

        elif c_type in [enums.CardType.SKILL, enums.CardType.INSTANT]:
            return card.SkillCard(
                **base_args,
                isInstant=(c_type == enums.CardType.INSTANT),
                ChainsWith=safe_str(data.get('ChainsWith')),
                OnChainActivate=safe_list(data.get('OnChainActivate')),
                OnHit=safe_str(data.get('OnHit')),
                OnMiss=safe_str(data.get('OnMiss'))
            )

        elif c_type == enums.CardType.CANTRIP:
            return card.CantripCard(
                **base_args,
                OnHit=safe_str(data.get('OnHit')),
                OnMiss=safe_str(data.get('OnMiss'))
            )

        else:
            return card.Card(**base_args)


def validate_deck(deck_id: int) -> tuple[bool, str]:
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, f"{deck_id}.csv"))

        if 'isSpec' not in df.columns: df['isSpec'] = 0
        df['isSpec'] = pd.to_numeric(df['isSpec'].fillna(0), errors='coerce').astype(int)

        if 'in_deck' not in df.columns or 'Name' not in df.columns:
            return False, "Invalid Format"

        loot_cards = df[df['isSpec'] == 0]
        count = loot_cards['in_deck'].sum()

        if count != 60:
            return False, f"Count {count} != 60"

        return True, "Valid"
    except Exception as e:
        return False, str(e)


def get_deck_base_specializations(deck_id: int) -> dict[str, str] | None:
    try:
        # Load the Global Specializations DB
        sp = get_base_specializations_db()
        if 'Name' in sp.columns:
            sp = sp.set_index('Name')

        # Load the Deck CSV
        path = os.path.join(DATA_DIR, f"{deck_id}.csv")
        if not os.path.exists(path):
            return None

        df = pd.read_csv(path)

        # Filter the DECK to find only rows where isSpec == 1
        # We fillna(0) to handle empty fields safely before comparing
        deck_specs = df[df['isSpec'].fillna(0) == 1]['Name']

        # Use the list of names from the deck to filter the global DB
        valid_specs = sp[sp.index.isin(deck_specs)]

        return valid_specs['Class'].to_dict()

    except Exception as e:
        print(f"Error loading specs for deck {deck_id}: {e}")
        return None