import argparse
import multiprocessing
import os
import time
import random
import json
import math
from itertools import combinations_with_replacement

from tqdm import tqdm

from core.deck import get_deck_base_specializations
from core.enums import Winner, Actions
from core.game import matchCreator, Game
from DAMA.meta_registry import MetaRegistry
from DAMA.tree import MCTSTree

_SPECS_CACHE = {}


def get_simulation_config(target_moe: float):
    """
    Dynamically calculates the number of games required to reach the target
    Margin of Error (MoE) at a 95% Confidence Level (Z=1.96).

    It applies 'Process Noise Multipliers' to account for the fact that
    lower-iteration (Casual) AI is noisier and requires a larger sample size
    to find the true signal compared to high-iteration (Competitive) AI.
    """
    Z_SCORE = 1.96
    P_VAL = 0.5  # Worst case variance assumption (50% winrate)

    # Standard formula for N
    base_n = (Z_SCORE ** 2 * P_VAL * (1 - P_VAL)) / (target_moe ** 2)

    # Round up to nearest 10 for clean numbers
    def clean_n(n): return int(math.ceil(n / 10.0)) * 10

    # Multipliers:
    # Casual (1.5x): High variance due to sub-optimal plays. Needs more games.
    # Advanced (1.2x): Medium variance.
    # Competitive (1.0x): Low variance. AI plays optimally, so Base N is sufficient.
    return [
        ("Casual", 100, clean_n(base_n * 1.5)),
        ("Advanced", 500, clean_n(base_n * 1.2)),
        ("Competitive", 1000, clean_n(base_n * 1.0))
    ]


def _get_cached_specs(deck_id: int):
    if deck_id not in _SPECS_CACHE:
        _SPECS_CACHE[deck_id] = get_deck_base_specializations(deck_id)
    return _SPECS_CACHE[deck_id]


def god_mode_consistency(game: Game, move_data: dict, card_used):
    """
    Aggressively forces the Real Game state to match the AI's decision.
    """
    if not card_used: return

    player = game.players[game.isPlaying]
    action = move_data['action']
    required_name = card_used.name

    # 1. REWARDS
    if action == Actions.CHOOSE_REWARD:
        if any(c.name == required_name for c in player.choice_candidates): return
        # Check Deck
        for i, c in enumerate(player.deck.cards):
            if c.name == required_name:
                player.choice_candidates.append(player.deck.cards.pop(i))
                return
        # Check Hand
        for i, c in enumerate(player.hand):
            if c.name == required_name:
                player.choice_candidates.append(player.hand.pop(i))
                return
        # Check Equipped
        for slot, c in player.equippedCards.items():
            if c and c.name == required_name:
                player.equippedCards[slot] = None
                player.choice_candidates.append(c)
                return
        return

    # 2. HAND ACTIONS
    if any(c.name == required_name for c in player.hand): return

    # Check Deck
    for i, c in enumerate(player.deck.cards):
        if c.name == required_name:
            card = player.deck.cards.pop(i)
            if player.hand: player.deck.cards.append(player.hand.pop())
            player.hand.append(card)
            return
    # Check Candidates
    for i, c in enumerate(player.choice_candidates):
        if c.name == required_name:
            card = player.choice_candidates.pop(i)
            player.hand.append(card)
            return


