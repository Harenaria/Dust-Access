import os
import math
import textwrap
import time
from core.game import matchCreator
from core.enums import Actions, Phases, Winner, CardType


# --- CONFIGURAZIONE COLORI ANSI ---
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    INVERT = "\033[7m"  # Inverte background/foreground per header
    RED = "\033[91m"  # Errori, Nemici, Danni
    GREEN = "\033[92m"  # Successi, HP, Buff
    YELLOW = "\033[93m"  # ID, Fasi
    BLUE = "\033[94m"  # Statistiche
    MAGENTA = "\033[95m"  # Skills, CD
    CYAN = "\033[96m"  # Tipo Carta, Equip
    WHITE = "\033[97m"
    DIM = "\033[90m"  # Testo descrittivo


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def is_valid_stat(value):
    """Ritorna True se il valore è un numero valido, non zero e non NaN"""
    if value is None: return False
    try:
        val_float = float(value)
        if math.isnan(val_float): return False
        if val_float == 0: return False
        return True
    except (ValueError, TypeError):
        return False


# --- FORMATTAZIONE CARTE (Box Style) ---

def get_formatted_card_lines(card, index, player, width=96):
    """
    Genera una lista di stringhe formattate per stampare la carta
    all'interno del box (multi-riga) con wrapping del testo e REQUISITI DI LIVELLO.
    """
    lines = []

    # --- Recupero Livello Carta ---
    # Gestisce sia 'Level' (CSV) che 'level' (attributo classe) e converte NaN/None in 1
    try:
        req_lvl = int(getattr(card, 'Level', getattr(card, 'level', 1)))
    except (ValueError, TypeError):
        req_lvl = 1

    # --- RIGA 1: Intestazione (ID, Nome, Livello, Tipo) ---
    header_idx = f"{C.YELLOW}{index}:{C.RESET}"
    header_name = f"{C.BOLD}{card.name}{C.RESET}"

    # Logica visualizzazione Livello
    lvl_str = ""
    if req_lvl > 1:  # Mostra il livello solo se è > 1
        if player.level >= req_lvl:
            # Requisito soddisfatto
            lvl_str = f" {C.CYAN}Lv.{req_lvl}{C.RESET}"
        else:
            # Requisito NON soddisfatto (Rosso e Grassetto)
            lvl_str = f" {C.RED}{C.BOLD}!REQ Lv.{req_lvl}!{C.RESET}"

    header_type = f"{C.DIM}({card.cardType.name}){C.RESET}"

    # Info extra (Cooldown)
    extra_info = ""
    if card.cardType in [CardType.SKILL, CardType.INSTANT]:
        cd = getattr(card, 'CD', 0)
        extra_info = f" {C.MAGENTA}[CD:{cd}]{C.RESET}"

    lines.append(f"{header_idx} {header_name}{lvl_str} {header_type}{extra_info}")

    # --- RIGA 2: Statistiche e Danni ---
    stats_parts = []

    # Equip Stats
    if is_valid_stat(getattr(card, 'PowerIncrease', 0)): stats_parts.append(f"Pow {card.PowerIncrease:+}")
    if is_valid_stat(getattr(card, 'TenacityIncrease', 0)): stats_parts.append(f"Ten {card.TenacityIncrease:+}")
    if is_valid_stat(getattr(card, 'EfficiencyIncrease', 0)): stats_parts.append(f"Eff {card.EfficiencyIncrease:+}")
    if is_valid_stat(getattr(card, 'SensitivityIncrease', 0)): stats_parts.append(f"Sen {card.SensitivityIncrease:+}")
    if is_valid_stat(getattr(card, 'DurabilityIncrease', 0)): stats_parts.append(f"HP {card.DurabilityIncrease:+}")

    # Weapon Stats
    if card.cardType in [CardType.WEAPON, CardType.DUAL]:
        coeff = getattr(card, 'AtkCoeff', 0)
        dmg_str = "Pow"
        if coeff > 0:
            dmg_str += f"+{coeff}"
        elif coeff < 0:
            dmg_str += f"{coeff}"

        attr = f"{C.RED}DMG:{dmg_str}{C.RESET}"
        if getattr(card, 'is2Handed', False):
            attr += f" {C.RED}[2H]{C.RESET}"
        stats_parts.append(attr)

    if stats_parts:
        colored_stats = []
        for s in stats_parts:
            if "\033" in s:
                colored_stats.append(s)
            else:
                colored_stats.append(f"{C.BLUE}{s}{C.RESET}")
        lines.append("   " + " | ".join(colored_stats))

    # --- RIGHE 3+: Testo Completo (Wrappato) ---
    raw_text = getattr(card, 'Text', '')
    if raw_text and str(raw_text).lower() != 'nan':
        wrapper = textwrap.TextWrapper(width=width - 6)
        paragraphs = raw_text.split('\n')

        for p in paragraphs:
            if not p.strip(): continue
            wrapped = wrapper.wrap(p)
            for w_line in wrapped:
                lines.append(f"   {C.DIM}> {w_line}{C.RESET}")

    return lines


