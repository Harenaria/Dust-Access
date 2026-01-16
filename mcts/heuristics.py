from dataclasses import dataclass
from enum import Enum, auto
from core.game import Game
from core.enums import Winner, Counter, AccessorClass, CardType


class CardTag(Enum):
    GENERATOR = auto()  # Rage, Kai, Draw
    CONSUMER = auto()   # Scales with Rage/Kai
    FINISHER = auto()    # Level 5+ or high damage
    DEFENSIVE = auto()   # Heal, Tenacity, Shield
    COUNTER = auto()     # Nullify, Discard, Unequip
    SCALER = auto()      # Permanent stat buffs
    COMBO = auto()       # Chains or Sets


@dataclass
class ThreatReport:
    lethal_risk: bool = False
    incoming_damage: int = 0
    wall_threat: bool = False  # Enemy Tenacity > My Power
    volatile_threat: bool = False  # My enemy has volatile buffs that I can disable


class HeuristicAnalyzer:
    _tag_cache = {}

    @staticmethod
    def _tag_card(card) -> set[CardTag]:
        """Categorizes a card into functional tags for faster heuristic evaluation."""
        name = getattr(card, 'name', 'Unknown')
        if name in HeuristicAnalyzer._tag_cache:
            return HeuristicAnalyzer._tag_cache[name]

        tags = set()
        on_play = str(getattr(card, 'OnPlay', ''))
        on_activate = str(getattr(card, 'OnActivate', ''))
        effects = on_play + on_activate
        
        # Generator
        if any(x in effects for x in ["Rage", "Kai", "Draw", "Refill"]):
            tags.add(CardTag.GENERATOR)
        
        # Consumer (Heuristic: usually cards with AtkStat or specific scaling mentions)
        if hasattr(card, 'AtkStat') or "Scale" in effects:
            tags.add(CardTag.CONSUMER)
            
        # Finisher
        if getattr(card, 'level', 1) >= 5 or "Lethal" in effects:
            tags.add(CardTag.FINISHER)
            
        # Defensive
        if any(x in effects for x in ["Heal", "Tenacity", "Shield", "Cover"]):
            tags.add(CardTag.DEFENSIVE)
            
        # Counter
        if any(x in effects for x in ["Nullify", "Discard", "Unequip", "Rust"]):
            tags.add(CardTag.COUNTER)
            
        # Scaler
        if any(x in effects for x in ["Permanent", "PowerIncrease", "TenacityIncrease"]):
            tags.add(CardTag.SCALER)
            
        # Combo
        if getattr(card, 'ChainsWith', None) or "Set:" in effects:
            tags.add(CardTag.COMBO)

        HeuristicAnalyzer._tag_cache[name] = tags
        return tags

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

        # Damage prediction
        weapon_dmg = HeuristicAnalyzer.predict_damage(me.currentPower, me.currentTenacity)
        
        report.incoming_damage = weapon_dmg
        if weapon_dmg >= me.currentHP: report.lethal_risk = True

        # Enemy is "walling" me
        my_dmg = HeuristicAnalyzer.predict_damage(me.currentPower, me.currentTenacity)
        if my_dmg == 1: report.wall_threat = True

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
        low_level_cards = [c for c in hand if getattr(c, 'level', 1) <= 2]

        # Se abbiamo 0 o 1 carta giocabile, la mano è un "mattone" (brick).
        # Diamo un bonus altissimo all'azione di Mulligan.
        if len(low_level_cards) <= 1:
            return 800.0

            # Se abbiamo già 3 o più carte giocabili, la mano è ottima.
        # Diamo un malus pesante all'azione di Mulligan per evitarla.
        if len(low_level_cards) >= 3:
            return -800.0

        return 0.0

    @staticmethod
    def evaluate_state(game: Game, player_id: int) -> float:
        """Represents the chance of winning based on the archetype."""
        if game.winner == Winner(player_id + 1): return 1.0 # Winner enum is 1-indexed
        if game.winner != Winner.NONE: return -1.0

        me = game.players[player_id]
        opp = game.players[1 - player_id]
        
        # Detect Persona
        persona = me.specialization.accessorClass
        
        # Base Metrics
        my_dpt = HeuristicAnalyzer.predict_damage(me.currentPower, opp.currentTenacity)
        opp_dpt = HeuristicAnalyzer.predict_damage(opp.currentPower, me.currentTenacity)
        
        my_ttd = me.currentHP / max(0.1, opp_dpt)
        opp_ttd = opp.currentHP / max(0.1, my_dpt)
        
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
            if Counter.RAGE in me.counters: score += 0.1
            
        elif persona == AccessorClass.MEDIUM:
            # MIDRANGE: Balance.
            race_score = 0
            if my_ttd > opp_ttd:
                race_score = 0.5
            else:
                race_score = -0.5
                
            # Value board/resources more
            resource_score = (len(me.hand) - len(opp.hand)) * 0.05
            score = race_score + resource_score + (hp_diff_ratio * 0.5)

        elif persona == AccessorClass.LIGHT:
            # CONTROL: Survive early, crush late.
            is_late_game = me.level >= 7
            
            if is_late_game:
                # GAP CLOSING MODE
                 if my_ttd > opp_ttd:
                    score = 1.0 - (opp_ttd / (my_ttd + 0.1))
                 else:
                    score = -1.0 + (my_ttd / (opp_ttd + 0.1))
            else:
                # SURVIVAL MODE
                survival_score = me.currentHP / me.currentDurability
                card_adv = (len(me.hand) - len(opp.hand)) * 0.1
                score = survival_score + card_adv

        return max(-1.0, min(1.0, score))

    @staticmethod
    def get_micro_heuristic_bonus(card, action_args, state: Game, player_id: int, weights_cache: dict = None) -> float:
        """Expert-level heuristic bonus considering Tempo, Ramping, Snowballing, and Persona."""
        bonus = 0.0
        me = state.players[player_id]
        opp = state.players[1 - player_id]
        persona = me.specialization.accessorClass
        tags = HeuristicAnalyzer._tag_card(card)
        card_name = getattr(card, 'name', '')
        
        # --- 1. COMBO & CHAINS (Human-like sequencing) ---
        if me.chainedSkillName == card_name:
            bonus += 600.0 # Peak priority: finish the chain

        if CardTag.COMBO in tags:
            chains_with = getattr(card, 'ChainsWith', None)
            if chains_with and any(c.name == chains_with for c in (me.hand + [s for s in me.skillSlots if s])):
                bonus += 120.0
            # Set Piece Logic
            if "Set:" in str(getattr(card, 'OnPlay', '')):
                 valors_equipped = sum(1 for c in me.equippedCards.values() if c and "Valor" in c.name)
                 if valors_equipped == 1 and "Valor" in card_name:
                     bonus += 100.0

        # --- 2. RAMPING & SNOWBALLING (Early Game focus) ---
        is_early_game = state.turn <= 5
        if is_early_game:
            if CardTag.GENERATOR in tags:
                 # Ramping: Get resources early (especially Heavy/Medium)
                 bonus += 80.0
            if CardTag.SCALER in tags:
                 # Snowballing: Permanent buffs are better early
                 # Light (Scaling) players prioritize these even more
                 if persona == AccessorClass.LIGHT:
                     bonus += 120.0 
                 else:
                     bonus += 60.0
        else:
            if CardTag.GENERATOR in tags and len(me.hand) > 4:
                 # Diminishing returns on draw generators late game
                 bonus -= 20.0

        # --- 3. TEMPO (Immediate Impact) ---
        # Tempo is most critical when HP is low or for Aggro personas
        is_lethal_range = opp.currentHP / opp.currentDurability < 0.4
        
        tempo_val = 0.0
        if CardTag.FINISHER in tags:
            # Finisher Discipline: Optimizing for impact
            if is_lethal_range:
                tempo_val += 150.0
            else:
                tempo_val -= 40.0 # Don't waste early
        
        if CardTag.DEFENSIVE in tags and (me.currentHP / me.currentDurability < 0.3):
             tempo_val += 120.0 # Survival tempo

        # Persona Scaling for Tempo
        if persona == AccessorClass.HEAVY:
            bonus += tempo_val * 1.5 # Aggro values tempo 1.5x more
        else:
            bonus += tempo_val

        # --- 4. META-COUNTERING ---
        if CardTag.COUNTER in tags and weights_cache:
            for equip in opp.equippedCards.values():
                if equip:
                    # Use cache passed from MCTS tree to avoid millions of singleton/lock calls
                    if equip.name in weights_cache:
                        bias, _ = weights_cache[equip.name]
                        if bias > 20.0: # Opponent has a meta-powerhouse
                            bonus += 150.0
                            break

        # --- 5. RESOURCE EFFICIENCY ---
        # Generator sequencing
        has_low_rage = me.counters.count(Counter.RAGE) < 2
        if has_low_rage and CardTag.GENERATOR in tags:
            bonus += 40.0
        if not has_low_rage and CardTag.CONSUMER in tags:
            bonus += 30.0

        # --- 6. PREREQUISITE CHECK (Declarative from Requires field) ---
        prereq_mult = HeuristicAnalyzer.check_prerequisites(card, state, player_id)
        if prereq_mult < 0.1:
            return -500.0  # Hard penalty: don't use this card without prerequisites
        bonus *= prereq_mult  # Scale all bonuses by prerequisite satisfaction

        return bonus

    @staticmethod
    def check_prerequisites(card, state: Game, player_id: int) -> float:
        """
        Returns a multiplier (0.0 to 1.0) based on prerequisite satisfaction.
        0.0 = prerequisites NOT met, do not use this card
        1.0 = all prerequisites met
        0.5 = partial (e.g., missing 1 of 2 required counters)
        """
        requires = getattr(card, 'Requires', '') or ''
        me = state.players[player_id]
        
        # Auto-detect chain setup requirement from ChainsWith
        chains_with = getattr(card, 'ChainsWith', '')
        if chains_with:
            target_available = any(
                c.name == chains_with 
                for c in (me.hand + [s for s in me.skillSlots if s])
            )
            if not target_available:
                # Chain target not available - reduced value but not zero
                # (Card still has base value without the chain)
                if not requires:
                    return 0.4  # Partial value without chain target
        
        if not requires:
            return 1.0  # No explicit requirements
        
        clauses = [r.strip() for r in requires.split('&&')]
        
        for clause in clauses:
            if clause == '2H':
                weapon = me.equippedCards.get(CardType.WEAPON)
                if not (weapon and getattr(weapon, 'is2Handed', False)):
                    return 0.0  # Hard fail - 2H weapon required
            
            elif clause.startswith('Counter:'):
                # Format: Counter:RAGE:2
                parts = clause.split(':')
                try:
                    counter_name = parts[1].upper()
                    counter_type = Counter[counter_name]
                    required_count = int(parts[2]) if len(parts) > 2 else 1
                    actual_count = me.counters.count(counter_type)
                    if actual_count < required_count:
                        return actual_count / required_count  # Partial satisfaction
                except (KeyError, ValueError, IndexError):
                    pass  # Invalid counter spec, ignore
            
            elif clause.startswith('Equip:'):
                # Format: Equip:OFF_HAND or Equip:WEAPON
                slot_name = clause.split(':')[1].upper()
                try:
                    slot = CardType[slot_name]
                    if me.equippedCards.get(slot) is None:
                        return 0.0  # Required equipment not present
                except (KeyError, ValueError, IndexError):
                    pass  # Invalid slot name, ignore
            
            elif clause.startswith('UsedAction:'):
                # Format: UsedAction:Tactical or UsedAction:Combat or UsedAction:Tactical&&Combat
                action_type = clause.split(':')[1]
                if 'Tactical' in action_type and me.hasTacticalAction:
                    return 0.0  # Card only useful if tactical already used
                if 'Combat' in action_type and me.hasCombatAction:
                    return 0.0  # Card only useful if combat already used
            
            elif clause.startswith('HP:'):
                # Format: HP:>50% or HP:<30%
                condition = clause[3:]
                hp_percent = (me.currentHP / me.currentDurability) * 100 if me.currentDurability > 0 else 0
                try:
                    if condition.startswith('>'):
                        threshold = float(condition[1:].rstrip('%'))
                        if hp_percent <= threshold:
                            return 0.0
                    elif condition.startswith('<'):
                        threshold = float(condition[1:].rstrip('%'))
                        if hp_percent >= threshold:
                            return 0.0
                except ValueError:
                    pass  # Invalid HP spec, ignore
        
        return 1.0