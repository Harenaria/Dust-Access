class Effects:
    def __init__(self):
        self.game = None

    def playCounter(self, counterName, num):
        # Aggiunge i counter al giocatore attivo
        active_player_idx = self.game.isPlaying
        for _ in range(num):
            self.game.players[active_player_idx].counters.append(counterName)

        self.game.recalculateStats(active_player_idx)


def solveEffect(effectStr, resolver, gameState):
    resolver.game = gameState
    if effectStr is None or not isinstance(effectStr, str):
        return

    clean_effect = effectStr.replace('\x00', '').strip()

    if not clean_effect or clean_effect.lower() == 'nan':
        return

    try:
        context = {
            method_name: getattr(resolver, method_name)
            for method_name in dir(resolver)
            if callable(getattr(resolver, method_name)) and not method_name.startswith("__")
        }

        eval(clean_effect, {"__builtins__": None}, context)

    except SyntaxError:
        print(f"[Effect Error] Invalid Syntax: '{clean_effect}'")
    except Exception as e:
        print(f"[Effect Error] Executing '{clean_effect}': {e}")