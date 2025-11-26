from typing import List, Dict, Any

from core.card import WeaponCard
from core.effects import Effects, solveEffect
from core.enums import Winner, Phases, Actions, CardType, Scaling
from core.player import Player

def matchCreator():
    players = [Player(True, "P1", 0, "Scraper"), Player(False, "P1", 0, "Scraper")]
    return Game(players)

class Game:
    def __init__(self, players: List[Player]):
        self.players: List[Player] = players
        self.turn: int = 0
        self.arePlayersReady = [False, False]
        # noinspection PyTypeChecker
        self.isPlaying: bool = 0
        self.phase: Phases = Phases.SETUP
        self.winner: Winner = Winner.NONE
        self.logs: List[str] = []

    def nextPhase(self):
            # Gestione esplicita delle transizioni (più sicuro di phase += 1)

            if self.phase == Phases.SETUP:
                if len(self.players[0].hand) == 0:
                    self._deal_init_hand(0)
                    self._deal_init_hand(1)
                    return
                self.phase = Phases.START
                self._handle_start_phase_logic()
                self.nextPhase()

            elif self.phase == Phases.START:
                self.phase = Phases.LOOT
                self._handle_loot_phase_logic()
                player = self.players[self.isPlaying]
                if len(player.hand) > 5:
                    return
                else:
                    self.nextPhase()

            elif self.phase == Phases.LOOT:
                self.phase = Phases.PREPARATION

            elif self.phase == Phases.PREPARATION:
                self.phase = Phases.DUEL

            elif self.phase == Phases.DUEL:
                self.phase = Phases.END
                self._handle_end_phase_logic()

                self.isPlaying = 1 - self.isPlaying
                if self.isPlaying == 0:
                    self.turn += 1

                self.phase = Phases.START
                self.nextPhase()

    def receiveAction(self, player: bool, action: Actions, args: Dict[str, Any]):
        if self.winner != Winner.NONE:
            return {"valid": False, "error": "Game is already over"}
        if player != self.isPlaying:
            return {"valid": False, "error": "It's not your turn"}
        effectResolver = Effects()
        match action:
            case Actions.PASS_PHASE:
                if self.phase == Phases.SETUP:
                    self.arePlayersReady[self.isPlaying] = True
                    #DEBUG: please remove
                    self.arePlayersReady[1] = True
                    while not(self.arePlayersReady[0] and self.arePlayersReady[1]): pass
                    self.nextPhase()
                    return {"valid": True, "message": "Hand Kept, Game Starting"}

                elif self.phase == Phases.PREPARATION:
                    self.nextPhase()  # Va a DUEL
                    return {"valid": True}

                elif self.phase == Phases.DUEL:
                    self.nextPhase()  # Va a END
                    return {"valid": True}
                return {"valid": False}
            case Actions.MULLIGAN:
                if self.phase != Phases.SETUP:
                    return {"valid": False, "error": "You can't mulligan in this phase"}
                else:
                    return self._deal_init_hand(player)
            case Actions.DRAW:
                if self.phase != Phases.LOOT:
                    return {"valid": False, "error": "You can't draw in this phase"}
                else:
                    self.players[player].hand.append(self.players[player].deck.cards.pop())
                    return {"valid": True}
            case Actions.DISCARD:
                if self.phase != Phases.LOOT:
                    return {"valid": False, "error": "Can only discard in Loot phase"}

                if len(self.players[player].hand) <= 5:
                    return {"valid": False, "error": "Hand size is OK, no need to discard"}

                card = self.players[player].hand.pop(args['index'])
                self.logs.append(f"{self.players[player].accessorName} discarded {card.name}")

                if len(self.players[player].hand) <= 5:
                    self.nextPhase()

                return {"valid": True}
            case Actions.PLAY:
                if self.phase != Phases.PREPARATION: return {"valid": False, "error": "You can't play in this phase"}
                if not self.players[player].hasAction: return {"valid": False,
                                                               "error": "You don't have any action actions left"}
                if args['index'] >= len(self.players[player].hand): return {"valid": False, "error": "Invalid index"}
                if (
                        (
                                self.players[player].hand[args['index']].cardType == CardType.SKILL
                                or self.players[player].hand[args['index']].cardType == CardType.INSTANT
                        )
                        and len(list(filter(None, self.players[player].skillSlots))) == len(
                    self.players[player].skillSlots)
                ):
                    card = self.players[player].hand.pop(args['index'])
                    self.players[player].skillSlots[self.players[player].skillSlots.index(None)] = card
                    solveEffect(card.OnPlay, effectResolver)
                    self.players[player].hasAction = False
                    return {"valid": True}
                elif self.players[player].hand[args['index']].cardType == CardType.CANTRIP:
                    card = self.players[player].hand.pop(args['index'])
                    solveEffect(card.OnPlay, effectResolver)
                    return {"valid": True}
                else:
                    if check := self.checkTwoHanded(player, args['index']):
                        return check
                    card = self.players[player].hand.pop(args['index'])
                    self.players[player].equippedCards[card.cardType.value] = card
                    self.recalculateStats(player)
                    solveEffect(card.OnPlay, effectResolver)
                    self.players[player].hasAction = False
                    return {"valid": True}
            case Actions.EQUIP:
                if self.phase != Phases.PREPARATION: return {"valid": False, "error": "You can't equip in this phase"}
                if not self.players[player].hasBonusAction: return {"valid": False,
                                                                    "error": "You don't have any bonus actions left"}
                if args['index'] >= len(self.players[player].hand): return {"valid": False, "error": "Invalid index"}
                if (
                        self.players[player].hand[args['index']].cardType == CardType.SKILL
                        or self.players[player].hand[args['index']].cardType == CardType.INSTANT
                        or self.players[player].hand[args['index']].cardType == CardType.CANTRIP
                ):
                    return {"valid": False, "error": "You can't equip that card"}
                else:
                    if check := self.checkTwoHanded(player, args['index']):
                        return check
                    card = self.players[player].hand.pop(args['index'])
                    self.players[player].equippedCards[card.cardType.value] = card
                    solveEffect(card.OnPlay, effectResolver)
                    self.recalculateStats(player)
                    self.players[player].hasBonusAction = False
                    return {"valid": True}
            case Actions.ACTIVATE:
                source_type = args.get('source')  # "SKILL" o "EQUIP"

                if source_type == 'SKILL':
                    idx = args.get('index')
                    if idx is None or idx >= len(self.players[player].skillSlots):
                        return {"valid": False, "error": "Invalid skill index"}
                    target_card = self.players[player].skillSlots[idx]

                elif source_type == 'EQUIP':
                    slot_name = args.get('slot')
                    target_card = self.players[player].equippedCards.get(slot_name)

                else:
                    return {"valid": False, "error": "Unknown source type"}

                if target_card is None:
                    return {"valid": False, "error": "No card found in target slot"}
                if not target_card.OnActivate:
                    return {"valid": False, "error": "This card has no active effect"}
                if target_card.currentCD > 0:
                    return {"valid": False, "error": "Cooldown not finished yet"}
                if not self.players[player].hasAction and target_card.cardType != CardType.INSTANT:
                    return {"valid": False, "error": "You don't have any actions left"}

                solveEffect(target_card.OnActivate, effectResolver)
                target_card.currentCD = target_card.CD

                if target_card.cardType != CardType.INSTANT:
                    self.players[player].hasAction = False

                return {"valid": True}
            case Actions.ATTACK:
                if self.phase != Phases.DUEL: return {"valid": False, "error":"You cannot attack yet"}
                if not self.players[player].hasBonusAction: return {"valid": False, "error": "You don't have any bonus actions left"}
                if self.checkDamage(player, self.calcWeaponDamage(player))>0:
                    solveEffect(self.players[player].equippedCards['Weapon'].OnHit, effectResolver)
                else: solveEffect(self.players[player].equippedCards['Weapon'].OnMiss, effectResolver)
                return {"valid": True}
            case Actions.END_TURN:
                self.phase = Phases.END
                self.nextPhase()
                return {"valid": True}
            case _:
                # noinspection PyUnreachableCode
                return {"valid": False, "error": "This action is not yet implemented"}

    # -------------------------------------------HANDLERS----------------------------------------------
    def _handle_start_phase_logic(self):
        player = self.players[self.isPlaying]

        if player.level < 10:
            player.level += 1

        if player.level <= 5:
            player.currentHP = player.currentHP + 10
            player.currentDurability = player.currentDurability + 10

        for card in player.skillSlots:
            if card and card.currentCD > 0:
                card.currentCD -= 1

        player.hasAction = True
        player.hasBonusAction = True

    def _handle_loot_phase_logic(self):
        player = self.players[self.isPlaying]

        if len(player.deck.cards) > 0:
            card = player.deck.cards.pop()
            player.hand.append(card)
            self.logs.append(f"{player.accessorName} draws.")
        else:
            # TODO: What to do if deck is empty?
            self.logs.append(f"{player.accessorName} cannot draw any more cards.")

    def _handle_end_phase_logic(self):
        #Nothing for now
        pass

