import json
import os
import sys

import pandas as pd

from core.deck import get_deck_base_specializations
from networking.utils import logger

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Used to read deck/spec data
DATA_DIR = os.path.join(project_root, "data")


def get_available_specializations(deck_id=None) -> list[str]:
    if deck_id is not None:
        try:
            deck_specs = get_deck_base_specializations(deck_id)
            if deck_specs: return deck_specs
        except Exception as e:
            logger.warning(f"Failed to read specs from deck {deck_id}: {e}")

    try:
        path = os.path.join(DATA_DIR, "Specializations.csv")
        if not os.path.exists(path): return ["Scraper", "Crawler", "Querist"]
        df = pd.read_csv(path)
        return df[df['isBase'] == 1]['Name'].tolist()
    except Exception:
        return ["Scraper", "Crawler", "Querist"]


def get_available_decks() -> list[int]:
    decks = []
    if not os.path.exists(DATA_DIR):
        logger.error(f"DATA_DIR not found: {DATA_DIR}")
        return []

    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.csv') and filename != 'Specializations.csv' and filename != 'Cards.csv':
            try:
                decks.append(int(filename.replace('.csv', '')))
            except:
                continue
    return sorted(decks)

def get_deck_metadata(deck_id:int | None = None) -> dict:
    try:
        deck_metadata = json.load(open(os.path.join(DATA_DIR, "Decks.json")))
    except FileNotFoundError:
        print(f"Deck metadata file not found in: {os.path.join(DATA_DIR, 'Decks.json')}")
        return {}
    if deck_id is None:
        return deck_metadata
    else:
        return deck_metadata[deck_id]
