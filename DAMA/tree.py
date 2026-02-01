from __future__ import annotations

import math
import random
from typing import Any, TypeAlias, override

from core.card import CantripCard, WeaponCard, EquipCard, Card
from core.enums import Winner, Actions, CardTag
from core.game import Game
from core.game_logs import GameLogger
from DAMA.heuristics import HeuristicAnalyzer
from DAMA.meta_registry import MetaRegistry
from DAMA.moves_discoverer import get_moves
from DAMA.constants import MCTSConfig, RolloutPolicyWeights

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
        b_param = MCTSConfig.RAVE_B_PARAM # Makes the AMAF values' impact "decay" over time
        if self.visits == 0: return float('inf')
        self.standard_wr = self.wins / self.visits
        self.amaf_wr = self.amaf_wins / self.amaf_visits if self.amaf_visits > 0 else MCTSConfig.AMAF_DEFAULT_WR
        beta_denom = self.visits + self.amaf_visits + 4*b_param**2*self.visits*self.amaf_visits
        if beta_denom == 0: beta = 1
        else: beta = self.amaf_visits / beta_denom
        combined_wr = (1-beta)*self.standard_wr + beta*self.amaf_wr
        exploration_term = MCTSConfig.UCT_EXPLORATION_CP * math.sqrt(2 * math.log(self.parent.visits) / self.visits) if self.parent.visits and self.visits else 0
        score = combined_wr + exploration_term
        return score



