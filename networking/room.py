import dataclasses
from core.game import Game


@dataclasses.dataclass
class Room:
    code: str
    host_id: str
    clients: list[str] = dataclasses.field(default_factory=list)
    is_private: bool = False
    game_state: Game | None = None

    @property
    def is_full(self):
        return len(self.clients) >= 2
    @property
    def is_empty(self):
        return len(self.clients) == 0

    @property
    def is_joinable_via_quick_match(self):
        return not self.is_private and not self.is_full and self.game_state is None