# ------------------------------------------------UTILS--------------------------------------------------
    def calcPlayerStat(self, player:int, stat:str):
        match stat:
            case 'Durability': return self.players[player].currentDurability
            case 'Power': return self.players[player].currentPower
            case 'Efficiency': return self.players[player].currentEfficiency
            case 'Tenacity': return self.players[player].currentTenacity
            case 'Sensitivity': return self.players[player].currentSensitivity
            case _: return 0
    def calcWeaponDamage(self, player:int):
        weapon:WeaponCard = self.players[player].equippedCards['Weapon']
        match weapon.AtkFunc:
            case Scaling.LINEAR:
                return self.calcPlayerStat(player, weapon.AtkStat)+weapon.AtkCoeff
            case Scaling.MULTIPLICATIVE:
                return self.calcPlayerStat(player, weapon.AtkStat)*weapon.AtkCoeff


    def checkDamage(self, player:int, damage:int):
        opponent = 1 if player == 0 else 0
        tempDamage = max(0, damage - self.players[opponent].currentTenacity)
        self.players[opponent].currentHP -= tempDamage
        if self.players[opponent].currentHP<= 0:
            self.winner = Winner(player+1)
        return tempDamage

    def recalculateStats(self, player: int):
        p = self.players[player]

        p.currentPower = p.specialization.power
        p.currentTenacity = p.specialization.tenacity
        p.currentEfficiency = p.specialization.efficiency
        p.currentSensitivity = p.specialization.sensitivity
        p.currentDurability = p.specialization.durability + (p.level-1)*10

        for slot, card in p.equippedCards.items():
            if card:
                p.currentPower += card.PowerIncrease
                p.currentTenacity += card.TenacityIncrease
                p.currentEfficiency += card.EfficiencyIncrease
                p.currentSensitivity += card.SensitivityIncrease
                p.currentDurability += card.DurabilityIncrease

    def checkTwoHanded(self,player:int, card_index:int):
        card = self.players[player].hand[card_index]
        if isinstance(card, WeaponCard) and card.is2Handed:
            if self.players[player].equippedCards['Off-Hand']:
                self.players[player].equippedCards['Off-Hand'] = None

        if card.cardType == CardType.OFF_HAND:
            weapon = self.players[player].equippedCards['Weapon']
            if weapon and weapon.is2Handed:
                return {"valid": False, "error": "Cannot equip Off-Hand with a 2-Handed Weapon"}
        return None

    def _deal_init_hand(self, player):
        self.players[player].hand = []
        for i in range(5 if player == 0 else 6):
            self.players[player].hand.append(self.players[player].deck.cards.pop())  # DRAW!
        return {"valid": True}