class MCTSTree:
    def __init__(self, root_state:Game, registry: MetaRegistry | None = None):
        # We start by using a CLONE of the state, so we don't mess up the real game's logs.
        # Immedately strip the logs to save memory/perf during expansion
        sim_root = root_state.clone()
        sim_root.logs = DummyLogger("", [])
        self.root: Node = Node(sim_root)
        self.registry = registry if registry else MetaRegistry()

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
        weights_cache = {}
        for move in self.root.moves_to_try:
            name = getattr(move[0], 'name', None)
            if name and name not in weights_cache:
                weights_cache[name] = self.registry.get_meta_weight_modifier(name)

        for i in range(iterations):
            # determinization on root to create different possibilities
            working_state = self.root.state.clone()
            working_state.simulation_mode = True
            working_state.logs = DummyLogger("", [])
            observer_id = working_state.isPlaying
            self._determinize_state(working_state, observer_id)

            # Selection
            selected_node, working_state = self._selection(self.root, working_state)
            # Expansion
            if working_state.winner == Winner.NONE:
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

            # Check if the move is valid in the determinized state
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
    def _determinize_state(state: Game, observer_id: int) -> None:
        """
        Redistributes hidden information (Opponent Hand/Deck) and shuffles Observer Deck.
        Critical: Preserves 'Known' cards (Observer Hand, Active Candidates) to ensure information consistency.
        """
        obs_idx, opp_idx = observer_id, 1 - observer_id
        observer = state.players[obs_idx]
        opponent = state.players[opp_idx]

        # --- OBSERVER: Shuffle Deck, Preserve Hand & Candidates ---
        # Candidates in the deck (e.g. valid targets for specific search) are "Known".
        # --- OBSERVER: Randomize Deck, Preserve Visible Cards ---
        obs_cands_ids = {id(c) for c in observer.choice_candidates} if observer.choice_pending else set()
        
        obs_deck_locked = []
        obs_deck_shufflable = []
        for c in observer.deck.cards:
            if id(c) in obs_cands_ids: obs_deck_locked.append(c)
            else: obs_deck_shufflable.append(c)
        
        random.shuffle(obs_deck_shufflable)
        observer.deck.cards = obs_deck_shufflable + obs_deck_locked

        # --- OPPONENT: Randomize Hand & Deck, Preserve Known Candidates ---
        opp_cands_ids = {id(c) for c in opponent.choice_candidates} if opponent.choice_pending else set()
        
        opp_hand_known = []
        opp_hand_unknown = []
        # Hand Pass
        for c in opponent.hand:
            if id(c) in opp_cands_ids: opp_hand_known.append(c)
            else: opp_hand_unknown.append(c)
        
        opp_deck_known = []
        opp_deck_unknown = []
        # Deck Pass
        for c in opponent.deck.cards:
            if id(c) in opp_cands_ids: opp_deck_known.append(c)
            else: opp_deck_unknown.append(c)
            
        unknown_pool = opp_hand_unknown + opp_deck_unknown
        random.shuffle(unknown_pool)
        
        needed_for_hand = len(opponent.hand) - len(opp_hand_known)
        opponent.hand = opp_hand_known + unknown_pool[:needed_for_hand] 
        opponent.deck.cards = unknown_pool[needed_for_hand:] + opp_deck_known

    def _simulation(self, state:Game, weights_cache: dict) -> float:
        depth = 0
        while state.winner == Winner.NONE and depth < MCTSConfig.MAX_ROLLOUT_DEPTH:
            moves = get_moves(state.isPlaying, state)
            if not moves: break
            
            # Use FAST rollout policy with Meta Weights
            move = self._rollout_policy(state, moves, weights_cache)
            state.receiveAction(state.isPlaying, move[1]['action'], move[1]['args'])
            depth += 1

        winner_id = state.winner

        if winner_id != Winner.NONE:
            return 1 if winner_id is Winner.PLAYER1 else 0
        else:
            score = HeuristicAnalyzer.evaluate_state(state, player_id=0)
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
    def _rollout_policy(state: Game, moves: list[MoveData], weights_cache: dict = None) -> MoveData:
        """
        Intelligent Rollout Policy (Restored).
        Uses HeuristicAnalyzer for tactical depth and MetaRegistry for historical bias.
        Optimized to use centralized constants from RolloutPolicyWeights.
        """
        threats = HeuristicAnalyzer.analyze_threats(state, state.isPlaying)
        weights = []
        
        me = state.players[state.isPlaying]
        opp = state.players[1 - state.isPlaying]

        for card, action_data in moves:
            act_type = action_data['action']
            base_weight = RolloutPolicyWeights.BASE_WEIGHT

            # 1. Mulligan Logic
            if act_type == Actions.MULLIGAN:
                mulligan_bonus = HeuristicAnalyzer.evaluate_mulligan(state, state.isPlaying)
                base_weight += mulligan_bonus

            # 2. Greedy Finisher (Lethal check) - Instant decision for efficiency
            if act_type == Actions.ATTACK:
                damage = max(0, me.currentPower - opp.currentTenacity)
                if damage >= opp.currentHP:
                    return card, action_data

            # 3. Micro Heuristics (Deep tactial analysis)
            micro_bonus = HeuristicAnalyzer.get_micro_heuristic_bonus(
                card, action_data['args'], state, state.isPlaying, weights_cache=weights_cache
            )
            base_weight += micro_bonus

            # 4. Reactive Defensive Logic
            if threats.wall_threat and card and (CardTag.DEFENSIVE in card.tags or CardTag.SCALER in card.tags):
                base_weight += RolloutPolicyWeights.WALL_THREAT_REACTIVE_BONUS

            # 5. Meta-Game Knowledge (MetaRegistry)
            if weights_cache and card:
                card_name = getattr(card, 'name', None)
                if card_name and card_name in weights_cache:
                    bias, explore = weights_cache[card_name]
                    base_weight += (bias * RolloutPolicyWeights.META_BIAS_MULTIPLIER) + \
                                   (explore * RolloutPolicyWeights.META_EXPLORE_MULTIPLIER)

            weights.append(max(RolloutPolicyWeights.MIN_WEIGHT, base_weight))

        # Weighted Sampling (Human-like behavior)
        return random.choices(moves, weights=weights, k=1)[0]


