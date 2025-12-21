import contextvars
import dataclasses
import json
import logging
import os
import sys
from dataclasses import is_dataclass
from enum import Enum, auto
from typing import override

from core.game import Game

GLOBAL_PROTOCOL_VERSION:str = "0.0.2a"

log_context = contextvars.ContextVar("log_context", default="")
class ContextFilter(logging.Filter):
    def filter(self, record):
        # Get the current value (e.g., "Room-1 | Client-A")
        ctx = log_context.get()
        # Add a new attribute 'context_prefix' to the log record
        record.context_prefix = f"[{ctx}] " if ctx else ""
        return True


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    # Remove default handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    # Filter provides us with the log context
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(context_prefix)s%(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    # Add the filter to the handler so it runs for every log
    handler.addFilter(ContextFilter())
    root_logger.addHandler(handler)
    # Silence websockets noise redirecting logs as warnings
    logging.getLogger("websockets").setLevel(logging.WARNING)

logger = logging.getLogger("UtilityFunctions")


class CSActions(Enum):
    HANDSHAKE = auto()
    ERROR = auto()
    INFO = auto()
    CREATE_ROOM = auto()
    JOIN = auto()
    QUICK_MATCH = auto()
    ROOM_JOINED = auto()
    SET_NAME = auto()
    GET_DECK = auto()
    DECKS_AVAILABLE = auto()
    SEND_DECK = auto()
    DECK_ISVALID = auto()
    GET_SPEC = auto()
    SPECS_AVAILABLE = auto()
    SEND_SPEC = auto()
    SPEC_ISVALID = auto()
    PLAYER_READY = auto()
    LOBBY_UPDATE = auto()
    START_GAME = auto()
    ACTION_EXECUTED = auto()
    UPDATED_STATE = auto()
    REMATCH = auto()

def sanitized_state(real_game:Game, player_id:int):
    import copy
    try:
        state = copy.deepcopy(real_game)
        opp_idx = 1 - player_id
        if opp_idx >= len(state.players):
            logger.error(f"Sanitization error: Opponent index {opp_idx} out of bounds.")
            return real_game #FIXME: feels dangerous, but I don't know what else to do for now
        for card in state.players[opp_idx].hand:
            card.name = "Covered"
            card.Text = "?"
        return state
    except Exception as e:
        logger.error(f"Deep copy or card sanitization failed for player {player_id}: {e}")
        return real_game #FIXME: feels dangerous, but I don't know what else to do for now

# --- HELPERS ---
def get_opponent_name(lobby_data: dict, my_id: str) -> str | None:
    """Finds the name of the first player in the lobby that isn't the current client."""
    players = lobby_data.get("players", [])
    for p in players:
        if p.get("id") != my_id:
            return p.get("name")
    return None

# --- EXCEPTIONS ---
class ClientDisconnected(Exception): pass

# ------------------------------ JSON ENCODER ------------------------------
class GameEncoder(json.JSONEncoder):
    @override
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        # Assuming any complex object we want to serialize inherits the Mixin DataclassJSONCapable
        if hasattr(obj, 'dict_serializer') and callable(obj.dict_serializer):
            return obj.dict_serializer()
        # If the object is a dataclass without the mixin (e.g., LogEntry if not updated)
        if is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        return super().default(obj)