def run_single_match(p1_deck_id: int, p2_deck_id: int, specs1: dict, specs2: dict, turn_iterations: int = 100,
                     verbose: bool = False) -> tuple[int | None, MetaRegistry]:
    if not specs1 or not specs2: return None, MetaRegistry()
    spec1_name = list(specs1.keys())[0] if specs1 else "Unknown"
    spec2_name = list(specs2.keys())[0] if specs2 else "Unknown"
    game = matchCreator("SimRoom", "AI_1", p1_deck_id, spec1_name, "AI_2", p2_deck_id, spec2_name)

    p1_played = []
    p2_played = []
    hp_history = [(game.players[0].currentHP, game.players[1].currentHP)]
    interactivity_count = 0
    p1_low_hp = False
    p2_low_hp = False

    MAX_TURNS = 50
    stuck_counter = 0
    last_turn_hash = ""

    while game.winner == Winner.NONE and game.turn < MAX_TURNS:
        current_hash = f"{game.turn}-{game.phase}-{game.isPlaying}-{len(game.players[game.isPlaying].hand)}"
        if current_hash == last_turn_hash:
            stuck_counter += 1
        else:
            stuck_counter = 0; last_turn_hash = current_hash

        # Anti-Stuck Logic
        if stuck_counter > 3:
            legal = game.outputLegalActions(game.isPlaying)
            if not legal: break
            action = random.choice(legal)
            args = {'index': 0} if action in [Actions.DISCARD, Actions.CHOOSE_REWARD] else {}
            game.receiveAction(game.isPlaying, action, args)
            continue

        tree = MCTSTree(game)
        best_node = tree.mcts_decisor(iterations=turn_iterations)

        if not best_node:
            game.receiveAction(game.isPlaying, Actions.PASS_PHASE, {})
            if game.winner != Winner.NONE: break
            if stuck_counter > 5: break
            continue

        move_data = best_node.move
        card_used = best_node.card_used
        if game.isPlaying == 0:
            p1_played.append((card_used, game.turn))
        else:
            p2_played.append((card_used, game.turn))

        god_mode_consistency(game, move_data, card_used)
        res = game.receiveAction(game.isPlaying, move_data['action'], move_data['args'])

        if move_data['action'] in [Actions.ATTACK, Actions.ACTIVATE, Actions.DISCARD]:
            interactivity_count += 1

        hp_history.append((game.players[0].currentHP, game.players[1].currentHP))
        if game.players[0].currentHP / max(1, game.players[0].currentDurability) < 0.3: p1_low_hp = True
        if game.players[1].currentHP / max(1, game.players[1].currentDurability) < 0.3: p2_low_hp = True

    total_swing = 0.0
    max_durability = max(1, game.players[0].currentDurability + game.players[1].currentDurability)
    for i in range(1, len(hp_history)):
        gap_current = hp_history[i][0] - hp_history[i][1]
        gap_prev = hp_history[i - 1][0] - hp_history[i - 1][1]
        total_swing += abs(gap_current - gap_prev)
    swinginess = (total_swing / max_durability) / max(1, len(hp_history))

    is_p1_win = (game.winner == Winner.PLAYER1)
    is_p2_win = (game.winner == Winner.PLAYER2)
    p1_comeback = (is_p1_win and p1_low_hp)
    p2_comeback = (is_p2_win and p2_low_hp)

    registry = MetaRegistry.get_instance()
    m1 = {'swinginess': swinginess, 'interactivity': interactivity_count, 'comeback_win': p1_comeback,
          'turns': game.turn}

    if game.winner != Winner.NONE:
        registry.update_stats(p1_deck_id, p1_played, winner=is_p1_win, opponent_deck_id=p2_deck_id, metrics=m1)
        registry.update_stats(p2_deck_id, p2_played, winner=is_p2_win, opponent_deck_id=p1_deck_id, metrics=m1)

    return (0 if is_p1_win else (1 if is_p2_win else None)), registry


def run_batch(batch_args):
    p1, p2, n, verbose, iterations = batch_args
    registry = MetaRegistry.get_instance()
    registry.clear()

    specs1 = _get_cached_specs(p1)
    specs2 = _get_cached_specs(p2)

    if not specs1 or not specs2: return {}, 0

    success_count = 0
    for i in range(n):
        try:
            win, _ = run_single_match(p1, p2, specs1, specs2, turn_iterations=iterations, verbose=verbose)
            if win is not None: success_count += 1
        except Exception as e:
            if verbose: print(f"Match Error: {e}")
            continue

    return registry.get_raw_data(), success_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decks", type=str, default="0")
    parser.add_argument("--procs", type=int, default=6)
    parser.add_argument("--moe", type=float, default=0.05, help="Target Margin of Error (e.g. 0.03 for 3%)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    deck_ids = [int(x) for x in args.decks.split(",")]
    matchups = list(combinations_with_replacement(deck_ids, 2))

    # DYNAMICALLY CALCULATE GAMES BASED ON MoE
    tiers = get_simulation_config(args.moe)

    print(f"=== Starting Tiered Simulation (Target MoE: ±{args.moe:.1%}) ===")
    print(f"Parallel Processes: {args.procs}")

    for tier_name, iterations, n_games in tiers:
        total_tier_games = n_games * len(matchups)
        print(f"\n>> Running Tier: {tier_name}")
        print(f"   - MCTS Depth: {iterations} iterations")
        print(f"   - Sample Size: {total_tier_games} games ({n_games} per matchup)")

        # 1. Reset Registry for this Tier
        tier_registry = MetaRegistry()
        tier_registry.clear()

        # Hack: Force Singleton to point to our new local instance
        MetaRegistry._instance = tier_registry
        MetaRegistry._instance.owner_pid = os.getpid()

        tasks = []
        BATCH_SIZE = 1  # Keep 1 for smooth progress bar updates
        for p1, p2 in matchups:
            remaining = n_games
            while remaining > 0:
                current = min(remaining, BATCH_SIZE)
                tasks.append((p1, p2, current, args.verbose, iterations))
                remaining -= current

        # 2. Run with Progress Bar
        with tqdm(total=total_tier_games, unit="game") as pbar:
            def callback(result):
                res_data, n = result
                tier_registry.merge_data(res_data)
                pbar.update(n)

            if args.procs > 1:
                with multiprocessing.Pool(processes=args.procs) as pool:
                    for t in tasks:
                        pool.apply_async(run_batch, args=(t,), callback=callback)
                    pool.close()
                    pool.join()
            else:
                for t in tasks:
                    res = run_batch(t)
                    callback(res)

        # 3. Save specific file
        filename = f"meta_stats_{tier_name.lower()}.json"
        tier_registry.save(filename)
        print(f"Saved data to: {filename}")


if __name__ == "__main__":
    main()