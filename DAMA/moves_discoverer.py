from typing import Any

from core.card import Card, EquipCard, WeaponCard, CantripCard
from core.enums import Actions, CardType, Phases
from core.game import Game


def get_moves(pid: int, g: Game) -> list[tuple[Card | EquipCard | WeaponCard | CantripCard | None, dict[str, Any]]]:
    p = g.players[pid]
    action_list = g.outputLegalActions(pid)
    moves = []

    # --- PRIORITY 1: Mandatory Actions (Blocking) ---
    # If these exist, we MUST do them. We return immediately to avoid generating invalid parallel moves.

    if Actions.CHOOSE_REWARD in action_list:
        for i, card in enumerate(p.choice_candidates):
            moves.append((card, {'action': Actions.CHOOSE_REWARD, 'args': {'index': i, 'card_name': card.name}}))
        return moves

    if Actions.DISCARD in action_list:
        # Mandatory discard (End phase or pending effect)
        for i, card in enumerate(p.hand):
            moves.append((None, {'action': Actions.DISCARD, 'args': {'index': i, 'card_name': card.name}}))
        return moves

    # --- PRIORITY 2: Global Actions ---

    if Actions.PASS_PHASE in action_list:
        moves.append((None, {'action': Actions.PASS_PHASE, 'args': {}}))
    if Actions.MULLIGAN in action_list:
        moves.append((None, {'action': Actions.MULLIGAN, 'args': {}}))
    if Actions.ATTACK in action_list and p.hasCombatAction and "Nullified" not in p.statuses:
        moves.append((None, {'action': Actions.ATTACK, 'args': {}}))
    if Actions.DRAW in action_list:
        moves.append((None, {'action': Actions.DRAW, 'args': {}}))

    # --- PRIORITY 3: Hand Actions ---

    for i, card in enumerate(p.hand):

        # LEARN (Preparation Phase)
        if Actions.LEARN in action_list:
            is_valid_learn = False
            if g.phase == Phases.PREPARATION:
                if card.cardType in [CardType.SKILL, CardType.INSTANT]:
                    if None in p.skillSlots:
                        is_valid_learn = True
                elif card.cardType == CardType.ADVANCED:
                    if p.level >= 5:
                        is_valid_learn = True

            if is_valid_learn:
                moves.append((card, {'action': Actions.LEARN, 'args': {'index': i, 'card_name': card.name}}))

        # CAST (Duel Phase - Cantrips)
        if Actions.CAST in action_list and card.cardType == CardType.CANTRIP:
            if g.phase == Phases.DUEL:
                if card.level <= p.level:
                    if card.ChoiceLabels:
                        for choice_id in range(len(card.ChoiceLabels)):
                            moves.append((
                                card,
                                {
                                    'action': Actions.CAST,
                                    'args': {'index': i, 'card_name': card.name, 'choice': choice_id}
                                }
                            ))
                    else:
                        moves.append((
                            card,
                            {'action': Actions.CAST, 'args': {'index': i, 'card_name': card.name}}
                        ))

        # EQUIP (Duel Phase)
        if Actions.EQUIP in action_list:
            args = {'index': i, 'card_name': card.name, 'slot': card.cardType}
            # Pre-filter optimization to avoid building dicts for non-equips (optional but good)
            # But keeping strictly to "Ask Don't Guess", we just ask.
            check = g.is_action_valid(g.isPlaying, Actions.EQUIP, args)
            if check['valid']:
                moves.append((card, {'action': Actions.EQUIP, 'args': args}))

    # --- PRIORITY 4: Board Actions (Skills / Equipment) ---
    
    if Actions.ACTIVATE in action_list:
        # Skills
        for i, skill in enumerate(p.skillSlots):
            if not skill: continue

            # Check for Multi-Choice
            if skill.ChoiceLabels:
                for choice_id in range(len(skill.ChoiceLabels)):
                    args = {'source': 'SKILL', 'index': i, 'choice': choice_id}
                    if g.is_action_valid(g.isPlaying, Actions.ACTIVATE, args)['valid']:
                        moves.append((skill, {'action': Actions.ACTIVATE, 'args': args}))
            else:
                args = {'source': 'SKILL', 'index': i}
                if g.is_action_valid(g.isPlaying, Actions.ACTIVATE, args)['valid']:
                    moves.append((skill, {'action': Actions.ACTIVATE, 'args': args}))

        # Equipment
        for slot, card in p.equippedCards.items():
            if card and card.OnActivate:
                if card.ChoiceLabels:
                    for choice_id in range(len(card.ChoiceLabels)):
                        args = {'source': 'EQUIP', 'slot': slot, 'choice': choice_id}
                        if g.is_action_valid(g.isPlaying, Actions.ACTIVATE, args)['valid']:
                            moves.append((card, {'action': Actions.ACTIVATE, 'args': args}))
                else:
                    args = {'source': 'EQUIP', 'slot': slot}
                    if g.is_action_valid(g.isPlaying, Actions.ACTIVATE, args)['valid']:
                        moves.append((card, {'action': Actions.ACTIVATE, 'args': args}))

    return moves
