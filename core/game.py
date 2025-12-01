from typing import List, Dict, Any

from core.card import WeaponCard
from core.effects import Effects, solveEffect
from core.enums import Winner, Phases, Actions, CardType, Scaling
from core.player import Player


def dbg_matchCreator():
    players = [Player(True, "P1", 0, "Scraper"), Player(False, "P2", 0, "Scraper")]
    return Game(players)

def matchCreator(name1: str, deck1: int, spec1: str, name2: str, deck2: int, spec2: str):
    players = [Player(True, name1, deck1, spec1), Player(False, name2, deck2, spec2)]
    return Game(players)


class Game:
    def __init__(self, players: List[Player]):
        self.players: List[Player] = players
        self.turn: int = 1
        self.arePlayersReady = [False, False]
        # noinspection PyTypeChecker
        self.isPlaying: bool = 0  # 0 per P1, 1 per P2
        self.hasMulligan = [False, False]
        self.ready_in_setup = [False, False]
        self.phase: Phases = Phases.SETUP
        self.winner: Winner = Winner.NONE
        self.logs: List[str] = []

    def nextPhase(self):
        match self.phase:
            case Phases.SETUP:
                # Se le mani sono vuote, distribuiscile e resta in Setup (attendi Mulligan)
                if len(self.players[0].hand) == 0:
                    self._deal_init_hand(0)
                    self._deal_init_hand(1)
                    return

                # Setup finito -> Inizio Partita
                self.phase = Phases.START
                self._handle_start_phase_logic()
                self.nextPhase()  # Auto-advance: START -> LOOT

            case Phases.START:
                self.phase = Phases.LOOT
                self._handle_loot_phase_logic()
                self.nextPhase()  # Auto-advance: LOOT -> PREP

            case Phases.LOOT:
                self.phase = Phases.PREPARATION

            case Phases.PREPARATION:
                self.phase = Phases.DUEL

            case Phases.DUEL:
                self.phase = Phases.END
                # Richiamiamo subito nextPhase per entrare nel case END
                # e verificare immediatamente se bisogna scartare
                self.nextPhase()

            case Phases.END:
                player = self.players[self.isPlaying]

                # BLOCCO CRITICO: Controllo limite mano
                if len(player.hand) > 5:
                    self.logs.append(f"{player.accessorName} must discard down to 5 cards.")
                    return  # Si ferma qui finché il giocatore non scarta

                # Se la mano è ok, procedi al cambio turno
                self._handle_end_phase_logic()

                # Scambio Giocatore (0 -> 1 -> 0...)
                self.isPlaying = 1 - self.isPlaying
                self.turn += 1

                self.phase = Phases.START
                self._handle_start_phase_logic()
                self.nextPhase()

    def receiveAction(self, player: bool, action: Actions, args: Dict[str, Any]):
        if self.winner != Winner.NONE:
            return {"valid": False, "error": "Game is already over"}
        if player != self.isPlaying:
            # Eccezione: Nel SETUP sincrono permettiamo azione se è il proprio setup
            if not (self.phase == Phases.SETUP and not self.ready_in_setup[player]):
                return {"valid": False, "error": "It's not your turn"}

        effectResolver = Effects()
        current_player = self.players[player]

        match action:
            case Actions.PASS_PHASE:
                # 1. SETUP
                if self.phase == Phases.SETUP:
                    self.ready_in_setup[player] = True
                    if self.ready_in_setup[0] and self.ready_in_setup[1]:
                        self.isPlaying = 0  # Inizia P1
                        self.nextPhase()
                        return {"valid": True, "message": "Game Starting!"}
                    else:
                        # Hack per visualizzazione: se l'altro non è pronto, switchiamo
                        # visivamente l'active player per far attendere il client
                        if self.isPlaying == player:
                            self.isPlaying = 1 - player
                        return {"valid": True, "message": "Waiting for opponent..."}

                # 2. PREPARATION -> DUEL
                elif self.phase == Phases.PREPARATION:
                    self.nextPhase()
                    return {"valid": True}

                # 3. DUEL -> END
                elif self.phase == Phases.DUEL:
                    self.nextPhase()
                    return {"valid": True}

                # 4. END -> NEW TURN (START)
                # QUESTO BLOCCO È CRUCIALE PER USCIRE DALLA END PHASE
                elif self.phase == Phases.END:
                    if len(current_player.hand) <= 5:
                        self.nextPhase()  # Scatena la transizione END -> START -> LOOT -> PREP
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
                self.logs.append(f"{current_player.accessorName} discarded {card.name}")

                return {"valid": True}

            case Actions.MULLIGAN:
                if self.phase != Phases.SETUP:
                    return {"valid": False, "error": "You can't mulligan in this phase"}
                if self.hasMulligan[player]:
                    return {"valid": False, "error": "You've already used your mulligan"}
                self.hasMulligan[player] = True
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
                            card.currentCD = 0
                            solveEffect(card.OnPlay, effectResolver)
                            return {"valid": True}
                        else:
                            return {"valid": False, "error": "Skill slots full. Remove one first."}
                    elif card_to_play.cardType == CardType.SPE_ADVANCED:
                        if current_player.level >= 5:
                            # TODO: Implement Spec Evolution logic
                            return {"valid": True, "message": "Spec Evolved"}
                        return {"valid": False, "error": "Level too low"}
                    else:
                        return {"valid": False, "error": "Can only place Skills or Evolve in Preparation"}

                # Duel Phase Playable cards:
                #   Cantrip (DUEL PHASE - Cost: NONE)
                elif self.phase == Phases.DUEL:
                    if card_to_play.cardType == CardType.CANTRIP:

                        card = current_player.hand.pop(args['index'])
                        if card.level > self.players[player].level:
                            return {"valid": False, "error": "Level too low"}
                        solveEffect(card.OnPlay, effectResolver)  # Cantrips use OnPlay
                        return {"valid": True}
                    else:
                        return {"valid": False, "error": "Can only play Cantrips in Duel Phase"}

                else:
                    return {"valid": False, "error": "Cannot Play in this phase"}

            case Actions.EQUIP:
                # Equip (DUEL PHASE - Cost: TACTICAL)
                if self.phase != Phases.DUEL: return {"valid": False, "error": "Can only equip in Duel Phase"}
                if not current_player.hasTacticalAction: return {"valid": False, "error": "No Tactical Actions left"}
                if args['index'] >= len(current_player.hand): return {"valid": False, "error": "Invalid index"}
                card = current_player.hand[args['index']]

                if card.cardType not in [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND, CardType.HEAD, CardType.CHEST,
                                         CardType.BRACERS, CardType.BOOTS]:
                    return {"valid": False, "error": "Not an equipment"}
                if card.level > self.players[player].level:
                    return {"valid": False, "error": "Level too low"}
                if check := self.checkTwoHanded(player, args['index']):
                    return check

                # Equip
                real_card = current_player.hand.pop(args['index'])
                current_player.equippedCards[real_card.cardType.value] = real_card
                solveEffect(real_card.OnPlay, effectResolver)
                self.recalculateStats(player)

                current_player.hasTacticalAction = False
                return {"valid": True}

            case Actions.ACTIVATE:
                # Skill on field (DUEL PHASE - Cost: TACTICAL)
                # Equip on field (DUEL PHASE - Cost: TACTICAL)
                if self.phase != Phases.DUEL: return {"valid": False, "error": "Can only activate in Duel Phase"}

                # Retrieve card source
                source_type = args.get('source')  # "SKILL or EQUIP"
                if source_type == 'SKILL':
                    idx = args.get('index')
                    if idx is None or idx >= len(current_player.skillSlots):
                        return {"valid": False, "error": "Invalid skill index"}
                    target_card = current_player.skillSlots[idx]
                    if target_card is None: return {"valid": False, "error": "Slot empty"}
                    if target_card.currentCD > 0: return {"valid": False, "error": "Skill in Cooldown"}

                    if not current_player.hasTacticalAction and target_card.cardType != CardType.INSTANT:
                        return {"valid": False, "error": "No Tactical Actions left"}
                    solveEffect(target_card.OnActivate, effectResolver)
                elif source_type == 'EQUIP':
                    slot = args.get('slot')
                    target_card = self.players[player].equippedCards[slot]
                    if slot is not None:
                        solveEffect(target_card.OnActivate, effectResolver)

                else: return {"valid": False, "error": "Cannot activate that"}

                # CD and "TAP"
                target_card.currentCD = target_card.CD

                if target_card.cardType != CardType.INSTANT:
                    current_player.hasTacticalAction = False

                return {"valid": True}

            case Actions.ATTACK:
                # Weapon Attack (DUEL PHASE - Cost: COMBAT)
                if self.phase != Phases.DUEL: return {"valid": False, "error": "Wrong phase"}
                if not current_player.hasCombatAction: return {"valid": False, "error": "No Combat Actions left"}

                damage = self.calcWeaponDamage(player)
                final_damage = self.checkDamage(player, damage)

                # OnHit / OnMiss
                weapon = current_player.equippedCards['Weapon']
                if weapon:
                    if final_damage > 0:  # Almost everytime
                        solveEffect(weapon.OnHit, effectResolver)
                    else:  # For forced miss
                        solveEffect(weapon.OnMiss, effectResolver)

                current_player.hasCombatAction = False
                return {"valid": True}

            case _:
                return {"valid": False, "error": "Action not implemented"}

    # -------------------------------------------HANDLERS----------------------------------------------
    def _handle_start_phase_logic(self):
        player = self.players[self.isPlaying]

        if player.level < 10 and self.turn != 1:
            player.level += 1
        self.recalculateStats(self.isPlaying)

        for card in player.skillSlots:
            if card and card.currentCD > 0:
                card.currentCD -= 1

        player.hasTacticalAction = True
        player.hasCombatAction = True

    def _handle_loot_phase_logic(self):
        player = self.players[self.isPlaying]


        if self.turn == 1 and self.isPlaying == 0:
            self.logs.append("P1 skips draw on first turn.")
            return

        if len(player.deck.cards) > 0:
            card = player.deck.cards.pop()
            player.hand.append(card)
            self.logs.append(f"{player.accessorName} draws.")
        else:
            self.logs.append(f"{player.accessorName} deck empty (Fatigue?).")

    def _handle_end_phase_logic(self):
        # For turn end effects,
        # for now, nothing to do.
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

    def calcWeaponDamage(self, player: int):
        # Damage = (Base + Stat)
        weapon: WeaponCard = self.players[player].equippedCards['Weapon']
        if weapon is None:
            return 1
        stat = self.calcPlayerStat(player, weapon.AtkStat)


        match weapon.AtkFunc:
            case Scaling.LINEAR:
                return stat + weapon.AtkCoeff
            case Scaling.MULTIPLICATIVE:
                return stat * weapon.AtkCoeff
            case _:
                # noinspection PyUnreachableCode
                return stat

    def checkDamage(self, player: int, raw_damage: int):
        opponent_idx = 1 if player == 0 else 0
        opponent = self.players[opponent_idx]

        mitigated_damage = raw_damage - opponent.currentTenacity
        final_damage = max(1, mitigated_damage)

        opponent.currentHP -= final_damage
        self.logs.append(f"Dealt {final_damage} damage (Raw: {raw_damage} - Tenacity: {opponent.currentTenacity})")

        if opponent.currentHP <= 0:
            self.winner = Winner(player + 1)

        return final_damage

    def recalculateStats(self, player: int):
        p = self.players[player]

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

        if p.currentHP > p.currentDurability:
            p.currentHP = p.currentDurability

    def checkTwoHanded(self, player: int, card_index: int):
        card = self.players[player].hand[card_index]
        if isinstance(card, WeaponCard) and card.is2Handed:
            if self.players[player].equippedCards['Off-Hand']:
                self.players[player].equippedCards['Off-Hand'] = None
                self.logs.append("Off-Hand removed for 2H Weapon.")

        if card.cardType == CardType.OFF_HAND:
            weapon = self.players[player].equippedCards['Weapon']
            if weapon and weapon.is2Handed:
                return {"valid": False, "error": "Cannot equip Off-Hand with a 2-Handed Weapon"}
        return None

    def _deal_init_hand(self, player):
        self.players[player].hand = []
        # P1: 5, P2: 6
        count = 5 if player == 0 else 6
        for i in range(count):
            if len(self.players[player].deck.cards) > 0:
                self.players[player].hand.append(self.players[player].deck.cards.pop())
        self.recalculateStats(player)
        self.players[player].currentHP = self.players[player].currentDurability

        return {"valid": True}