# --- RENDERING PRINCIPALE ---

def draw_top_bar(g):
    """Barra di stato singola riga"""
    p_name = g.players[g.isPlaying].accessorName

    # Status turni
    bar = f" TURN {g.turn:<2} | {g.phase.name:<12} | ACTIVE: {p_name} "
    fill = " " * (100 - len(bar))
    print(f"{C.INVERT}{C.BOLD}{bar}{fill}{C.RESET}")


def draw_enemy_compact(p):
    """Visualizzazione compatta del nemico"""
    hp_col = C.GREEN if p.currentHP > p.currentDurability * 0.5 else C.RED

    w = p.equippedCards.get('Weapon')
    w_name = w.name if w else "Unarmed"

    # Armor visualization
    h = p.equippedCards.get('Head')
    c = p.equippedCards.get('Chest')
    b = p.equippedCards.get('Bracers')
    l = p.equippedCards.get('Boots')
    armor = f"{'H' if h else '-'}{'C' if c else '-'}{'B' if b else '-'}{'L' if l else '-'}"

    print(
        f"{C.RED}[ENEMY]{C.RESET} {p.accessorName:<10} | HP: {hp_col}{p.currentHP}/{p.currentDurability}{C.RESET} | Hand: {len(p.hand)} cards | Wpn: {w_name} | Armor: [{armor}]")
    print(f"{C.DIM}{'-' * 100}{C.RESET}")


