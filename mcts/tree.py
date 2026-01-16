from __future__ import annotations

import math
import random
from typing import Any, TypeAlias, override

from core.card import CantripCard, WeaponCard, EquipCard, Card
from core.enums import Winner, Actions
from core.game import Game
from core.game_logs import GameLogger
from mcts.heuristics import HeuristicAnalyzer
from mcts.meta_registry import MetaRegistry
from mcts.moves_discoverer import get_moves

MoveData: TypeAlias = tuple[Card | EquipCard | WeaponCard | CantripCard | None, dict[str, Any]]

class DummyLogger(GameLogger):
    @override
    def append(self, *args, **kwargs):
        pass

class Node:
    def __init__(self, state:Game, parent:Node | None = None, move_data:MoveData | None = None):
        self.state: Game = state
        # Using DummyLogger to prevent logging overhead and crashes during simulation
        self.state.logs = DummyLogger("Dummy")
        self.parent: Node = parent
        self.card_used: Card|EquipCard|WeaponCard|CantripCard|None = move_data[0] if move_data else None
        self.move: dict[str, Any]|None = move_data[1] if move_data else None
        self.children: list[Node] = []

        self.wins: int = 0
        self.visits: int = 0
        self.standard_wr: float = 0.0

        #It heuristically determines the node's value
        #from the entire line of play's success
        #rather than from the impact of the node itself.
        #Useful to find "Game Engines", cards with much usefulness
        #but low impact on the state of the game by themselves
        self.amaf_wins: int = 0
        self.amaf_visits: int = 0
        self.amaf_wr: float = 0.0

        self.moves_to_try = get_moves(self.state.isPlaying, state)

    def is_leaf(self) -> bool:
        return len(self.children) == 0
    def is_fully_expanded(self) -> bool:
        return len(self.moves_to_try) == 0

    def get_path(self) -> list[Node]:
        path = []
        node = self
        path.append(node)
        while node.parent is not None:
            node = node.parent
            path.append(node)
        path.reverse()
        return path

    def ucb1_rave(self) -> float:
        b_param = 0.05 # Makes the AMAF values' impact "decay" over time
        if self.visits == 0: return float('inf')
        self.standard_wr = self.wins / self.visits
        self.amaf_wr = self.amaf_wins / self.amaf_visits if self.amaf_visits > 0 else 0.5
        beta_denom = self.visits + self.amaf_visits + 4*b_param**2*self.visits*self.amaf_visits
        if beta_denom == 0: beta = 1
        else: beta = self.amaf_visits / beta_denom
        combined_wr = (1-beta)*self.standard_wr + beta*self.amaf_wr
        exploration_term = (2*math.log(self.parent.visits)/self.visits)**0.5 if self.parent.visits and self.visits else 0
        score = combined_wr + exploration_term
        return score



