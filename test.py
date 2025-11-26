from core.game import matchCreator
from core.enums import Actions, Phases, Winner


def print_game_state(g):
    p1 = g.players[0]
    p2 = g.players[1]
    print(f"\n{'=' * 20} TURNO {g.turn} - FASE: {g.phase.name} {'=' * 20}")
    print(f"Active Player: {g.players[g.isPlaying].accessorName}")
    print(f"P1 HP: {p1.currentHP} | Hand ({len(p1.hand)}): {[c.name for c in p1.hand]}")
    print(f"P2 HP: {p2.currentHP} | Hand ({len(p2.hand)}): {[c.name for c in p2.hand]}")
    if g.logs:
        print(f"LAST LOG: {g.logs[-1]}")


game = matchCreator()
game.nextPhase()

while game.winner == Winner.NONE:
    print_game_state(game)

    current_p_idx = game.isPlaying

    # --- INPUT HANDLER ---
    try:
        if game.phase == Phases.SETUP:
            print("Opzioni: [M]ulligan, [K]eep Hand (Pass Phase)")
            cmd = input("> ").lower()
            if cmd == 'm':
                res = game.receiveAction(current_p_idx, Actions.MULLIGAN, {})
            elif cmd == 'k':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})
            else:
                print("Comando ignoto")
                continue

        elif game.phase == Phases.LOOT:
            # Se il gioco si ferma qui è perché devi scartare (Hand > 5)
            # Assicurati di aver implementato Actions.DISCARD in receiveAction!
            print("Hand limit exceeded! [D]iscard index")
            cmd = input("> ").lower()
            if cmd == 'd':
                idx = int(input("Index to discard: "))
                res = game.receiveAction(current_p_idx, Actions.DISCARD, {'index': idx})

        elif game.phase == Phases.PREPARATION:
            print("Opzioni: [P]lay Card, [E]quip Card, [A]ctivate Skill/Item, [F]ine Fase")
            cmd = input("> ").lower()

            if cmd == 'f':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})

            elif cmd == 'p':
                idx = int(input("Card Index to Play: "))
                # Qui costruiamo correttamente gli ARGS
                res = game.receiveAction(current_p_idx, Actions.PLAY, {'index': idx})

            elif cmd == 'e':
                idx = int(input("Card Index to Equip: "))
                res = game.receiveAction(current_p_idx, Actions.EQUIP, {'index': idx})

            elif cmd == 'a':
                print("Source? [S]kill or [E]quip slot?")
                src = input("> ").lower()
                if src == 's':
                    i = int(input("Skill Index (0-3): "))
                    res = game.receiveAction(current_p_idx, Actions.ACTIVATE, {'source': 'SKILL', 'index': i})
                elif src == 'e':
                    slot = input("Slot Name (Weapon, Off-Hand, Head...): ")
                    res = game.receiveAction(current_p_idx, Actions.ACTIVATE, {'source': 'EQUIP', 'slot': slot})

        elif game.phase == Phases.DUEL:
            print("Opzioni: [A]ttack, [S]kill/Item Activate, [F]ine Turno")
            cmd = input("> ").lower()
            if cmd == 'a':
                res = game.receiveAction(current_p_idx, Actions.ATTACK, {})
            elif cmd == 'f':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})
                # O Actions.END_TURN se hai mantenuto quella
            elif cmd == 's':
                i = int(input("Skill Index (0-3): "))
                res = game.receiveAction(current_p_idx, Actions.ACTIVATE, {'source': 'SKILL', 'index': i})
                pass
        elif game.phase == Phases.END or game.phase == Phases.START:
            # Se finiamo qui, forza l'avanzamento automatico
            print(f"Fase automatica {game.phase.name}, avanzo...")
            game.nextPhase()

        else:
            # Catch-all per evitare loop infiniti
            print(f"!!! FASE NON GESTITA: {game.phase.name} !!!")
            input("Premi invio per forzare nextPhase o CTRL+C per uscire...")
            game.nextPhase()
        # Stampa risultato azione
        if 'res' in locals():
            print(f"RESULT: {res}")
            if not res.get('valid'):
                print(f"ERROR: {res.get('error')}")
            del res  # Pulisci per il prossimo loop

    except Exception as e:
        print(f"!!! EXCEPTION: {e}")
        import traceback

        traceback.print_exc()

print(f"GAME OVER! Winner: {game.winner}")