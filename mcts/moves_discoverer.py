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
    # Iterate the hand exactly ONCE for efficiency

    for i, card in enumerate(p.hand):

        # 1. LEARN (Preparation Phase)
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

        # 2. CAST (Duel Phase - Cantrips)
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

        # 3. EQUIP (Duel Phase)
        if Actions.EQUIP in action_list and p.hasTacticalAction:
            if g.phase == Phases.DUEL:
                is_equip_type = (card.cardType in
                                 [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND,
                                  CardType.HEAD, CardType.CHEST, CardType.BRACERS, CardType.BOOTS])

                if is_equip_type and p.level >= card.level:
                    # Validate Dual Wielding Logic
                    weapon = p.equippedCards.get(CardType.WEAPON)
                    is_dual_equipped = weapon is not None and weapon.cardType == CardType.DUAL

                    # Cannot equip Off-Hand if holding 2H Weapon
                    if not (card.cardType == CardType.OFF_HAND and is_dual_equipped):
                        moves.append((
                            card,
                            {'action': Actions.EQUIP,
                             'args': {'index': i, 'card_name': card.name, 'slot': card.cardType}}
                        ))

    # --- PRIORITY 4: Board Actions (Skills / Equipment) ---

    if Actions.ACTIVATE in action_list and "Nullified" not in p.statuses:
        # Skills
        for i, skill in enumerate(p.skillSlots):
            if skill and skill.currentCD == 0:
                is_chained = (p.chainedSkillName == skill.name)
                can_activate = p.hasTacticalAction or skill.cardType == CardType.INSTANT or is_chained
                if can_activate:
                    effect_field = "OnChainActivate" if is_chained and skill.OnChainActivate else "OnActivate"
                    effects = getattr(skill, effect_field, [])
                    if skill.ChoiceLabels and len(effects) > 1:
                        for choice_id in range(len(skill.ChoiceLabels)):
                            moves.append((
                                p.skillSlots[i],
                                {
                                    'action': Actions.ACTIVATE,
                                    'args': {'source': 'SKILL', 'index': i, 'choice': choice_id}
                                }
                            ))
                    else:
                        moves.append((skill, {'action': Actions.ACTIVATE, 'args': {'source': 'SKILL', 'index': i}}))

        # Equipment
        for slot, card in p.equippedCards.items():
            if card and card.OnActivate:
                is_combat_item = card.cardType in [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND]
                can_activate = (is_combat_item and p.hasCombatAction) or (not is_combat_item and p.hasTacticalAction)
                if can_activate:
                    moves.append((
                        card,
                        {
                            'action': Actions.ACTIVATE,
                            'args': {'source': 'EQUIP', 'slot': slot}
                        }
                    ))

    return moves