class MCTSTree:
    def __init__(self, root_state:Game):
        self.root: Node = Node(root_state)

    def step_root_to_node(self, node:Node) -> None:
        if node not in self.root.children:
            # If for some reason the node isn't a child, we fallback to move-based search
            move_data:MoveData = (node.card_used, node.move)
            self.step_root_by_move(move_data)
            return

        self.root = node

    def step_root_by_move(self, move_data:MoveData) -> None:
        card_used, action_dict = move_data

        # Try to find if this move was already expanded
        for child in self.root.children:
            if child.move == action_dict:
                self.root = child
                return

        # If not expanded, create the node to act as the new root
        # This ensures the path is preserved even for 'surprising' opponent moves
        new_state = self.root.state.clone()
        new_state.receiveAction(new_state.isPlaying, action_dict['action'], action_dict['args'])

        new_node = Node(
            new_state,
            parent=self.root,
            move_data=move_data
        )
        self.root.children.append(new_node)
        self.root = new_node

    def mcts_decisor(self, iterations: int = 800) -> Node|None:
        if self.root.is_leaf() and self.root.is_fully_expanded(): return None
        
        # Performance Cache for the duration of this decisor call
        registry = MetaRegistry.get_instance()
        weights_cache = {}
        for move in self.root.moves_to_try:
            name = getattr(move[0], 'name', None)
            if name and name not in weights_cache:
                weights_cache[name] = registry.get_meta_weight_modifier(name)

        for i in range(iterations):
            #determinization on root to create different possibilities
            working_state = self.root.state.clone()
            observer_id = working_state.isPlaying
            self._determinize_state(working_state, observer_id)

            # Selection
            selected_node, working_state = self._selection(self.root, working_state)
            # Expansion
            if not working_state.winner != Winner.NONE:
                expanded_node, working_state = self._expansion(selected_node, working_state)
            else:
                expanded_node = selected_node
            # Simulation (Playout)
            result = self._simulation(working_state, weights_cache)
            # Backpropagation
            self._backpropagation(expanded_node, result)
            if i > iterations/4 and i % (iterations/10) == 0:
                top_two = sorted(self.root.children, key=lambda n: n.visits, reverse=True)[:2]
                if len(top_two) > 1 and top_two[0].visits > top_two[1].visits * 10:
                    break
        
        if not self.root.children:
            print(f"DEBUG: Root has no children. Moves to try: {len(self.root.moves_to_try)}")
            return None
            
        best_child = max(self.root.children, key=lambda n: n.visits)
        return best_child

    @staticmethod
    def _selection(node: Node, working_state: Game) -> tuple[Node, Game]:
        n = node
        while not n.is_leaf():
            if not n.is_fully_expanded(): break

            n = max(n.children, key=lambda c: c.ucb1_rave())
            MCTSTree._ensure_move_consistency(n, working_state)
            res = working_state.receiveAction(working_state.isPlaying, n.move['action'], n.move['args'])
            if not res['valid']:
                # We expect this to happen occasionally due to shuffling.
                # Just break the loop and let MCTS try the next iteration.
                break

            if working_state.winner != Winner.NONE: break
        return n, working_state

    @staticmethod
    def _expansion(selected_node, working_state: Game) -> tuple[Node, Game]:
        # Loop until we find a valid move or run out of moves
        while not selected_node.is_fully_expanded():
            move_data = selected_node.moves_to_try.pop()

            # Create a prospective node (cloning state is expensive but necessary here)
            new_node = Node(
                working_state.clone(),
                parent=selected_node,
                move_data=move_data
            )

            # Try to fix the state to make this move valid
            MCTSTree._ensure_move_consistency(new_node, working_state)

            # Check if the move is valid in the fixed state
            res = working_state.receiveAction(working_state.isPlaying, move_data[1]['action'], move_data[1]['args'])

            if res['valid']:
                # Success! Update the node's state to match the result
                new_node.state = working_state.clone()
                selected_node.children.append(new_node)
                return new_node, working_state

            # If invalid, the loop continues and tries the next move...

        # If we run out of moves and nothing was valid (Rare edge case)
        # We return the selected node itself to force a rollout from here
        return selected_node, working_state

    @staticmethod
    def _ensure_move_consistency(node: Node, state: Game) -> None:
        required_card = node.card_used
        if not required_card: return

        player = state.players[state.isPlaying]
        action = node.move['action']

        # CASE 1: REWARDS
        if action == Actions.CHOOSE_REWARD:
            if any(c.name == required_card.name for c in player.choice_candidates): return

            # Find in Deck
            deck_index = -1
            for i, c in enumerate(player.deck.cards):
                if c.name == required_card.name:
                    deck_index = i
                    break

            if deck_index != -1:
                player.choice_candidates.append(player.deck.cards.pop(deck_index))
            return

        # CASE 2: HAND ACTIONS
        if any(c.name == required_card.name for c in player.hand): return

        # Find in Deck
        deck_index = -1
        for i, c in enumerate(player.deck.cards):
            if c.name == required_card.name:
                deck_index = i
                break

        if deck_index != -1:
            card_from_deck = player.deck.cards.pop(deck_index)
            # Swap with last card in hand if hand is not empty
            if player.hand:
                card_from_hand = player.hand.pop()
                player.deck.cards.append(card_from_hand)
            player.hand.append(card_from_deck)

    @staticmethod
    def _determinize_state(state: Game, observer_id: int) -> None:
        opp_id = 1 - observer_id
        observer = state.players[observer_id]
        opponent = state.players[opp_id]

        # Cards currently being chosen from the deck must remain in the deck
        opp_candidates = opponent.choice_candidates if opponent.choice_pending else []
        obs_candidates = observer.choice_candidates if observer.choice_pending else []

        # Opponent's unknown pool: hand + deck (excluding candidates being viewed)
        opp_unknown_pool = []
        opp_unknown_pool.extend(opponent.hand)
        for c in opponent.deck.cards:
            if c not in opp_candidates:
                opp_unknown_pool.append(c)

        import random
        random.shuffle(opp_unknown_pool)

        hand_size = len(opponent.hand)
        opponent.hand = opp_unknown_pool[:hand_size]
        opponent.deck.cards = opp_unknown_pool[hand_size:] + opp_candidates
        
        # Observer's deck shuffle (order is unknown, but candidates are known to stay in deck)
        obs_deck_pool = [c for c in observer.deck.cards if c not in obs_candidates]
        random.shuffle(obs_deck_pool)
        observer.deck.cards = obs_deck_pool + obs_candidates

    def _simulation(self, state:Game, weights_cache: dict) -> float:
        temp_state = state.clone()
        depth = 0
        while temp_state.winner == Winner.NONE and depth < 60:
            moves = get_moves(temp_state.isPlaying, temp_state)
            if not moves: break
            
            # Use HEURISTIC select for playouts to build a human-like meta
            move = self._heuristic_move_select(temp_state, moves, weights_cache)
            temp_state.receiveAction(temp_state.isPlaying, move[1]['action'], move[1]['args'])
            depth += 1

        winner_id = temp_state.winner

        if winner_id != Winner.NONE:
            # We skip registry update here to avoid polluting stats with simulated games 
            # and because we switched to tracking "Played Cards" which is hard to extract here without 
            # tracking the whole simulation path.
            # Local heuristics will just depend on "Pre-Existing" meta knowledge.

            return 1 if winner_id is Winner.PLAYER1 else 0
        else:
            score = HeuristicAnalyzer.evaluate_state(temp_state, player_id=0)
            return (score + 1) / 2

    @staticmethod
    def _backpropagation(expanded_node: Node, score:float) -> None:
        current = expanded_node
        while current is not None:
            current.visits += 1
            current.wins += score  # P1 Score
            current.amaf_visits += 1
            current.amaf_wins += score
            current = current.parent

    @staticmethod
    def _heuristic_move_select(state: Game, moves: list[MoveData], weights_cache: dict) -> MoveData:
        """Heuristic selection for playouts that balances speed with human-like logic."""
        threats = HeuristicAnalyzer.analyze_threats(state, state.isPlaying)
        weights = []
        
        for card, action_data in moves:
            act_type = action_data['action']
            base_weight = 10.0

            if act_type == Actions.MULLIGAN:
                mulligan_bonus = HeuristicAnalyzer.evaluate_mulligan(state, state.isPlaying)
                base_weight += mulligan_bonus

            # 1. Greedy Finisher (Lethal check)
            if act_type == Actions.ATTACK:
                target_hp = state.players[1 - state.isPlaying].currentHP
                if state.players[state.isPlaying].currentPower - state.players[1-state.isPlaying].currentTenacity >= target_hp:
                    return card, action_data

            # 2. Local Logic (Heuristics)
            micro_bonus = HeuristicAnalyzer.get_micro_heuristic_bonus(card, action_data['args'], state, state.isPlaying, weights_cache=weights_cache)
            base_weight += micro_bonus

            # Anti-Meta awareness in heuristic
            if threats.wall_threat and 'Buff' in str(card):
                base_weight += 200.0

            # 3. Meta weights from cache (Fast)
            card_name = getattr(card, 'name', None)
            if card_name and card_name in weights_cache:
                bias, explore = weights_cache[card_name]
                
                # Expert logic: In playouts, we trust the meta bias but reduce exploration
                base_weight += bias + (explore * 0.2)

            weights.append(max(0.1, base_weight))

        return random.choices(moves, weights=weights, k=1)[0]


