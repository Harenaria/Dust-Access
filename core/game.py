from dataclasses import dataclass, field
from typing import List, Dict, Any

from core.card import WeaponCard
from core.effects import Effects
from core.enums import Winner, Phases, Actions, CardType, Scaling, Counter
from core.game_logs import GameLogger, LogEntry
from core.player import Player
from core.serialization import DataclassJSONCapable


def matchCreator(room:str, name1: str, deck1: int, spec1: str, name2: str, deck2: int, spec2: str):
    p1 = Player.create_new(True, name1, deck1, spec1)
    p2 = Player.create_new(False, name2, deck2, spec2)

    return Game(room, [p1, p2])

@dataclass
class Game(DataclassJSONCapable):
    room: str
    players: List[Player]
    turn: int = 1
    arePlayersReady: List[bool] = field(default_factory=lambda: [False, False])
    isPlaying: int = 0
    hasMulligan: List[bool] = field(default_factory=lambda: [False, False])
    ready_in_setup: List[bool] = field(default_factory=lambda: [False, False])
    phase: Phases = Phases.SETUP
    winner: Winner = Winner.NONE
    logs: GameLogger = None
    spec_effect_triggered: bool = False

    def __post_init__(self):
        # Initialize internal logic objects
        if isinstance(self.logs, dict):
            self.logs = GameLogger.dict_deserializer(self.logs)
        elif self.logs is None:
            self.logs = GameLogger(self.room, [])

        if isinstance(self.phase, str):
            self.phase = Phases[self.phase] if self.phase in Phases.__members__ else Phases(self.phase)
        if isinstance(self.winner, str):
            self.winner = Winner[self.winner] if self.winner in Winner.__members__ else Winner(self.winner)

        self.effectResolver = Effects()
        self.current_action_args = {}

        raw_players: Any = self.players

        if raw_players and isinstance(raw_players[0], dict):
            self.players = [Player(**p) for p in raw_players]

        # Only run the startup logic if this is a fresh game (Phase SETUP, Turn 1, Empty Hands).
        # This prevents the client from running game logic when deserializing an existing state.
        if self.phase == Phases.SETUP and self.turn == 1 and all(len(p.hand) == 0 for p in self.players):
            self.nextPhase()

    def nextPhase(self):
        match self.phase:
            case Phases.SETUP:
                if len(self.players[0].hand) == 0:
                    self._deal_init_hand(0)
                    self._deal_init_hand(1)
                    return
                self.phase = Phases.START
                self._handle_start_phase_logic()
                self.nextPhase()  # Auto-advance: START -> LOOT

            case Phases.START:
                self.phase = Phases.LOOT
                self._handle_loot_phase_logic()
                self.nextPhase()  # Auto-advance: LOOT -> PREP

            case Phases.LOOT:
                self.phase = Phases.PREPARATION
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"--- Turn: {self.turn} (Player: {int(self.isPlaying+1)}), Phase: {self.phase.name} ---"
                ))

            case Phases.PREPARATION:
                self.phase = Phases.DUEL
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"--- Turn: {self.turn} (Player: {int(self.isPlaying + 1)}), Phase: {self.phase.name} ---"
                ))

            case Phases.DUEL:
                self.phase = Phases.END
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"--- Turn: {self.turn} (Player: {int(self.isPlaying + 1)}), Phase: {self.phase.name} ---"
                ))
                self.nextPhase()

            case Phases.END:
                player = self.players[self.isPlaying]

                if len(player.hand) > 5:
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"System: {player.accessorName} must discard {len(player.hand) - 5} card(s)."
                    ))
                    return
                self._handle_end_phase_logic()

                self.isPlaying = 1 - self.isPlaying

                # Check turn increment
                self.turn += 1
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"--- Turn {self.turn} starts. Player {int(self.isPlaying + 1)} will be playing.---"
                ))

                self.phase = Phases.START
                self._handle_start_phase_logic()
                self.nextPhase()

    def receiveAction(self, player: int, action: Actions, args: Dict[str, Any]):
        if self.winner != Winner.NONE:
            return {"valid": False, "error": "Game Over"}

        if player != self.isPlaying and self.phase != Phases.SETUP:
            if action != Actions.CHOOSE_REWARD:
                return {"valid": False, "error": "Not your turn"}

        current_player = self.players[player]
        self.current_action_args = args

        if current_player.pending_discard > 0:
            if action != Actions.DISCARD:
                return {"valid": False, "error": f"You must discard {current_player.pending_discard} card(s) first!"}

            # Handle the discard logic specifically for pending
            if args['index'] >= len(current_player.hand): return {"valid": False, "error": "Idx"}
            card = current_player.hand.pop(args['index'])
            current_player.pending_discard -= 1
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"{current_player.accessorName} discarded {card.name}."
            ))
            return {"valid": True}

        match action:
            case Actions.PASS_PHASE:
                if self.phase == Phases.SETUP:
                    self.ready_in_setup[player] = True
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"{current_player.accessorName} is ready!"
                    ))

                    if self.ready_in_setup[0] and self.ready_in_setup[1]:
                        if not self.spec_effect_triggered:
                            self.spec_effect_triggered = True
                            for i in range(2):
                                p = self.players[i]
                                if p.specialization.onGameBegins:
                                    old_p = self.isPlaying
                                    self.isPlaying = i
                                    self.effectResolver.resolve(p.specialization.onGameBegins, self)
                                    self.isPlaying = old_p

                        if any(p.choice_pending for p in self.players):
                            return {"valid": True, "message": "Resolve choices first!"}
                        self.isPlaying = 0
                        self.nextPhase()
                        return {"valid": True, "message": "Starting..."}
                    else:
                        # self.isPlaying = 1 - player  <-- Removed to allow simultaneous setup
                        self.logs.append(LogEntry(
                            self.turn,
                            self.isPlaying,
                            self.phase,
                            f"System: Waiting for opponent..."
                        ))
                        return {"valid": True, "message": "Waiting for opponent..."}

                elif self.phase in [Phases.PREPARATION, Phases.DUEL]:
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"{current_player.accessorName} passed phase {self.phase.name}."
                    ))
                    self.nextPhase()
                    return {"valid": True}

                elif self.phase == Phases.END:
                    if len(current_player.hand) <= 5:
                        self.logs.append(LogEntry(
                            self.turn,
                            self.isPlaying,
                            self.phase,
                            f"{current_player.accessorName} passed the turn."
                        ))
                        self.nextPhase()
                        return {"valid": True}
                    else:
                        return {"valid": False, "error": "You must discard down to 5 cards first"}

                return {"valid": False, "error": "Cannot pass phase now"}

            case Actions.DISCARD:
                if self.phase != Phases.END:
                    return {"valid": False, "error": "Can only discard in End phase"}
                if len(current_player.hand) <= 5:
                    return {"valid": False, "error": "Hand size OK"}

                if args['index'] >= len(current_player.hand): return {"valid": False, "error": "Idx"}
                card = current_player.hand.pop(args['index'])
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"{current_player.accessorName} discarded {card.name}."
                ))
                if current_player.pending_discard > 0:
                    current_player.pending_discard -= 1

                return {"valid": True}

            case Actions.MULLIGAN:
                if self.phase != Phases.SETUP:
                    return {"valid": False, "error": "You can't mulligan in this phase"}
                if self.hasMulligan[player]:
                    return {"valid": False, "error": "You've already used your mulligan"}
                self.hasMulligan[player] = True
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"{current_player.accessorName} used their mulligan."
                ))
                return self._deal_init_hand(player)

            case Actions.PLAY:
                if args['index'] >= len(current_player.hand): return {"valid": False, "error": "Invalid index"}
                card_to_play = current_player.hand[args['index']]

                # Skill Placement
                if self.phase == Phases.PREPARATION:
                    if card_to_play.cardType in [CardType.SKILL, CardType.INSTANT]:
                        if None in current_player.skillSlots:
                            card = current_player.hand.pop(args['index'])
                            idx = current_player.skillSlots.index(None)
                            current_player.skillSlots[idx] = card
                            # Handle multi-effect cards with choice
                            if not(self.multi_effect_resolver(args, card)): return {"valid": False, "error": "Invalid choice"}
                            self.logs.append(LogEntry(
                                self.turn,
                                self.isPlaying,
                                self.phase,
                                f"{current_player.accessorName} placed {card.name} in slot {idx + 1}."
                            ))
                            self._schedule_future_effects(player, card)
                            return {"valid": True}
                        else:
                            return {"valid": False, "error": "Skill slots full. Remove one first."}
                    elif card_to_play.cardType == CardType.ADVANCED:
                        if current_player.level >= 5:
                            self.logs.append(LogEntry(
                                self.turn,
                                self.isPlaying,
                                self.phase,
                                f"{current_player.accessorName} EVOLVED TO {card_to_play.name}."
                            ))
                            return {"valid": True, "message": "Spec Evolved"}
                        return {"valid": False, "error": "Level too low"}
                    else:
                        return {"valid": False, "error": "Can only place Skills or Evolve in Preparation"}

                # Cantrips
                elif self.phase == Phases.DUEL:
                    if card_to_play.cardType == CardType.CANTRIP:
                        card = current_player.hand.pop(args['index'])
                        if card.level > self.players[player].level:
                            return {"valid": False, "error": "Level too low"}
                        # Handle multi-effect cards with choice
                        if not(self.multi_effect_resolver(args, card)): return {"valid": False, "error": "Invalid choice"}
                        self.logs.append(LogEntry(
                            self.turn,
                            self.isPlaying,
                            self.phase,
                            f"{current_player.accessorName} casted the cantrip {card.name}."
                        ))
                        # Cantrips do not consume action, update stats just in case
                        self.recalculateStats(player)
                        self._schedule_future_effects(player, card)
                        return {"valid": True}
                    else:
                        return {"valid": False, "error": "Can only play Cantrips in Duel Phase"}

                else:
                    return {"valid": False, "error": "Cannot Play in this phase"}

            case Actions.EQUIP:
                if self.phase != Phases.DUEL: return {"valid": False, "error": "Can only equip in Duel Phase"}
                if not current_player.hasTacticalAction: return {"valid": False, "error": "No Tactical Actions left"}
                if args['index'] >= len(current_player.hand): return {"valid": False, "error": "Invalid index"}
                card = current_player.hand[args['index']]

                if card.cardType not in [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND, CardType.HEAD,
                                         CardType.CHEST,
                                         CardType.BRACERS, CardType.BOOTS]:
                    return {"valid": False, "error": "Not an equipment"}
                if card.level > self.players[player].level:
                    return {"valid": False, "error": "Level too low"}
                if check := self.checkDual(player, args['index']):
                    return check

                # Equip
                real_card = current_player.hand.pop(args['index'])
                if real_card.cardType.value == CardType.DUAL:
                    current_player.equippedCards[CardType.WEAPON] = real_card
                    current_player.equippedCards[CardType.OFF_HAND] = None
                else:
                    current_player.equippedCards[real_card.cardType.value] = real_card

                # Handle multi-effect cards with choice
                if not(self.multi_effect_resolver(args, card)): return {"valid": False, "error": "Invalid choice"}
                self.recalculateStats(player)
                current_player.hasTacticalAction = False

                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"{current_player.accessorName} equipped {real_card.name}."
                ))
                self._schedule_future_effects(player, real_card)
                return {"valid": True}

            case Actions.ACTIVATE:
                if self.phase != Phases.DUEL: return {"valid": False, "error": "Can only activate in Duel Phase"}
                source_type = args.get('source')

                # Check for Nullified status
                if "Nullified" in current_player.statuses:
                    current_player.statuses.remove("Nullified")
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"{current_player.accessorName} has their action Nullified!"
                    ))
                    if source_type == 'SKILL':
                        idx = args.get('index')
                        target_card = current_player.skillSlots[idx]
                        if target_card is not None and target_card.cardType != CardType.INSTANT:
                            current_player.hasTacticalAction = False
                    elif source_type == 'EQUIP':
                        slot = args.get('slot')
                        if slot in [CardType.WEAPON, CardType.OFF_HAND]:
                            current_player.hasCombatAction = False
                        else:
                            current_player.hasTacticalAction = False
                    return {"valid": True}

                if source_type == 'COUNTER':
                    counter_name = args.get('counter')
                    if counter_name not in current_player.counters:
                        return {"valid": False, "error": f"You don't have a {counter_name} counter"}

                    match counter_name:
                        case 'Momentum':
                            skill_idx = args.get('index')
                            target_skill = current_player.skillSlots[skill_idx] if skill_idx < len(
                                current_player.skillSlots) else None
                            if target_skill:
                                current_player.counters.remove(Counter(counter_name))
                                target_skill.currentCD = 0
                                self.logs.append(LogEntry(
                                    self.turn,
                                    self.isPlaying,
                                    self.phase,
                                    f"{current_player.accessorName} activated {counter_name} on {target_skill.name}!"
                                ))
                                return {"valid": True}
                            return {"valid": False, "error": "Invalid target"}
                        case _:
                            return {"valid": False, "error": f"Counter {counter_name} not activatable"}

                elif source_type == 'SKILL':
                    idx = args.get('index')
                    target_card = current_player.skillSlots[idx]
                    if target_card is None: return {"valid": False, "error": "Slot empty"}
                    if target_card.currentCD > 0: return {"valid": False, "error": "Skill in Cooldown"}
                    
                    is_chained = (current_player.chainedSkillName == target_card.name)

                    if not current_player.hasTacticalAction and target_card.cardType != CardType.INSTANT and not is_chained:
                        return {"valid": False, "error": "No Tactical Actions left"}

                    # Handle multi-effect cards with choice
                    effect_field = "OnChainActivate" if is_chained and target_card.OnChainActivate else "OnActivate"
                    if not(self.multi_effect_resolver(args, target_card, effect_field)): return {"valid": False, "error": "Invalid choice"}
                    
                    # Update chain
                    current_player.chainedSkillName = getattr(target_card, 'ChainsWith', "")
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"{current_player.accessorName} activated {target_card.name}!" + (" (Chained!)" if is_chained else "")
                    ))
                    self._schedule_future_effects(player, target_card)

                elif source_type == 'EQUIP':
                    slot = args.get('slot')
                    target_card = self.players[player].equippedCards[slot]
                    if target_card is None: return {"valid": False, "error": "Slot empty"}

                    if slot in [CardType.WEAPON, CardType.OFF_HAND]:
                        if not current_player.hasCombatAction: return {"valid": False, "error": "No Combat Actions left"}
                    else:
                        if not current_player.hasTacticalAction: return {"valid": False, "error": "No Tactical Actions left"}

                    if slot is not None:
                        # Handle multi-effect cards with choice
                        if target_card.ChoiceLabels and len(target_card.OnActivate) > 1:
                            choice = args.get('choice', 0)
                            if 0 <= choice < len(target_card.OnActivate):
                                self.effectResolver.resolve(target_card.OnActivate[choice], self)
                        else:
                            for effect in target_card.OnActivate:
                                self.effectResolver.resolve(effect, self)
                        self.logs.append(LogEntry(
                            self.turn,
                            self.isPlaying,
                            self.phase,
                            f"{current_player.accessorName} activated {target_card.name}!"
                        ))

                else:
                    return {"valid": False, "error": "Cannot activate that"}

                # Cooldown & Cost
                target_card.currentCD = target_card.cd  # Use 'cd' from property
                if target_card.cardType != CardType.INSTANT:
                    if source_type == 'EQUIP' and slot in [CardType.WEAPON, CardType.OFF_HAND]:
                        current_player.hasCombatAction = False
                    else:
                        current_player.hasTacticalAction = False

                self.recalculateStats(player)
                return {"valid": True}

            case Actions.ATTACK:
                if self.phase != Phases.DUEL: return {"valid": False, "error": "Wrong phase"}
                if not current_player.hasCombatAction: return {"valid": False, "error": "No Combat Actions left"}

                # Attack must also check for Nullified status
                if "Nullified" in current_player.statuses:
                    current_player.statuses.remove("Nullified")
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"{current_player.accessorName} has their attack Nullified!"
                    ))
                    current_player.hasCombatAction = False
                    return {"valid": True}

                damage = self.calcWeaponDamage(player)
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"{current_player.accessorName} attacks! (Tries to deal: {damage} DMG)"
                ))

                final_dmg, is_hit = self.checkDamage(player, damage)

                # OnHit / OnMiss
                weapon = current_player.equippedCards[CardType.WEAPON]
                if weapon:
                    if is_hit:
                        self.effectResolver.resolve(weapon.OnHit, self)
                    else:  # is Mitigated
                        self.effectResolver.resolve(weapon.OnMiss, self)
                        self.effectResolver.resolve('removeAllCounters("Rage")', self)
                else:  # No weapon is counted as a miss.
                    self.effectResolver.resolve('removeAllCounters("Rage")', self)

                current_player.hasCombatAction = False
                self.recalculateStats(player)
                return {"valid": True}

            case Actions.CHOOSE_REWARD:
                if not current_player.choice_pending:
                    return {"valid": False, "error": "No choice pending"}
                
                card_name = args.get('card_name')
                # Find in candidates
                card = next((c for c in current_player.choice_candidates if c.name == card_name), None)
                if not card:
                    return {"valid": False, "error": "Invalid choice"}

                # Resolve based on card type and usual effect logic
                # Handling all equippable types, with DUAL redirection
                equippable = [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND, 
                              CardType.HEAD, CardType.CHEST, CardType.BRACERS, CardType.BOOTS]
                
                if card.cardType in equippable:
                    slot = card.cardType
                    if slot == CardType.DUAL:
                        slot = CardType.WEAPON
                    current_player.equippedCards[slot] = card
                    self.logs.append(LogEntry(self.turn, player, self.phase, f"{current_player.accessorName} reveals and equips {card.name}."))
                elif card.cardType == CardType.SKILL or card.cardType == CardType.INSTANT:
                     for i in range(len(current_player.skillSlots)):
                         if current_player.skillSlots[i] is None:
                             current_player.skillSlots[i] = card
                             break
                     self.logs.append(LogEntry(self.turn, player, self.phase, f"{current_player.accessorName} reveals and learns {card.name}."))
                elif card.cardType == CardType.CANTRIP:
                     current_player.hand.append(card)
                     self.logs.append(LogEntry(self.turn, player, self.phase, f"{current_player.accessorName} reveals and draws {card.name}."))

                current_player.deck.cards.remove(card)
                import random
                random.shuffle(current_player.deck.cards)
                
                current_player.choice_pending = False
                current_player.choice_candidates = []
                self.recalculateStats(player)

                # If both are done AND both ready in setup, advance
                if not any(p.choice_pending for p in self.players) and self.phase == Phases.SETUP and all(self.ready_in_setup):
                    self.nextPhase()
                return {"valid": True}

            case _:
                return {"valid": False, "error": "Action not implemented"}

    def multi_effect_resolver(self, args: dict[str, Any], real_card, effect_field="OnPlay"):
        effects = getattr(real_card, effect_field, [])
        if not effects: return True 

        if real_card.ChoiceLabels and len(effects) > 1:
            choice = args.get('choice', 0)
            if 0 <= choice < len(effects):
                self.effectResolver.resolve(effects[choice], self)
            else:
                return False
        else:
            for effect in effects:
                self.effectResolver.resolve(effect, self)
        return True

    # -------------------------------------------HANDLERS----------------------------------------------
    def _handle_start_phase_logic(self):
        player = self.players[self.isPlaying]

        # Level Calculation
        player.level = min(10, (self.turn + 1) // 2)

        player.temp_stats = {'Power': 0, 'Tenacity': 0, 'Efficiency': 0, 'Sensitivity': 0, 'Durability': 0}
        player.chainedSkillName = ""
        player.shield_active = False
        player.deflect_val = 0

        self.logs.append(LogEntry(
            self.turn,
            self.isPlaying,
            self.phase,
            f"{player.accessorName} leveled up to {player.level}."
        ))

        self.recalculateStats(self.isPlaying)

        # Cooldown Reduction
        for card in player.skillSlots:
            if card and card.currentCD > 0:
                card.currentCD -= 1
                if card.currentCD == 0:
                    self.logs.append(LogEntry(
                        self.turn,
                        self.isPlaying,
                        self.phase,
                        f"{player.accessorName}'s {card.name} is ready to use again."
                    ))

        if player.tactical_silenced:
            player.hasTacticalAction = False
            player.tactical_silenced = False  # Reset flag
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"{player.accessorName} is silenced for this turn."
            ))
        else:
            player.hasTacticalAction = True
        player.hasCombatAction = True

        # Process Pending Effects
        current_turn = self.turn
        to_execute = [e for e in player.pending_effects if e['turn'] == current_turn]
        player.pending_effects = [e for e in player.pending_effects if e['turn'] > current_turn]

        for effect_data in to_execute:
            self.effectResolver.resolve(effect_data['effect'], self)

    def _handle_loot_phase_logic(self):
        player = self.players[self.isPlaying]

        if self.turn == 1 and self.isPlaying == 0:
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"{player.accessorName}, being P1, skips their loot phase."
            ))
            return

        if len(player.deck.cards) > 0:
            card = player.deck.cards.pop()
            player.hand.append(card)
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"{player.accessorName} draws a card."
            ))
        else:
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"{player.accessorName} has no more cards in their deck."
            ))

    def _handle_end_phase_logic(self):
        pass

    # ------------------------------------------------UTILS--------------------------------------------------
    def calcPlayerStat(self, player: int, stat: str):
        p = self.players[player]
        match stat:
            case 'Durability':
                return p.currentDurability
            case 'Power':
                return p.currentPower
            case 'Efficiency':
                return p.currentEfficiency
            case 'Tenacity':
                return p.currentTenacity
            case 'Sensitivity':
                return p.currentSensitivity
            case _:
                return 0

    # noinspection PyUnreachableCode
    def calcWeaponDamage(self, player: int):
        weapon: WeaponCard = self.players[player].equippedCards[CardType.WEAPON]
        if weapon is None:
            return 1
        stat = self.calcPlayerStat(player, weapon.AtkStat)
        match weapon.AtkFunc:
            case Scaling.LINEAR:
                return stat + weapon.AtkCoeff
            case Scaling.MULTIPLICATIVE:
                return stat * weapon.AtkCoeff
            case _:
                return stat

    def checkDamage(self, player: int, raw_damage: int):
        opponent_idx = 1 if player == 0 else 0
        opponent = self.players[opponent_idx]

        if opponent.shield_active:
            opponent.shield_active = False
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"{self.players[player].accessorName}'s attack has been absorbed by {opponent.accessorName}'s shield!"
            ))
            return 0, False  # 0 Dmg, Miss

        effective_tenacity = opponent.currentTenacity
        if opponent.deflect_val > 0:
            effective_tenacity += opponent.deflect_val
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"({opponent.accessorName} prepares to deflect: +{opponent.deflect_val} Tenacity)"
            ))
        mitigated = raw_damage - effective_tenacity
        final_damage = max(0, mitigated)
        is_hit = final_damage > 0
        if is_hit:
            opponent.currentHP -= final_damage
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"HIT! {opponent.accessorName} takes {final_damage} DMG! (Ten: {effective_tenacity})"
            ))
        else:
            opponent.currentHP -= 1
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"MISS! {opponent.accessorName} takes 1 DMG! (Ten: {effective_tenacity})"
            ))
            if opponent.deflect_val > 0:
                opponent.counters.append(Counter.MOMENTUM)
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"{opponent.accessorName} has deflected the hit, gaining a Momentum counter!"
                ))

        opponent.deflect_val = 0

        if opponent.currentHP <= 0:
            self.winner = Winner(player + 1)

        return final_damage, is_hit

    def checkCounterStatGain(self, player: int):
        for counter in self.players[player].counters:
            match counter:
                case Counter.RAGE:
                    self.players[player].currentPower += 1
                case Counter.VALOR:
                    self.players[player].currentPower += 2
                    self.players[player].currentTenacity += 2
                case _:
                    pass

    def recalculateStats(self, player: int):
        p = self.players[player]

        # Temporarily remove set-based counters so they can be re-added if still valid
        p.counters = [c for c in p.counters if not c.startswith("Set: ")]

        p.currentPower = p.specialization.power
        p.currentTenacity = p.specialization.tenacity
        p.currentEfficiency = p.specialization.efficiency
        p.currentSensitivity = p.specialization.sensitivity
        p.currentDurability = p.specialization.durability

        for slot, card in p.equippedCards.items():
            if card:
                p.currentPower += card.PowerIncrease
                p.currentTenacity += card.TenacityIncrease
                p.currentEfficiency += card.EfficiencyIncrease
                p.currentSensitivity += card.SensitivityIncrease
                p.currentDurability += card.DurabilityIncrease

                if hasattr(card, 'WhileinPlay') and card.WhileinPlay:
                    # This calls methods like gainXY... or checkEquipSet in Effects
                    # We temporarily set isPlaying to 'player' so Effects knows who to target
                    old_playing = self.isPlaying
                    self.isPlaying = player
                    self.effectResolver.resolve(card.WhileinPlay, self)
                    self.isPlaying = old_playing

        p.currentDurability += p.temp_stats['Durability']
        p.currentPower += p.temp_stats['Power']
        p.currentTenacity += p.temp_stats['Tenacity']
        p.currentEfficiency += p.temp_stats['Efficiency']
        p.currentSensitivity += p.temp_stats['Sensitivity']

        self.checkCounterStatGain(player)

        # Cap HP at Durability, but DO NOT heal up to it automatically
        if p.currentHP > p.currentDurability:
            p.currentHP = p.currentDurability

    def checkDual(self, player: int, card_index: int):
        card = self.players[player].hand[card_index]
        if isinstance(card, WeaponCard) and card.cardType == CardType.DUAL:
            if self.players[player].equippedCards[CardType.OFF_HAND]:
                self.players[player].equippedCards[CardType.OFF_HAND] = None
                self.logs.append(LogEntry(
                    self.turn,
                    self.isPlaying,
                    self.phase,
                    f"{self.players[player].accessorName} un-equips their Off-Hand to equip {card.name}."
                ))

        if card.cardType == CardType.OFF_HAND:
            weapon = self.players[player].equippedCards[CardType.WEAPON]
            if weapon and weapon.cardType == CardType.DUAL:
                return {"valid": False, "error": "Cannot equip Off-Hand with a Dual Weapon"}
        return None

    def _deal_init_hand(self, player):
        p = self.players[player]
        p.hand = []
        count = 5 if player == 0 else 6
        for i in range(count):
            if len(p.deck.cards) > 0:
                p.hand.append(p.deck.cards.pop())
        self.recalculateStats(player)
        p.currentHP = p.currentDurability
        self.logs.append(LogEntry(
            self.turn,
            self.isPlaying,
            self.phase,
            f"{p.accessorName} draws their initial hand."
        ))

        return {"valid": True}
    def _schedule_future_effects(self, player_idx: int, card):
        """Schedules effects for future turns based on OnNextTurn and OnNextPlayerTurn fields."""
        if not card: return
        
        # OnNextPlayerTurn: next turn (n+1)
        if hasattr(card, 'OnNextPlayerTurn') and card.OnNextPlayerTurn:
            target_idx = 1 - player_idx
            self.players[target_idx].pending_effects.append({
                'effect': card.OnNextPlayerTurn,
                'turn': self.turn + 1
            })
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"Effect scheduled for {self.players[target_idx].accessorName}'s next turn."
            ))

        # OnNextTurn: turn after next (n+2)
        if hasattr(card, 'OnNextTurn') and card.OnNextTurn:
            self.players[player_idx].pending_effects.append({
                'effect': card.OnNextTurn,
                'turn': self.turn + 2
            })
            self.logs.append(LogEntry(
                self.turn,
                self.isPlaying,
                self.phase,
                f"Effect scheduled for {self.players[player_idx].accessorName} in 2 turns."
            ))
