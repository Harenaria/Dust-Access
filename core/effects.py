import logging
from typing import Any

from core.card import WeaponCard
from core.enums import Counter, Scaling, CardType
from core.game_logs import LogEntry

EFFECT_CONSTANTS = {
    "Power": "Power",
    "Tenacity": "Tenacity",
    "Efficiency": "Efficiency",
    "Sensitivity": "Sensitivity",
    "Durability": "Durability",
    "Empathy": "Sensitivity",  # For legacy name support
    "LINEAR": Scaling.LINEAR,
    "MULTIPLICATIVE": Scaling.MULTIPLICATIVE,
    "OFF_HAND": CardType.OFF_HAND,
    "DUAL": CardType.DUAL,
    "Off-Hand": CardType.OFF_HAND,
    "Dual": CardType.DUAL,
    "Heavy": "Heavy",
    "Medium": "Medium",
    "Light": "Light"
}


class Effects:
    def __init__(self):
        self.game = None
        self.logger = logging.getLogger("EffectsResolver")

    def resolve(self, effect_str: str, game_state):
        """
        Parses a string like 'Damage(Power, LINEAR, 1)' and executes the corresponding method.
        """
        prior_game = self.game
        self.game = game_state

        # Basic Validation
        if not effect_str or not isinstance(effect_str, str):
            self.game = prior_game
            return

        clean_str = effect_str.strip().replace('\x00', '')
        if not clean_str or clean_str.lower() == 'nan':
            self.game = prior_game
            return

        # Parse: Split "MethodName(Args)"
        try:
            if '(' not in clean_str or not clean_str.endswith(')'):
                # all valid effects function calls have ()
                return

            method_name, args_part = clean_str.split('(', 1)
            method_name = method_name.strip()
            args_part = args_part[:-1]  # Remove trailing ')'

            # This splits the arguments by comma and parses them but handles the fact that args might be empty
            raw_args = [arg.strip() for arg in args_part.split(',') if arg.strip()]
            parsed_args = []

            for arg in raw_args:
                parsed_args.append(self._convert_arg(arg))

            # Dispatch: Find the method on this class and call it
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                # Security Check: Ensure we don't call internal methods (starting with _)
                if not method_name.startswith('_') and callable(method):
                    method(*parsed_args)
                else:
                    self._log_error(f"Security: Attempted to call non-callable or private '{method_name}'")
            else:
                self._log_error(f"Unknown effect method: '{method_name}'")

        except Exception as e:
            self._log_error(f"Error parsing '{clean_str}': {e}")
        finally:
            self.game = prior_game

    @staticmethod
    def _convert_arg(arg: str) -> Any:
        """Converts string arguments from CSV into Types (Int, Enums, Strings)"""
        # Check if it's a known Constant/Enum (e.g., "LINEAR", "Power")
        if arg in EFFECT_CONSTANTS:
            return EFFECT_CONSTANTS[arg]

        # Check if it's an Integer, handling negative numbers too
        if arg.lstrip('-').isdigit():
            return int(arg)

        # Check if it's a quoted string (e.g., "Rage")
        # CSVs sometimes double quote: ""Rage""
        if '"' in arg or "'" in arg:
            return arg.replace('"', '').replace("'", "")

        # Default: Return as string
        return arg

    def _log_error(self, message: str):
        if self.game:
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying if self.game.players else 0,
                self.game.phase,
                f"Effect Error: {message}"
            ))
        self.logger.error(message)

    def playCounter(self, counterName, num):
        # Fix for CSV parsing sometimes keeping double quotes
        counterName = counterName.replace('"', '')
        for _ in range(num):
            self.game.players[self.game.isPlaying].counters.append(counterName)
        self.game.recalculateStats(self.game.isPlaying)
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{self.game.players[self.game.isPlaying].accessorName} played {counterName} x{num}."
        ))

    def removeAllCounters(self, counterName: str):
        counterName = counterName.replace('"', '')
        p = self.game.players[self.game.isPlaying]
        original_len = len(p.counters)
        p.counters = [c for c in p.counters if c != counterName and c != Counter(counterName)]
        if len(p.counters) < original_len:
            self.game.recalculateStats(self.game.isPlaying)

    def Damage(self, stat: str, scale: str, coeff: int):
        player = self.game.players[self.game.isPlaying]
        if "Kai" in player.counters:
            stat = "Power"
            player.counters.remove("Kai")
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName}'s Kai triggers! Power stat used instead of {stat}."
            ))

        stat_val = self.game.calcPlayerStat(self.game.isPlaying, stat)
        scale_type = Scaling(scale)
        damage = 0
        if scale_type == Scaling.LINEAR:
            damage = stat_val + coeff
        elif scale_type == Scaling.MULTIPLICATIVE:
            damage = stat_val * coeff

        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} deals {damage} damage to opponent."
        ))
        self.game.checkDamage(self.game.isPlaying, damage)

    def HealSelf(self, stat: str, scale: str, coeff: int):
        player = self.game.players[self.game.isPlaying]
        stat_val = self.game.calcPlayerStat(self.game.isPlaying, stat)
        scale_type = Scaling(scale)
        amount = 0
        if scale_type == Scaling.LINEAR:
            amount = stat_val + coeff
        elif scale_type == Scaling.MULTIPLICATIVE:
            amount = stat_val * coeff

        # Ensure we don't heal negative (if stat + coeff < 0)
        amount = max(0, amount)

        old_hp = player.currentHP
        player.currentHP = min(player.currentHP + amount, player.currentDurability)
        healed = player.currentHP - old_hp
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} healed for {healed} HP (Req: {amount})."
        ))
        self.game.recalculateStats(self.game.isPlaying)

    def DrawThenDiscard(self, num: int):
        player = self.game.players[self.game.isPlaying]
        drawn = 0
        for _ in range(num):
            if player.deck.cards:
                player.hand.append(player.deck.cards.pop())
                drawn += 1
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} drew {drawn} card(s)."
        ))
        if drawn > 0:
            player.pending_discard += num
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName} must discard {player.pending_discard} card(s)."
            ))

    def Cover(self, amount: int):
        player = self.game.players[self.game.isPlaying]
        player.temp_stats['Tenacity'] += amount
        self.game.recalculateStats(self.game.isPlaying)
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} covers for {amount} Tenacity."
        ))

    def Shield(self):
        player = self.game.players[self.game.isPlaying]
        player.shield_active = True
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} activates Shield! Your first damage Action you are the target of misses."
        ))

    def RemoveShield(self):
        player = self.game.players[self.game.isPlaying]
        if player.shield_active:
            player.shield_active = False
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName}'s Shield has expired."
            ))

    def Deflect(self, amount: int):
        player = self.game.players[self.game.isPlaying]
        player.deflect_val = amount
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} prepares to Deflect (+{amount} Tenacity on hit)"
        ))

    def SkullSplitter(self):
        player = self.game.players[self.game.isPlaying]
        target = self.game.players[1 - self.game.isPlaying]
        weapon: WeaponCard = player.equippedCards.get('Weapon')

        if weapon and weapon.is2Handed:
            dmg = player.currentPower
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName} has a 2H Weapon, so Skullsplitter will activate if it hits."
            ))
            final_dmg, is_hit = self.game.checkDamage(self.game.isPlaying, dmg)
            if is_hit:
                target.tactical_silenced = True
                self.game.logs.append(LogEntry(
                    self.game.turn,
                    self.game.isPlaying,
                    self.game.phase,
                    f"{player.accessorName} hits! {target.accessorName} is silenced."
                ))
            else:
                self.game.logs.append(LogEntry(
                    self.game.turn,
                    self.game.isPlaying,
                    self.game.phase,
                    f"{player.accessorName} missed! Skullsplitter failed."
                ))
        else:
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName} does not have a 2H weapon, so Skullsplitter failed."
            ))

    def TempStat(self, stat: str, amount: int):
        """Apply temporary stat bonus until end of turn. Replaces old Battlemaster logic."""
        player = self.game.players[self.game.isPlaying]
        # Ensure stat name is clean
        stat = stat.replace('"', '').replace("'", "").strip()

        if stat not in player.temp_stats:
            self._log_error(f"Invalid stat for TempStat: {stat}")
            return

        player.temp_stats[stat] += amount
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} gains +{amount} temporary {stat}."
        ))
        self.game.recalculateStats(self.game.isPlaying)

    def Battlemaster(self):
        """Legacy support - redirects to TempStat based on choice"""
        args = getattr(self.game, 'current_action_args', {})
        choice = int(args.get('choice', 0))
        if choice == 0:
            self.TempStat("Power", 2)
        else:
            self.TempStat("Tenacity", 5)


    def NullifyFirstAction(self):
        # This is now called at the start of the turn for the person who is Nullified.
        # We must check if the person who DID the bash (the opponent) STILL has an Off-Hand.
        player = self.game.players[self.game.isPlaying]
        opponent = self.game.players[1 - self.game.isPlaying]
        
        if opponent.equippedCards.get(CardType.OFF_HAND) is None:
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"Nullification failed: {opponent.accessorName} no longer has an Off-Hand equipped!"
            ))
            return

        player.counters.append("Nullified")
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.isPlaying,
            self.game.phase,
            f"{player.accessorName} is Nullified by {opponent.accessorName}'s Shield Bash!"
        ))

    def ifUsedBonusRegain(self):
        player = self.game.players[self.game.isPlaying]
        if not player.hasTacticalAction:
            player.hasTacticalAction = True
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName} regains their Tactical Action."
            ))
        else:
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.isPlaying,
                self.game.phase,
                f"{player.accessorName} already has their Tactical Action."
            ))
        self.game.recalculateStats(self.game.isPlaying)

    def gainXY_if_notZ_onField(self, stat_to_gain, amount, slot_to_check):
        player = self.game.players[self.game.isPlaying]
        slot = CardType(slot_to_check)
        equipped_item = player.equippedCards.get(slot)
        if slot == CardType.DUAL:
            w: WeaponCard = player.equippedCards.get("Weapon")
            if w and w.cardType == CardType.DUAL: return
        elif equipped_item is not None:
            return

        # Apply stat
        match stat_to_gain:
            case "Tenacity":
                player.currentTenacity += amount
            case "Power":
                player.currentPower += amount
            case "Efficiency":
                player.currentEfficiency += amount
            case "Sensitivity":
                player.currentSensitivity += amount
            case "Durability":
                player.currentDurability += amount

    def checkEquipSet(self, set_name):
        player = self.game.players[self.game.isPlaying]
        count = 0
        for card in player.equippedCards.values():
            if card and set_name in card.name:
                count += 1

        if count >= 2:
            clean_name = set_name.replace('"', '')
            if f"Set: {clean_name}" not in player.counters:
                player.counters.append(f"Set: {clean_name}")
                self.game.logs.append(LogEntry(
                    self.game.turn,
                    self.game.isPlaying,
                    self.game.phase,
                    f"{player.accessorName} completes the set {clean_name}!"
                ))
        else:
            clean_name = set_name.replace('"', '')
            if f"Set: {clean_name}" in player.counters:
                player.counters.remove(f"Set: {clean_name}")

    # --- Specialization "Game Begins" Effects ---

    @staticmethod
    def _find_candidates(player, max_level, types_list=None, card_name=None):
        """Centralized helper to find matching cards in player's deck."""
        # Normalize types_list to lowercase for comparison
        lower_types = [t.lower() for t in types_list] if types_list else []
        candidates = []
        for c in player.deck.cards:
            if c.level > max_level:
                continue
            if card_name and c.name.lower() != card_name.lower():
                continue
            if lower_types and c.cardType.lower() not in lower_types:
                continue
            candidates.append(c)
        return candidates

    def EquipFromDeck(self, types, max_level, card_name=None):
        import random
        player = self.game.players[self.game.isPlaying]

        # Parse types (handle string with || or list)
        types_list = [t.strip() for t in types.split("||")] if isinstance(types, str) else types

        # Validation: check if all types are equippable
        equippable = [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND, 
                      CardType.HEAD, CardType.CHEST, CardType.BRACERS, CardType.BOOTS]
        equippable_low = [et.lower() for et in equippable]
        for t in types_list:
            if t.lower() not in equippable_low:
                raise ValueError(f"Type {t} is not an equippable card type.")

        candidates = self._find_candidates(player, max_level, types_list, card_name)
        
        if not candidates:
            # We use the raw input for log for clarity
            self.game.logs.append(LogEntry(self.game.turn, self.game.isPlaying, self.game.phase, 
                f"Search: No matching {types} (max lvl {max_level}) found in deck."))
            return

        if len(candidates) == 1:
            card = candidates[0]
            try:
                player.deck.cards.remove(card)
            except ValueError:
                found = False
                for i, c in enumerate(player.deck.cards):
                    if c.name == card.name and c.cardType == card.cardType and c.level == card.level:
                        player.deck.cards.pop(i)
                        found = True
                        break
                if not found: raise
            # Find the correct slot
            slot = card.cardType
            if slot == CardType.DUAL or str(slot) == "Dual":
                slot = CardType.WEAPON
            
            player.equippedCards[slot] = card
            random.shuffle(player.deck.cards)
            self.game.logs.append(LogEntry(self.game.turn, self.game.isPlaying, self.game.phase, 
                f"{player.accessorName} reveals and equips {card.name}."))
            self.game.recalculateStats(self.game.isPlaying)
        else:
            player.choice_pending = True
            player.choice_candidates = candidates

    def LearnFromDeck(self, arg1, arg2=None):
        import random
        player = self.game.players[self.game.isPlaying]

        # Robust parsing for: LearnFromDeck(lvl), LearnFromDeck(lvl, name), LearnFromDeck(type, lvl)
        if arg2 is None:
            # Case: LearnFromDeck(max_level)
            max_level = arg1
            card_name = None
        elif str(arg1).isdigit():
            # Case: LearnFromDeck(max_level, card_name)
            max_level = int(arg1)
            card_name = arg2
        else:
            # Case: LearnFromDeck("Skill", max_level) - Old style compatibility
            max_level = arg2
            card_name = None

        # Inferred types for learning
        types_list = [CardType.SKILL, CardType.INSTANT]
        
        candidates = self._find_candidates(player, max_level, types_list, card_name)
        
        if not candidates: return

        if len(candidates) == 1:
            card = candidates[0]
            try:
                player.deck.cards.remove(card)
            except ValueError:
                found = False
                for i, c in enumerate(player.deck.cards):
                    if c.name == card.name and c.cardType == card.cardType and c.level == card.level:
                        player.deck.cards.pop(i)
                        found = True
                        break
                if not found: raise
            # Find empty skill slot
            for i in range(len(player.skillSlots)):
                if player.skillSlots[i] is None:
                    player.skillSlots[i] = card
                    break
            random.shuffle(player.deck.cards)
            self.game.logs.append(LogEntry(self.game.turn, self.game.isPlaying, self.game.phase, 
                f"{player.accessorName} reveals and learns {card.name}."))
            self.game.recalculateStats(self.game.isPlaying)
        else:
            player.choice_pending = True
            player.choice_candidates = candidates

    def DrawFromDeck(self, types, max_level, card_name=None):
        import random
        player = self.game.players[self.game.isPlaying]
        
        # Parse types (handle string with || or list)
        types_list = [t.strip() for t in types.split("||")] if isinstance(types, str) else types
        
        candidates = self._find_candidates(player, max_level, types_list, card_name)
        
        if not candidates: return

        if len(candidates) == 1:
            card = candidates[0]
            try:
                player.deck.cards.remove(card)
            except ValueError:
                found = False
                for i, c in enumerate(player.deck.cards):
                    if c.name == card.name and c.cardType == card.cardType and c.level == card.level:
                        player.deck.cards.pop(i)
                        found = True
                        break
                if not found: raise
            player.hand.append(card)
            random.shuffle(player.deck.cards)
            self.game.logs.append(LogEntry(self.game.turn, self.game.isPlaying, self.game.phase, 
                f"{player.accessorName} reveals and draws {card.name}."))
            self.game.recalculateStats(self.game.isPlaying)
        else:
            player.choice_pending = True
            player.choice_candidates = candidates
