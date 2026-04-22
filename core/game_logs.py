from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

from core.enums import Phases
from core.serialization import DataclassJSONCapable


@dataclass
class LogEntry(DataclassJSONCapable):
    turn: int
    player: int
    phase: Phases
    message: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime
            self.timestamp = datetime.now().strftime("%H:%M:%S")

    @classmethod
    def dict_deserializer(cls, data: Dict[str, Any]):
        return cls(
            turn=data['turn'],
            player=data['player'],
            phase=Phases(data['phase']),
            message=data['message'],
            timestamp=data.get('timestamp', "")
        )

@dataclass
class GameLogger(DataclassJSONCapable):
    room_name: str
    entries: List[LogEntry] = field(default_factory=list)

    def append(self, log_entry: LogEntry):
        self.entries.append(log_entry)

    @classmethod
    def dict_deserializer(cls, data: Dict[str, Any]):
        # Reconstruct the list of LogEntry objects
        entries = [LogEntry.dict_deserializer(e) for e in data['entries']]
        return cls(
            room_name=data.get('room_name', "Unknown"),
            entries=entries
        )