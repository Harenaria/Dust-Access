from typing import Any

from mcts.tree import Node


def extract_from_path(path: list[Node]) -> dict[Any, Any] | None:
    if not path: return {}
    final_node = path[-1]
    winner = final_node.state.winner
    p1 = path[0].state.players[0]
    p2 = path[0].state.players[1]
    game_summary = {
        "winner": winner.name,
        "total_turns": final_node.state.turn,
        "p1_class": p1.specialization.accessorClass,
        "p2_class": p2.specialization.accessorClass,
        "moves": []
    }
    for node in path:
        if node.move is None: continue
        card_obj, action_dict = node.move if node.move else (None, {})
        state = node.state
        move_data = {
            "turn": node.state.turn,
            "phase": node.state.phase.name,
            "pid": 1-state.isPlaying,
            "action": action_dict['action'],
            "card_name": card_obj.name if card_obj else "",
            "card_type": card_obj.cardType if card_obj else ""
        }
        game_summary["moves"].append(move_data)

    return game_summary