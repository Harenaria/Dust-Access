import json
import math
import os
from collections import defaultdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _default_card_stats():
    return {'wins': 0, 'plays': 0, 'turn_sum': 0, 'level': 0, 'type': 'Unknown', 'class': 'Medium'}


def _default_deck_stats():
    return {'wins': 0, 'plays': 0, 'swinginess': 0.0, 'interactivity': 0, 'comebacks': 0, 'total_turns': 0}


class MetaRegistry:
    def __init__(self):
        self.card_stats = defaultdict(_default_card_stats)
        self.deck_stats = defaultdict(_default_deck_stats)
        self.matchup_stats = defaultdict(_default_deck_stats)
        self.total_simulations = 0
        self.deck_cache = {}

    def clear(self):
        self.card_stats.clear()
        self.deck_stats.clear()
        self.matchup_stats.clear()
        self.total_simulations = 0
        self.deck_cache.clear()

    def _merge_deck_info(self, reg_stats:dict):
        for key, stats in reg_stats.items():
            target = self.matchup_stats[key]
            target['wins'] += stats.get('wins', 0)
            target['plays'] += stats.get('plays', 0)
            target['swinginess'] += stats.get('swinginess', 0.0)
            target['interactivity'] += stats.get('interactivity', 0)
            target['comebacks'] += stats.get('comebacks', 0)
            target['total_turns'] += stats.get('total_turns', 0)

    def get_raw_data(self):
        return {
            'card_stats': dict(self.card_stats),
            'deck_stats': dict(self.deck_stats),
            'matchup_stats': dict(self.matchup_stats),
            'total_simulations': self.total_simulations
        }

    def merge_data(self, data: dict):
        self.total_simulations += data.get('total_simulations', 0)

        for card, stats in data.get('card_stats', {}).items():
            target = self.card_stats[card]
            target['wins'] += stats.get('wins', 0)
            target['plays'] += stats.get('plays', 0)
            target['turn_sum'] += stats.get('turn_sum', 0)
            if stats.get('level', 0) > 0: target['level'] = stats['level']
            if stats.get('type') and stats.get('type') != "Unknown": target['type'] = stats['type']
            if stats.get('class') and stats.get('class') != "Medium": target['class'] = stats['class']

        self._merge_deck_info(data.get('deck_stats', {}))

        self._merge_deck_info(data.get('matchup_stats', {}))

    def update_stats(self, deck_id: int, played_cards: list, winner: bool, opponent_deck_id: int = None,
                     metrics: dict = None):
        val = 1 if winner else 0
        m = metrics or {}

        self._update_helper(self.deck_stats, deck_id, m, val)

        if opponent_deck_id is not None:
            key = f"{deck_id}_vs_{opponent_deck_id}"
            self._update_helper(self.matchup_stats, key, m, val)

        unique_cards = {}
        for item in played_cards:
            c, turn = item if isinstance(item, tuple) else (item, 0)
            name = getattr(c, 'name', None) or (c.get('name') if isinstance(c, dict) else None)
            if name and name not in unique_cards:
                unique_cards[name] = {'card': c, 'turn': turn}

        for name, data in unique_cards.items():
            card_obj, turn = data['card'], data['turn']
            target = self.card_stats[name]
            target['plays'] += 1
            target['wins'] += val
            target['turn_sum'] += turn

            lvl = getattr(card_obj, 'level', 0) or (card_obj.get('level', 0) if isinstance(card_obj, dict) else 0)
            if lvl > 0: target['level'] = lvl

            obj_type = getattr(card_obj, 'cardType', None) or (
                card_obj.get('type') or card_obj.get('cardType') if isinstance(card_obj, dict) else None)
            if obj_type: target['type'] = str(obj_type).upper().replace('_', '-')

            card_class = getattr(card_obj, 'Class', None) or getattr(card_obj, 'accessorClass', None) or getattr(card_obj, 'acClass', None)
            if card_class: target['class'] = str(card_class)

        self.total_simulations += 0.5

    @staticmethod
    def _update_helper(stat_list, key, metrics: dict, winner: int):
        stat_list[key]['plays'] += 1
        stat_list[key]['wins'] += winner
        stat_list[key]['swinginess'] += metrics.get('swinginess', 0.0)
        stat_list[key]['interactivity'] += metrics.get('interactivity', 0)
        stat_list[key]['comebacks'] += 1 if metrics.get('comeback_win') else 0
        stat_list[key]['total_turns'] += metrics.get('turns', 0)

    def get_meta_weight_modifier(self, card_name: str) -> tuple[float, float]:
        if card_name not in self.card_stats: return 0.0, 500.0
        stats = self.card_stats[card_name]
        wins, plays = stats['wins'], stats['plays']
        if plays == 0: return 0.0, 500.0

        k = 1000.0
        win_rate = wins / plays
        weighted_bias = (win_rate - 0.5) * ((plays / (plays + k)) * 0.8) * 100.0
        exploration = 2.0 * math.sqrt(math.log(max(1, self.total_simulations)) / plays)
        return weighted_bias, exploration * 50.0

    def save(self, path=None):
        path = path or os.path.join(PROJECT_ROOT, "data", "meta_stats.json")
        if not os.path.isabs(path): path = os.path.join(PROJECT_ROOT, path)
        data = self.get_raw_data()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".tmp", 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(path + ".tmp", path)
        except Exception as e:
            print(f"Save error: {e}")

    def load(self, path=None):
        path = path or os.path.join(PROJECT_ROOT, "data", "meta_stats.json")
        if not os.path.isabs(path): path = os.path.join(PROJECT_ROOT, path)
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.total_simulations = data.get("total_simulations", 0)
                for k, v in data.get("card_stats", {}).items():
                    self.card_stats[k].update(v)
                for k, v in data.get("deck_stats", {}).items():
                    self.deck_stats[int(k)].update(v)
                for k, v in data.get("matchup_stats", {}).items():
                    self.matchup_stats[k].update(v)
        except Exception as e:
            print(f"Load error: {e}")