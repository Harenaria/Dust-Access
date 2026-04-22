from dataclasses import dataclass
from enum import Enum, auto
from core.game import Game
from core.enums import Winner, Counter, AccessorClass, CardType, CardTag
from DAMA.constants import HeuristicWeights


@dataclass
class ThreatReport:
    lethal_risk: bool = False
    incoming_damage: int = 0
    wall_threat: bool = False  # Enemy Tenacity > My Power
    volatile_threat: bool = False  # My enemy has volatile buffs that I can disable


class HeuristicAnalyzer:

    @staticmethod
    def predict_damage(power: int, tenacity: int) -> int:
        margin = power - tenacity
        return margin if margin > 0 else 1

    @staticmethod
    def analyze_threats(state: Game, my_id: int) -> ThreatReport:
        report = ThreatReport()
        opp_id = 1 - my_id
        me = state.players[my_id]
        opp = state.players[opp_id]

        # Incoming Damage Prediction (Can I survive?)
        # Predicted damage: Enemy's Power vs My Tenacity
        weapon_dmg = HeuristicAnalyzer.predict_damage(opp.currentPower, me.currentTenacity)

        report.incoming_damage = weapon_dmg
        if weapon_dmg >= me.currentHP: report.lethal_risk = True

        # Offensive "Wall" Check (Can I hurt them?)
        # My Power vs Enemy's Tenacity
        my_dmg = HeuristicAnalyzer.predict_damage(me.currentPower, opp.currentTenacity)
        if my_dmg <= 1: report.wall_threat = True

        # Enemy has volatile resources that I could disable
        if state.players[opp_id].counters.count(Counter.RAGE) > 0:
            report.volatile_threat = True

        return report

    @staticmethod
    def evaluate_mulligan(state: Game, player_id: int) -> float:
        """
        Valuta se conviene tenere la mano o rimescolare.
        In Dust Access, l'early game (LV 1-2) è vitale.
        """
        hand = state.players[player_id].hand
        # Conta le carte con Livello 1 o 2 (giocabili subito o al prossimo turno)
        low_level_cards = [c for c in hand if getattr(c, 'level', 1) <= HeuristicWeights.LOW_LEVEL_THRESHOLD]

        # Se abbiamo 0 o 1 carta giocabile, la mano è un "mattone" (brick).
        # Diamo un bonus altissimo all'azione di Mulligan.
        if len(low_level_cards) <= HeuristicWeights.HAND_BRICK_THRESHOLD:
            return HeuristicWeights.MULLIGAN_BONUS

        # Se abbiamo già 3 o più carte giocabili, la mano è ottima.
        # Diamo un malus pesante all'azione di Mulligan per evitarla.
        if len(low_level_cards) >= HeuristicWeights.HAND_HEALTHY_THRESHOLD:
            return HeuristicWeights.MULLIGAN_PENALTY

        return 0.0

    @staticmethod
    def evaluate_state(game: Game, player_id: int) -> float:
        """Represents the chance of winning based on the archetype."""
        if game.winner == Winner(player_id + 1): return 1.0  # Winner enum is 1-indexed
        if game.winner != Winner.NONE: return -1.0

        me = game.players[player_id]
        opp = game.players[1 - player_id]

        # Detect Persona
        persona = me.specialization.accessorClass

        # Base Metrics
        my_dpt = HeuristicAnalyzer.predict_damage(me.currentPower, opp.currentTenacity)
        opp_dpt = HeuristicAnalyzer.predict_damage(opp.currentPower, me.currentTenacity)

        my_ttd = me.currentHP / max(HeuristicWeights.EPSILON, opp_dpt)
        opp_ttd = opp.currentHP / max(HeuristicWeights.EPSILON, my_dpt)

        hp_diff_ratio = (me.currentHP - opp.currentHP) / max(1, me.currentDurability)

        # Archetype Specific Weights
        score = 0.0

        if persona == AccessorClass.HEAVY:
            # AGGRO: Kill fast. High value on lowering Enemy HP/TTD.
            if my_ttd > opp_ttd:
                score = 1.0 - (opp_ttd / (my_ttd + 0.1))
            else:
                score = -1.0 + (my_ttd / (opp_ttd + 0.1))

            # Bonus for Rage maintenance
            if Counter.RAGE in me.counters: score += HeuristicWeights.HEAVY_RAGE_BONUS

        elif persona == AccessorClass.MEDIUM:
            # MIDRANGE: Balance.
            race_score = 0
            if my_ttd > opp_ttd:
                race_score = 0.5
            else:
                race_score = -0.5

            # Value board/resources more
            resource_score = (len(me.hand) - len(opp.hand)) * HeuristicWeights.MEDIUM_RESOURCE_SCALAR
            score = race_score + resource_score + (hp_diff_ratio * HeuristicWeights.MEDIUM_HP_DIFF_SCALAR)

        elif persona == AccessorClass.LIGHT:
            # CONTROL: Survive early, crush late.
            is_late_game = me.level >= HeuristicWeights.LIGHT_LATE_GAME_LEVEL

            if is_late_game:
                # GAP CLOSING MODE
                if my_ttd > opp_ttd:
                    score = 1.0 - (opp_ttd / (my_ttd + HeuristicWeights.EPSILON))
                else:
                    score = -1.0 + (my_ttd / (opp_ttd + HeuristicWeights.EPSILON))
            else:
                # SURVIVAL MODE
                survival_score = me.currentHP / me.currentDurability
                card_adv = (len(me.hand) - len(opp.hand)) * HeuristicWeights.LIGHT_CARD_ADV_SCALAR
                score = survival_score + card_adv

        return max(-1.0, min(1.0, score))

    @staticmethod
    def get_micro_heuristic_bonus(card, action_args, state: Game, player_id: int, weights_cache: dict = None) -> float:
        """Expert-level heuristic bonus considering Tempo, Ramping, Snowballing, and Persona."""
        bonus = 0.0
        me = state.players[player_id]
        opp = state.players[1 - player_id]
        if not card: return 0.0

        persona = me.specialization.accessorClass
        tags = card.tags
        card_name = getattr(card, 'name', '')

        # --- COMBO & CHAINS (Sequencing) ---
        if me.chainedSkillName == card_name:
            bonus += HeuristicWeights.CHAIN_COMPLETION_BONUS  # Peak priority: finish the chain

        # If card has a Chain successor, bonus for having the chance to chain it
        if CardTag.COMBO in tags:
            chains_with = getattr(card, 'ChainsWith', None)
            if chains_with and any(c.name == chains_with for c in (me.hand + [s for s in me.skillSlots if s])):
                bonus += HeuristicWeights.CHAIN_POTENTIAL_BONUS

            # Set Piece Logic: Check if the card calls checkEquipSet
            if "checkEquipSet" in getattr(card, 'called_methods', set()):
                valors_equipped = sum(1 for c in me.equippedCards.values() if c and "Valor" in c.name)
                if valors_equipped == 1 and "Valor" in card_name:
                    bonus += HeuristicWeights.SET_PIECE_BONUS

        # --- RAMPING & SNOWBALLING ---
        # Early Game: Ramp up, Late Game: Diminish returns
        # (It's supposed that in Late you already have enough resources and have to focus on using them)
        is_early_game = state.turn <= HeuristicWeights.EARLY_GAME_TURN_LIMIT
        if is_early_game:
            if CardTag.GENERATOR in tags:
                # Ramping: Get resources early (especially Heavy/Medium)
                bonus += HeuristicWeights.EARLY_RAMP_BONUS
            if CardTag.SCALER in tags:
                # Snowballing: Permanent buffs are better early
                # Light (Scaling) players prioritize these even more
                if persona == AccessorClass.LIGHT:
                    bonus += HeuristicWeights.EARLY_SCALING_BONUS_LIGHT
                else:
                    bonus += HeuristicWeights.EARLY_SCALING_BONUS_GENERIC
        else:
            if CardTag.GENERATOR in tags and len(me.hand) > HeuristicWeights.LATE_GAME_HAND_SIZE:
                # Diminishing returns on draw generators late game
                bonus += HeuristicWeights.LATE_GAME_GENERATOR_PENALTY

        # --- TEMPO (Immediate Impact) ---
        # Tempo is most critical when HP is low or for Aggro personas
        is_lethal_range = opp.currentHP / max(1, opp.currentDurability) < HeuristicWeights.LETHAL_HP_RATIO

        tempo_val = 0.0
        if CardTag.FINISHER in tags:
            # Finisher Discipline: Optimizing for impact
            if is_lethal_range:
                tempo_val += HeuristicWeights.FINISHER_LETHAL_BONUS
            else:
                tempo_val += HeuristicWeights.FINISHER_EARLY_PENALTY  # Constant is negative

        if CardTag.DEFENSIVE in tags and (
                me.currentHP / max(1, me.currentDurability) < HeuristicWeights.SURVIVAL_HP_RATIO):
            tempo_val += HeuristicWeights.SURVIVAL_TEMPO_BONUS  # Survival tempo

        # Persona Scaling for Tempo
        if persona == AccessorClass.HEAVY:
            bonus += tempo_val * HeuristicWeights.AGGRO_TEMPO_MULTIPLIER  # Aggro values tempo more
        else:
            bonus += tempo_val

        # --- META-COUNTERING ---
        if CardTag.COUNTER in tags and weights_cache:
            for equip in opp.equippedCards.values():
                if equip:
                    # Use cache passed from the MCTS tree to avoid millions of singleton/lock calls
                    if equip.name in weights_cache:
                        bias, _ = weights_cache[equip.name]
                        if bias > HeuristicWeights.META_COUNTER_THRESHOLD:  # Opponent has a meta-powerhouse
                            bonus += HeuristicWeights.META_COUNTER_BONUS
                            break

        # --- RESOURCE EFFICIENCY ---
        # Generator sequencing
        has_low_rage = me.counters.count(Counter.RAGE) < HeuristicWeights.LOW_RAGE_THRESHOLD
        if has_low_rage and CardTag.GENERATOR in tags:
            bonus += HeuristicWeights.LOW_RAGE_GENERATOR_BONUS
        if not has_low_rage and CardTag.CONSUMER in tags:
            bonus += HeuristicWeights.HIGH_RAGE_CONSUMER_BONUS

        # --- PREREQUISITE CHECK ---
        prereq_mult = state.check_requirements(player_id, card)
        if prereq_mult < HeuristicWeights.PREREQ_MIN_THRESHOLD:
            return HeuristicWeights.PREREQ_FAIL_PENALTY  # Hard penalty: don't use this card without prerequisites
        bonus *= prereq_mult  # Scale all bonuses by prerequisite satisfaction

        return bonus
