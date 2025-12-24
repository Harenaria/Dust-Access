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
    "Empathy": "Sensitivity", #For legacy name support
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
        self.game = game_state

        # Basic Validation
        if not effect_str or not isinstance(effect_str, str):
            return

        clean_str = effect_str.strip().replace('\x00', '')
        if not clean_str or clean_str.lower() == 'nan':
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
        self.game = None

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
                self.game.players[self.game.isPlaying].id if self.game.players else 0,
                self.game.phase,
                f"Effect Error: {message}"
            ))
        self.logger.error(message)


    def playCounter(self, counterName, num):
        # Fix for CSV parsing sometimes keeping double quotes
        counterName = counterName.replace('"', '')
        active_player_idx = self.game.isPlaying
        for _ in range(num):
            self.game.players[active_player_idx].counters.append(counterName)
        self.game.recalculateStats(active_player_idx)
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.players[active_player_idx].id,
            self.game.phase,
            f"{self.game.players[active_player_idx].accessorName} played {counterName} x{num}."
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
                self.game.players[self.game.isPlaying].id,
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
            self.game.players[self.game.isPlaying].id,
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
            self.game.players[self.game.isPlaying].id,
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
            self.game.players[self.game.isPlaying].id,
            self.game.phase,
            f"{player.accessorName} drew {drawn} card(s)."
        ))
        if drawn > 0:
            player.pending_discard += num
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} must discard {player.pending_discard} card(s)."
            ))

    def Cover(self, amount: int):
        player = self.game.players[self.game.isPlaying]
        player.temp_stats['Tenacity'] += amount
        self.game.recalculateStats(self.game.isPlaying)
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.players[self.game.isPlaying].id,
            self.game.phase,
            f"{player.accessorName} covers for {amount} Tenacity."
        ))

    def Shield(self):
        player = self.game.players[self.game.isPlaying]
        player.shield_active = True
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.players[self.game.isPlaying].id,
            self.game.phase,
            f"{player.accessorName} activates Shield! Next hit will be blocked."
        ))

    def Deflect(self, amount: int):
        player = self.game.players[self.game.isPlaying]
        player.deflect_val = amount
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.players[self.game.isPlaying].id,
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
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} has a 2H Weapon, so Skullsplitter will activate if it hits."
            ))
            final_dmg, is_hit = self.game.checkDamage(self.game.isPlaying, dmg)
            if is_hit:
                target.tactical_silenced = True
                self.game.logs.append(LogEntry(
                    self.game.turn,
                    self.game.players[self.game.isPlaying].id,
                    self.game.phase,
                    f"{player.accessorName} hits! {target.accessorName} is silenced."
                ))
            else:
                self.game.logs.append(LogEntry(
                    self.game.turn,
                    self.game.players[self.game.isPlaying].id,
                    self.game.phase,
                    f"{player.accessorName} missed! Skullsplitter failed."
                ))
        else:
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} does not have a 2H weapon, so Skullsplitter failed."
            ))

    def Battlemaster(self):
        player = self.game.players[self.game.isPlaying]
        # Retrieve choice from Game
        args = getattr(self.game, 'current_action_args', {})
        choice = int(args.get('choice', 0))

        if choice == 0:
            player.temp_stats['Power'] += 2
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} activates Battlemaster, choosing +2 Power."
            ))
        else:
            player.temp_stats['Tenacity'] += 5
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} activates Battlemaster, choosing +5 Tenacity."
            ))
        self.game.recalculateStats(self.game.isPlaying)

    def Kai(self):
        self.playCounter("Kai", 3)
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.players[self.game.isPlaying].id,
            self.game.phase,
            f"{self.game.players[self.game.isPlaying].accessorName} plays Kai! Next three actions will use Power stat for scaling."
        ))

    def NullifyFirstAction(self):
        target = self.game.players[1 - self.game.isPlaying]
        target.statuses.append("Nullified")
        self.game.logs.append(LogEntry(
            self.game.turn,
            self.game.players[self.game.isPlaying].id,
            self.game.phase,
            f"{self.game.players[self.game.isPlaying].accessorName} nullifies {target.accessorName}'s first action."
        ))

    def ifUsedBonusRegain(self):
        player = self.game.players[self.game.isPlaying]
        if not player.hasTacticalAction:
            player.hasTacticalAction = True
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} regains their Tactical Action."
            ))
        else:
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
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
            self.game.logs.append(LogEntry(
                self.game.turn,
                self.game.players[self.game.isPlaying].id,
                self.game.phase,
                f"{player.accessorName} completes the set {clean_name}!"
            )) # Optional verbose log
            if f"Set: {set_name}" not in player.statuses:
                player.statuses.append(f"Set: {set_name}")
            match clean_name:
                case "Valor":
                    player.currentPower += 2
                    player.currentTenacity += 2
        else:
            player.statuses.remove(f"Set: {set_name}")
