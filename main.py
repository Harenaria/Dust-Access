import socket
import pickle
import os
import math
import textwrap
import time
import sys

from core.enums import Actions, Phases, Winner, CardType

# --- CONFIGURAZIONE RETE ---
HOST = '127.0.0.1'
PORT = 65432


# --- COLORI ANSI ---
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    INVERT = "\033[7m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    DIM = "\033[90m"


# --- UTILS RETE ---
def send_data(sock, data):
    serialized = pickle.dumps(data)
    sock.sendall(len(serialized).to_bytes(4, byteorder='big'))
    sock.sendall(serialized)


def recv_exact(sock, num_bytes):
    """Read exactly num_bytes from sock or return None if connection closes."""
    chunks = []
    bytes_remaining = num_bytes
    while bytes_remaining > 0:
        packet = sock.recv(bytes_remaining)
        if not packet:
            return None
        chunks.append(packet)
        bytes_remaining -= len(packet)
    return b"".join(chunks)


def recv_data(sock):
    try:
        len_bytes = recv_exact(sock, 4)
        if not len_bytes: return None
        msg_len = int.from_bytes(len_bytes, byteorder='big')
        data = recv_exact(sock, msg_len)
        if data is None:
            return None
        return pickle.loads(data)
    except (ConnectionResetError, socket.error):
        return None


# --- UTILS VISUALIZZAZIONE ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def is_valid_stat(value):
    if value is None: return False
    try:
        val_float = float(value)
        if math.isnan(val_float): return False
        if val_float == 0: return False
        return True
    except (ValueError, TypeError):
        return False


def get_formatted_card_lines(card, index, player, width=96):
    lines = []
    try:
        req_lvl = int(getattr(card, 'Level', getattr(card, 'level', 1)))
    except:
        req_lvl = 1

    header_idx = f"{C.YELLOW}{index}:{C.RESET}"
    header_name = f"{C.BOLD}{card.name}{C.RESET}"

    lvl_str = ""
    if req_lvl > 1:
        if player.level >= req_lvl:
            lvl_str = f" {C.CYAN}Lv.{req_lvl}{C.RESET}"
        else:
            lvl_str = f" {C.RED}{C.BOLD}!REQ Lv.{req_lvl}!{C.RESET}"

    ctype_name = card.cardType.name if hasattr(card, 'cardType') else "UNKNOWN"
    header_type = f"{C.DIM}({ctype_name}){C.RESET}"

    extra_info = ""
    if hasattr(card, 'cardType') and card.cardType in [CardType.SKILL, CardType.INSTANT]:
        cd = getattr(card, 'CD', 0)
        extra_info = f" {C.MAGENTA}[CD:{cd}]{C.RESET}"

    lines.append(f"{header_idx} {header_name}{lvl_str} {header_type}{extra_info}")

    stats_parts = []
    if is_valid_stat(getattr(card, 'PowerIncrease', 0)): stats_parts.append(f"Pow {card.PowerIncrease:+}")
    if is_valid_stat(getattr(card, 'TenacityIncrease', 0)): stats_parts.append(f"Ten {card.TenacityIncrease:+}")
    if is_valid_stat(getattr(card, 'EfficiencyIncrease', 0)): stats_parts.append(f"Eff {card.EfficiencyIncrease:+}")
    if is_valid_stat(getattr(card, 'SensitivityIncrease', 0)): stats_parts.append(f"Sen {card.SensitivityIncrease:+}")
    if is_valid_stat(getattr(card, 'DurabilityIncrease', 0)): stats_parts.append(f"HP {card.DurabilityIncrease:+}")

    if hasattr(card, 'cardType') and card.cardType in [CardType.WEAPON, CardType.DUAL]:
        coeff = getattr(card, 'AtkCoeff', 0)
        dmg_str = "Pow"
        if coeff > 0:
            dmg_str += f"+{coeff}"
        elif coeff < 0:
            dmg_str += f"{coeff}"
        attr = f"{C.RED}DMG:{dmg_str}{C.RESET}"
        if getattr(card, 'is2Handed', False): attr += f" {C.RED}[2H]{C.RESET}"
        stats_parts.append(attr)

    if stats_parts:
        colored_stats = []
        for s in stats_parts:
            if "\033" in s:
                colored_stats.append(s)
            else:
                colored_stats.append(f"{C.BLUE}{s}{C.RESET}")
        lines.append("   " + " | ".join(colored_stats))

    raw_text = getattr(card, 'Text', '')
    if raw_text and str(raw_text).lower() != 'nan' and raw_text != "???":
        wrapper = textwrap.TextWrapper(width=width - 6)
        paragraphs = raw_text.split('\n')
        for p in paragraphs:
            if not p.strip(): continue
            wrapped = wrapper.wrap(p)
            for w_line in wrapped:
                lines.append(f"   {C.DIM}> {w_line}{C.RESET}")
    return lines


def draw_top_bar(g, my_idx):
    p_name = g.players[g.isPlaying].accessorName

    phase_lbl = g.phase.name
    if g.phase == Phases.SETUP:
        ready = getattr(g, 'ready_in_setup', [False, False])
        if ready[my_idx] and not ready[1 - my_idx]:
            phase_lbl = "WAITING OPP."
        elif not ready[my_idx]:
            phase_lbl = "DECIDE HAND"

    status = "YOUR TURN" if g.isPlaying == my_idx else "OPPONENT TURN"
    col = C.GREEN if g.isPlaying == my_idx else C.RED

    bar = f" TURN {g.turn:<2} | {phase_lbl:<12} | ACTIVE: {p_name} | {status} "
    fill = " " * (100 - len(bar))
    print(f"{C.INVERT}{C.BOLD}{bar}{fill}{C.RESET}")


def draw_enemy_compact(p):
    hp_col = C.GREEN if p.currentHP > p.currentDurability * 0.5 else C.RED
    w = p.equippedCards.get('Weapon')
    w_name = w.name if w else "Unarmed"
    h, c, b, l = p.equippedCards.get('Head'), p.equippedCards.get('Chest'), p.equippedCards.get(
        'Bracers'), p.equippedCards.get('Boots')
    armor = f"{'H' if h else '-'}{'C' if c else '-'}{'B' if b else '-'}{'L' if l else '-'}"
    print(
        f"{C.RED}[ENEMY]{C.RESET} {p.accessorName:<10} | HP: {hp_col}{p.currentHP}/{p.currentDurability}{C.RESET} | Wpn: {w_name} | Arm: [{armor}]")
    print(f"{C.WHITE}HAND ({len(p.hand)}):{C.RESET} ", end="")
    if not p.hand:
        print(f"{C.DIM}(Empty){C.RESET}")
    else:
        for _ in p.hand: print(f"{C.DIM}[#]{C.RESET} ", end="")
        print()
    print(f"{C.DIM}{'-' * 100}{C.RESET}")


def draw_player_detailed(p, is_active):
    border = f"{C.GREEN}│{C.RESET}"
    hp_col = C.GREEN if p.currentHP > p.currentDurability * 0.5 else C.RED
    print(
        f"{C.GREEN}┌── {C.BOLD}{p.accessorName}{C.RESET} {C.YELLOW}[Level {p.level}]{C.RESET}{C.GREEN} {'─' * 70}┐{C.RESET}")
    stats = (
        f"{C.BLUE}POW:{p.currentPower:<2} {C.RESET}| {C.BLUE}EFF:{p.currentEfficiency:<2} {C.RESET}| {C.BLUE}TEN:{p.currentTenacity:<2} {C.RESET}| {C.BLUE}SEN:{p.currentSensitivity:<2}{C.RESET}")
    print(f"{border} {C.BOLD}HP: {hp_col}{p.currentHP}/{p.currentDurability}{C.RESET}   {stats:<50} {' ' * 16}{border}")

    if is_active:
        tac = f"{C.GREEN}[X]{C.RESET}" if p.hasTacticalAction else f"{C.RED}[ ]{C.RESET}"
        com = f"{C.GREEN}[X]{C.RESET}" if p.hasCombatAction else f"{C.RED}[ ]{C.RESET}"
        print(f"{border} Actions: Tactical {tac} Combat {com} {' ' * 57}{border}")
    else:
        print(f"{border} {' ' * 86} {border}")

    w = p.equippedCards.get('Weapon')
    o = p.equippedCards.get('Off-Hand')
    w_str = w.name[:18] if w else "Unarmed"
    o_str = o.name[:18] if o else "Empty"
    h, c, b, l = p.equippedCards.get('Head'), p.equippedCards.get('Chest'), p.equippedCards.get(
        'Bracers'), p.equippedCards.get('Boots')
    armor_str = ""
    for piece, label in [(h, 'H'), (c, 'C'), (b, 'B'), (l, 'L')]:
        state = f"{C.GREEN}■{C.RESET}" if piece else f"{C.DIM}□{C.RESET}"
        armor_str += f"{state}{label} "
    print(
        f"{border} {C.CYAN}WPN:{C.RESET} {w_str:<20} {C.CYAN}OFF:{C.RESET} {o_str:<20} {C.CYAN}ARM:{C.RESET} {armor_str:<25} {' ' * 3}{border}")

    print(f"{border} {C.MAGENTA}SKILLS:{C.RESET} ", end="")
    for i, card in enumerate(p.skillSlots):
        if card:
            status = f"{C.RED}CD:{card.currentCD}{C.RESET}" if card.currentCD > 0 else f"{C.GREEN}RDY{C.RESET}"
            print(f"[{i}:{card.name[:9]} {status}] ", end="")
        else:
            print(f"[{i}:Empty{' ' * 5}] ", end="")
    print(f"{' ' * 26}{border}")

    print(f"{border} {C.WHITE}HAND ({len(p.hand)}):{C.RESET}{' ' * 77}{border}")
    for i, card in enumerate(p.hand):
        card_lines = get_formatted_card_lines(card, i, p, width=86)
        for line in card_lines: print(f"{border} {line}")
        if i < len(p.hand) - 1: print(f"{border} {C.DIM}{'-' * 86}{C.RESET} {border}")
    print(f"{C.GREEN}└{'─' * 88}┘{C.RESET}")


def draw_logs(logs):
    if not logs: return
    print(f"{C.DIM}LOGS:{C.RESET}")
    for log in logs[-3:]:
        colored = log
        if "damage" in log:
            colored = f"{C.RED}{log}{C.RESET}"
        elif "draws" in log:
            colored = f"{C.CYAN}{log}{C.RESET}"
        elif "discard" in log:
            colored = f"{C.YELLOW}{log}{C.RESET}"
        print(f" > {colored}")


def get_valid_commands(phase, hand, my_idx, game):
    cmds = []
    if phase == Phases.SETUP:
        ready = getattr(game, 'ready_in_setup', [False, False])
        if ready[my_idx]: return "WAITING FOR OPPONENT..."
        has_used = getattr(game, 'hasMulligan', [False, False])[my_idx]
        if not has_used: cmds.append("[M]ulligan")
        cmds.append("[K]eep")
    elif phase == Phases.PREPARATION:
        cmds = ["[P]lace Skill", "[F]inish Phase"]
    elif phase == Phases.DUEL:
        cmds = ["[A]ttack", "[S]kill", "[U]se Equip", "[E]quip", "[C]ast", "[F]inish"]
    elif phase == Phases.END:
        if len(hand) > 5:
            cmds = ["[D]iscard"]
        else:
            cmds = ["[F]inish Turn"]
    return " | ".join(cmds)


# --- MAIN ---

def handle_lobby_selection(client, my_id):
    """Handle lobby selection: deck first, then specialization"""
    clear_screen()
    
    # Receive lobby data (decks only)
    lobby_data = recv_data(client)
    if not isinstance(lobby_data, dict):
        print(f"{C.RED}Error: Invalid lobby data{C.RESET}")
        return None
    
    decks = lobby_data.get('decks', [])
    
    if not decks:
        print(f"{C.RED}Error: No decks available{C.RESET}")
        return None
    
    print(f"{C.BOLD}{C.CYAN}=== LOBBY SELECTION ==={C.RESET}\n")
    print(f"{C.YELLOW}You are: P{my_id + 1}{C.RESET}\n")
    
    # Step 1: Select deck
    print(f"{C.BOLD}Step 1: Select Deck{C.RESET}")
    print(f"{C.BOLD}Available Decks:{C.RESET}")
    for deck_id in decks:
        print(f"  {C.GREEN}Deck {deck_id}{C.RESET}")
    
    deck_selected = None
    while deck_selected is None:
        try:
            choice = input(f"\n{C.GREEN}Select deck ID ({decks[0]}-{decks[-1]}): {C.RESET}").strip()
            deck_id = int(choice)
            if deck_id in decks:
                deck_selected = deck_id
            else:
                print(f"{C.RED}Invalid deck ID{C.RESET}")
        except (ValueError, KeyboardInterrupt):
            print(f"{C.RED}Invalid input{C.RESET}")
    
    # Send deck selection
    send_data(client, {'deck_id': deck_selected})
    
    # Wait for deck validation and receive available specializations
    while True:
        response = recv_data(client)
        if response is None:
            print(f"{C.RED}Disconnected from server{C.RESET}")
            return None
        
        if isinstance(response, dict):
            step = response.get('step')
            if step == 'deck':
                if not response.get('valid', True):
                    error = response.get('error', 'Unknown error')
                    print(f"{C.RED}Error: {error}{C.RESET}")
                    # Retry deck selection
                    return handle_lobby_selection(client, my_id)
                else:
                    # Deck validated, get specializations
                    specializations = response.get('specializations', [])
                    if not specializations:
                        print(f"{C.YELLOW}Warning: No specializations found in deck, using defaults{C.RESET}")
                        specializations = ["Scraper", "Crawler", "Querist"]
                    break
    
    # Step 2: Select specialization
    print(f"\n{C.BOLD}Step 2: Select Specialization{C.RESET}")
    print(f"{C.BOLD}Available Specializations (from selected deck):{C.RESET}")
    for i, spec in enumerate(specializations):
        print(f"  {C.GREEN}{i + 1}.{C.RESET} {spec}")
    
    spec_selected = None
    while spec_selected is None:
        try:
            choice = input(f"\n{C.GREEN}Select specialization (1-{len(specializations)}): {C.RESET}").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(specializations):
                spec_selected = specializations[idx]
            else:
                print(f"{C.RED}Invalid selection{C.RESET}")
        except (ValueError, KeyboardInterrupt):
            print(f"{C.RED}Invalid input{C.RESET}")
    
    # Get player name (optional)
    name = input(f"\n{C.GREEN}Enter your name (or press Enter for P{my_id + 1}): {C.RESET}").strip()
    if not name:
        name = f"P{my_id + 1}"
    
    # Send specialization and name selection
    selection = {
        'spec': spec_selected,
        'name': name
    }
    send_data(client, selection)
    
    # Wait for confirmation
    while True:
        response = recv_data(client)
        if response is None:
            print(f"{C.RED}Disconnected from server{C.RESET}")
            return None
        
        if isinstance(response, dict):
            step = response.get('step')
            if step == 'spec':
                if not response.get('valid', True):
                    error = response.get('error', 'Unknown error')
                    print(f"{C.RED}Error: {error}{C.RESET}")
                    # Could retry, but for now just show error and continue
                    continue
            elif step == 'complete':
                # Selection complete
                pass
            
            status = response.get('status')
            if status == 'waiting':
                print(f"{C.YELLOW}{response.get('message', 'Waiting...')}{C.RESET}")
                # Keep waiting for ready status
                continue
            elif status == 'ready':
                print(f"{C.GREEN}{response.get('message', 'Ready!')}{C.RESET}")
                time.sleep(1)
                return True
    
    return True


def main():
    clear_screen()
    print("Connessione...")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
    except:
        print(f"{C.RED}Server non trovato.{C.RESET}")
        return

    # Receive player ID
    my_id = recv_data(client)
    if my_id is None:
        print(f"{C.RED}Failed to receive player ID{C.RESET}")
        return
    
    # Handle lobby selection
    if not handle_lobby_selection(client, my_id):
        return
    
    clear_screen()
    print(f"{C.GREEN}Starting game...{C.RESET}\n")
    time.sleep(1)

    while True:
        # -------------------------------------------------------------
        # 1. RICEZIONE DATI ROBUSTA (FIX CRASH DICT)
        # -------------------------------------------------------------
        incoming_data = recv_data(client)

        # Se il server chiude o crasha
        if incoming_data is None:
            print(f"\n{C.RED}Disconnesso dal server.{C.RESET}")
            break

        # Consumiamo tutti i dizionari in coda (status, conferme, ecc.)
        while isinstance(incoming_data, dict):
            if not incoming_data.get('valid', True):
                print(f"{C.RED}Late Error: {incoming_data.get('error')}{C.RESET}")
            incoming_data = recv_data(client)
            if incoming_data is None:
                print(f"\n{C.RED}Disconnesso dal server.{C.RESET}")
                break
        if incoming_data is None:
            break

        game = incoming_data

        # Controllo di sicurezza finale sul tipo
        if not hasattr(game, 'winner'):
            # Se siamo ancora qui e non è un gioco, qualcosa è rotto seriamente.
            # Proviamo a stampare e saltare il ciclo.
            print(f"{C.RED}Errore Protocollo: Ricevuto {type(game)} invece di Game{C.RESET}")
            continue

        if game.winner != Winner.NONE:
            clear_screen()
            print(f"{C.GREEN}VITTORIA: {game.players[game.winner.value - 1].accessorName}{C.RESET}")
            input()
            break

        # -------------------------------------------------------------
        # 2. RENDER
        # -------------------------------------------------------------
        clear_screen()
        me = game.players[my_id]
        opp = game.players[1 - my_id]

        draw_top_bar(game, my_id)
        draw_enemy_compact(opp)
        draw_logs(game.logs)
        draw_player_detailed(me, game.isPlaying == my_id)

        # -------------------------------------------------------------
        # 3. LOGICA FASI
        # -------------------------------------------------------------

        # Gestione Fasi Automatiche (Start/Loot): Aspetta solo che il server aggiorni
        if game.phase in [Phases.START, Phases.LOOT]:
            print(f"\n{C.YELLOW}>>> Fase Automatica: {game.phase.name}...{C.RESET}")
            time.sleep(0.5)
            continue  # Torna su a ricevere il nuovo stato

        # Controllo Turno
        can_act = (game.isPlaying == my_id)
        if game.phase == Phases.SETUP:
            ready = getattr(game, 'ready_in_setup', [False, False])
            if not ready[my_id]: can_act = True

        if not can_act:
            print(f"\n{C.YELLOW}In attesa dell'avversario...{C.RESET}")
            continue

        # -------------------------------------------------------------
        # 4. INPUT E COMANDI
        # -------------------------------------------------------------
        valid_cmds = get_valid_commands(game.phase, me.hand, my_id, game)
        print(f"\n{C.BOLD}COMMANDS:{C.RESET} {valid_cmds}")

        if "WAITING" in valid_cmds:
            time.sleep(1)
            continue

        action_payload = None
        while action_payload is None:
            try:
                raw = input(f"{C.GREEN}> {C.RESET}").lower().strip()
                if not raw: continue
                c = raw[0]
                idx = -1
                if len(raw) > 1 and raw[1:].isdigit(): idx = int(raw[1:])

                act = None
                args = {}

                if game.phase == Phases.SETUP:
                    if c == 'm':
                        act = Actions.MULLIGAN
                    elif c == 'k':
                        act = Actions.PASS_PHASE
                elif game.phase == Phases.PREPARATION:
                    if c == 'f':
                        act = Actions.PASS_PHASE
                    elif c == 'p':
                        if idx == -1: idx = int(input("Hand Idx: "))
                        act = Actions.PLAY
                        args = {'index': idx}
                elif game.phase == Phases.DUEL:
                    if c == 'f':
                        act = Actions.PASS_PHASE
                    elif c == 'a':
                        act = Actions.ATTACK
                    elif c == 's':
                        if idx == -1: idx = int(input("Slot Idx: "))
                        act = Actions.ACTIVATE
                        args = {'source': 'SKILL', 'index': idx}
                    elif c == 'e':
                        if idx == -1: idx = int(input("Hand Idx: "))
                        act = Actions.EQUIP
                        args = {'index': idx}
                    elif c == 'c':
                        if idx == -1: idx = int(input("Hand Idx: "))
                        act = Actions.PLAY
                        args = {'index': idx}
                    elif c == 'u':
                        slot = input("Slot [W/O/H/C/B/L]: ").lower()
                        m = {'w': 'Weapon', 'o': 'Off-Hand', 'h': 'Head', 'c': 'Chest', 'b': 'Bracers', 'l': 'Boots'}
                        if slot in m: act = Actions.ACTIVATE; args = {'source': 'EQUIP', 'slot': m[slot]}
                elif game.phase == Phases.END:
                    if len(me.hand) > 5:
                        if c == 'd':
                            if idx == -1: idx = int(input("Discard Idx: "))
                            act = Actions.DISCARD
                            args = {'index': idx}
                    elif c == 'f':
                        act = Actions.PASS_PHASE

                if act:
                    action_payload = {'action': act, 'args': args}
                else:
                    print("Comando ignoto.")
            except ValueError:
                print("Input numerico non valido.")

        # -------------------------------------------------------------
        # 5. INVIO E VALIDAZIONE
        # -------------------------------------------------------------
        send_data(client, action_payload)

        # Ricevi conferma
        res = recv_data(client)

        # FIX ROBUSTEZZA 2: Se riceviamo subito lo STATO invece della CONFERMA
        if hasattr(res, 'winner'):
            # Significa che la conferma è andata persa o non inviata, ma lo stato è arrivato.
            # Non possiamo validare l'azione, ma aggiorniamo il gioco per il prossimo ciclo.
            # Però il ciclo ricomincia con recv_data(), quindi dobbiamo gestire questo pacchetto.
            # Purtroppo se lo assegnamo a 'game' qui, verrà sovrascritto all'inizio del loop.
            # Soluzione sporca ma efficace: non fare nulla, il loop riceverà il nuovo stato.
            pass
        elif isinstance(res, dict):
            if not res.get('valid'):
                print(f"{C.RED}ERRORE: {res.get('error')}{C.RESET}")
                time.sleep(2)

        # Il loop ricomincia e scarica il nuovo stato del gioco


if __name__ == "__main__":
    main()