def draw_player_detailed(p, is_active):
    """Visualizzazione dettagliata del giocatore attivo"""
    border = f"{C.GREEN}│{C.RESET}"
    hp_col = C.GREEN if p.currentHP > p.currentDurability * 0.5 else C.RED

    # Header con Livello Giocatore
    print(
        f"{C.GREEN}┌── {C.BOLD}{p.accessorName}{C.RESET} {C.YELLOW}[Level {p.level}]{C.RESET}{C.GREEN} {'─' * 70}┐{C.RESET}")

    stats = (f"{C.BLUE}POW:{p.currentPower:<2} {C.RESET}| "
             f"{C.BLUE}EFF:{p.currentEfficiency:<2} {C.RESET}| "
             f"{C.BLUE}TEN:{p.currentTenacity:<2} {C.RESET}| "
             f"{C.BLUE}SEN:{p.currentSensitivity:<2}{C.RESET}")

    print(f"{border} {C.BOLD}HP: {hp_col}{p.currentHP}/{p.currentDurability}{C.RESET}   {stats:<50} {' ' * 16}{border}")

    # Action Economy
    if is_active:
        tac = f"{C.GREEN}[X]{C.RESET}" if p.hasTacticalAction else f"{C.RED}[ ]{C.RESET}"
        com = f"{C.GREEN}[X]{C.RESET}" if p.hasCombatAction else f"{C.RED}[ ]{C.RESET}"
        print(f"{border} Actions: Tactical {tac} Combat {com} {' ' * 57}{border}")
    else:
        print(f"{border} {' ' * 86} {border}")

    # Equipaggiamento
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

    # Skill Slots
    print(f"{border} {C.MAGENTA}SKILLS:{C.RESET} ", end="")
    for i, card in enumerate(p.skillSlots):
        if card:
            status = f"{C.RED}CD:{card.currentCD}{C.RESET}" if card.currentCD > 0 else f"{C.GREEN}RDY{C.RESET}"
            print(f"[{i}:{card.name[:9]} {status}] ", end="")
        else:
            print(f"[{i}:Empty{' ' * 5}] ", end="")
    print(f"{' ' * 26}{border}")

    # --- HAND SECTION ---
    print(f"{border} {C.WHITE}HAND ({len(p.hand)}):{C.RESET}{' ' * 77}{border}")

    for i, card in enumerate(p.hand):
        # *** QUI PASSIAMO p (il giocatore) PER IL CONTROLLO LIVELLO ***
        card_lines = get_formatted_card_lines(card, i, p, width=86)

        for line in card_lines:
            print(f"{border} {line}")

        if i < len(p.hand) - 1:
            print(f"{border} {C.DIM}{'-' * 86}{C.RESET} {border}")

    print(f"{C.GREEN}└{'─' * 88}┘{C.RESET}")


def draw_logs(logs):
    if not logs: return
    print(f"{C.DIM}LOGS:{C.RESET}")
    for log in logs[-3:]:
        colored_log = log
        if "damage" in log:
            colored_log = f"{C.RED}{log}{C.RESET}"
        elif "draws" in log:
            colored_log = f"{C.CYAN}{log}{C.RESET}"
        elif "discard" in log:
            colored_log = f"{C.YELLOW}{log}{C.RESET}"
        print(f" > {colored_log}")


def get_valid_commands(game, player_idx):
    """Restituisce la stringa dei comandi disponibili in base allo stato del gioco"""
    phase = game.phase
    p = game.players[player_idx]
    hand = p.hand
    hand_limit = 5

    cmds = []

    if phase == Phases.SETUP:
        # Controllo Mulligan: Se esiste la lista nel gioco e il giocatore è False
        has_mulliganed = False
        if hasattr(game, 'hasMulligan'):
            has_mulliganed = game.hasMulligan[player_idx]

        if not has_mulliganed:
            cmds.append("[M]ulligan")

        cmds.append("[K]eep")

    elif phase == Phases.PREPARATION:
        cmds = ["[P]lace Skill", "[F]inish Phase"]

    elif phase == Phases.DUEL:
        cmds = ["[A]ttack", "[S]kill Activ", "[U]se Equip", "[E]quip Hand", "[C]ast Cantrip", "[F]inish"]

    elif phase == Phases.END:
        if len(hand) > hand_limit:
            cmds = ["[D]iscard"]
        else:
            cmds = ["[F]inish Turn"]

    return " | ".join(cmds)


# --- MAIN LOOP ---

game = matchCreator()
game.nextPhase()  # Entra in SETUP

