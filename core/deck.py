import random
import pandas as pd
import os
import logging

from pandas import DataFrame
from core import card
from core import enums

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
                'WhileinPlay': ''
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


class Deck:
    def __init__(self, deckID: int):
        self.cards = list()
        self.id = deckID
        db = get_cards_db()
        deck_path = os.path.join(DATA_DIR, f"{deckID}.csv")

        logger.info(f"Building Deck {deckID}...")

        if not os.path.exists(deck_path):
            logger.error(f"Deck file {deck_path} not found.")
            return

        try:
            deck_list_df = pd.read_csv(deck_path)

            if 'isSpec' not in deck_list_df.columns:
                deck_list_df['isSpec'] = 0

            # Conversione sicura a numerico
            deck_list_df['isSpec'] = pd.to_numeric(deck_list_df['isSpec'], errors='coerce').fillna(0).astype(int)

            for _, row in deck_list_df.iterrows():
                if row['isSpec'] == 1:
                    continue

                card_name = row['Name']

                try:
                    in_deck = int(float(row['in_deck']))
                except:
                    in_deck = 1

                if card_name not in db.index:
                    logger.warning(f"Skipping unknown card '{card_name}' in deck {deckID}")
                    continue

                card_data = db.loc[card_name]

                for _ in range(in_deck):
                    try:
                        instance = self._create_card_instance(card_name, card_data)
                        self.cards.append(instance)
                    except Exception as e:
                        logger.error(f"Failed to create card '{card_name}': {e}")

            random.shuffle(self.cards)
            logger.info(f"Deck {deckID} ready: {len(self.cards)} cards.")

        except Exception as e:
            logger.error(f"Critical error building deck {deckID}: {e}")

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
            'OnPlay': safe_str(data.get('OnPlay')),
            'OnActivate': safe_str(data.get('OnActivate')),
            'OnNextTurn': '', 'OnNextPlayerTurn': '', 'OnRemove': '',
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
                OnChainActivate=safe_str(data.get('OnChainActivate')),
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
        df['isSpec'] = pd.to_numeric(df['isSpec'], errors='coerce').fillna(0).astype(int)

        if 'in_deck' not in df.columns or 'Name' not in df.columns:
            return False, "Invalid Format"

        loot_cards = df[df['isSpec'] == 0]
        count = loot_cards['in_deck'].sum()

        if count != 60:
            return False, f"Count {count} != 60"

        return True, "Valid"
    except Exception as e:
        return False, str(e)


def get_deck_base_specializations(deck_id: int):
    try:
        sp = get_base_specializations_db()
        path = os.path.join(DATA_DIR, f"{deck_id}.csv")
        if not os.path.exists(path): return []

        df = pd.read_csv(path)
        specs = []
        for _, row in df.iterrows():
            name = row['Name']
            if name in sp.index:
                specs.append(name)
        return specs
    except:
        return []