while game.winner == Winner.NONE:
    clear_screen()

    current_p_idx = game.isPlaying
    act_p = game.players[current_p_idx]
    opp_p = game.players[1 - current_p_idx]

    # 1. Top Bar
    draw_top_bar(game)

    # 2. Enemy Info
    draw_enemy_compact(opp_p)

    # 3. Logs
    draw_logs(game.logs)
    print(f"{C.DIM}{'=' * 100}{C.RESET}")

    # 4. Player Info (Dettagliata + Mano)
    draw_player_detailed(act_p, True)

    # 5. Auto-Advance Logic
    if game.phase in [Phases.START, Phases.LOOT]:
        print(f"\n{C.YELLOW}>>> Processing {game.phase.name}...{C.RESET}")
        time.sleep(0.5)
        game.nextPhase()
        continue

    # 6. Command Input
    # --- MODIFICA QUI ---
    valid_cmds = get_valid_commands(game, current_p_idx)
    # --------------------

    print(f"\n{C.BOLD}COMMANDS:{C.RESET} {valid_cmds}")

    try:
        raw_input = input(f"{C.GREEN}> {C.RESET}").lower().strip()
        if not raw_input: continue

        cmd = raw_input[0]
        res = {}
        idx = -1

        # Helper: parse index se attaccato al comando (es "e1")
        if len(raw_input) > 1 and raw_input[1:].isdigit():
            idx = int(raw_input[1:])

        # --- LOGICA COMANDI ---

        if game.phase == Phases.SETUP:
            if cmd == 'm':
                res = game.receiveAction(current_p_idx, Actions.MULLIGAN, {})
            elif cmd == 'k':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})

        elif game.phase == Phases.PREPARATION:
            if cmd == 'f':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})
            elif cmd == 'p':  # Place Skill
                if idx == -1: idx = int(input("Hand Index: "))
                res = game.receiveAction(current_p_idx, Actions.PLAY, {'index': idx})

        elif game.phase == Phases.DUEL:
            if cmd == 'f':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})
            elif cmd == 'a':  # Attack
                res = game.receiveAction(current_p_idx, Actions.ATTACK, {})
            elif cmd == 's':  # Skill Activate
                if idx == -1: idx = int(input("Skill Slot (0-3): "))
                res = game.receiveAction(current_p_idx, Actions.ACTIVATE, {'source': 'SKILL', 'index': idx})
            elif cmd == 'e':  # Equip from Hand
                if idx == -1: idx = int(input("Hand Index to Equip: "))
                res = game.receiveAction(current_p_idx, Actions.EQUIP, {'index': idx})
            elif cmd == 'c':  # Cast Cantrip (Play)
                if idx == -1: idx = int(input("Cantrip Hand Index: "))
                res = game.receiveAction(current_p_idx, Actions.PLAY, {'index': idx})
            elif cmd == 'u':  # Use/Activate Equip
                print("Slots: [W]eapon [O]ff-Hand [H]ead [C]hest [B]racers [L]egs")
                slot_char = input("Slot: ").lower()
                slot_map = {'w': 'Weapon', 'o': 'Off-Hand', 'h': 'Head', 'c': 'Chest', 'b': 'Bracers', 'l': 'Boots'}
                if slot_char in slot_map:
                    res = game.receiveAction(current_p_idx, Actions.ACTIVATE,
                                             {'source': 'EQUIP', 'slot': slot_map[slot_char]})
                else:
                    print(f"{C.RED}Invalid Slot{C.RESET}")
                    time.sleep(1)

        elif game.phase == Phases.END:
            if len(act_p.hand) > 5:
                if cmd == 'd':
                    if idx == -1: idx = int(input("Discard Index: "))
                    res = game.receiveAction(current_p_idx, Actions.DISCARD, {'index': idx})
            elif cmd == 'f':
                res = game.receiveAction(current_p_idx, Actions.PASS_PHASE, {})

        # --- FEEDBACK ---
        if res and not res.get('valid'):
            print(f"{C.RED}ERROR: {res.get('error')}{C.RESET}")
            time.sleep(1.5)

    except ValueError:
        print(f"{C.RED}Invalid Number Input{C.RESET}")
        time.sleep(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        input("CRASH! Press Enter...")

# Game Over
clear_screen()
winner_name = game.players[game.winner.value - 1].accessorName
print(f"\n{C.GREEN}{'=' * 40}")
print(f"      WINNER: {winner_name}!")
print(f"{'=' * 40}{C.RESET}")