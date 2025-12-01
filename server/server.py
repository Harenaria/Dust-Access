
import pickle
import socket
import time
import os
import pandas as pd
from enum import StrEnum
from core.deck import validate_deck, get_deck_specializations

def raw_send(conn, data):
    serialized = pickle.dumps(data)
    conn.sendall(len(serialized).to_bytes(4, byteorder='big'))
    conn.sendall(serialized)


def recv_exact(conn, num_bytes):
    """Read exactly num_bytes from conn or return None if the socket closes."""
    chunks = []
    bytes_remaining = num_bytes
    while bytes_remaining > 0:
        chunk = conn.recv(bytes_remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        bytes_remaining -= len(chunk)
    return b"".join(chunks)

class ClientDisconnected(Exception):
    pass


def get_available_specializations(deck_id=None):
    if deck_id is not None:
        deck_specs = get_deck_specializations(deck_id)
        if deck_specs:
            return deck_specs

    # Fallback to all base specializations if deck has none
    try:
        df = pd.read_csv("./data/Specializations.csv")
        base_specs = df[df['isBase'] == 1]['Name'].tolist()
        return base_specs
    except Exception as e:
        print(f"[!] Error loading specializations: {e}")
        return ["Scraper", "Crawler", "Querist"]  # Fallback


def get_available_decks():
    """Returns list of available deck IDs (numeric CSV files in data/)"""
    decks = []
    data_dir = "./data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith('.csv') and filename != 'Specializations.csv':
                try:
                    deck_id = int(filename.replace('.csv', ''))
                    # Validate deck exists and is readable
                    deck_path = os.path.join(data_dir, filename)
                    if os.path.isfile(deck_path):
                        decks.append(deck_id)
                except ValueError:
                    continue
    return sorted(decks)





class DustServer:
    HOST = "127.0.0.1"
    PORT = 65432
    TIMEOUT_SEC = 5

    def __init__(self):
        self.srvSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srvSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
        self.clients = [None, None]  # Fixed size for 2 players
        self.player_data = [None, None]  # Fixed size for 2 players
        self.srvSock.bind((self.HOST, self.PORT))
        self.srvSock.listen()

    def run(self):
        print(f"[*] Server attivo su {self.HOST}:{self.PORT}")
        # Accept both connections first
        self.wait_for_connection(0)
        self.wait_for_connection(1)
        # Then handle lobby selections (both players are now connected)
        print("[*] Both players connected. Starting lobby selection...")
        # Handle both players' selections concurrently using threading
        import threading
        t0 = threading.Thread(target=self.handle_lobby_selection, args=(0,))
        t1 = threading.Thread(target=self.handle_lobby_selection, args=(1,))
        t0.start()
        t1.start()
        t0.join()
        t1.join()
        print("[*] Partita iniziata.")
        self.game_man()

    @staticmethod
    def sanitize_state(real_game, player_idx_to_send_to):
        import copy
        game_view = copy.deepcopy(real_game)
        opponent_idx = 1 - player_idx_to_send_to
        for card in game_view.players[opponent_idx].hand:
            card.name = "Covered"
            card.Text = "?"
            card.PowerIncrease = 0
            if not hasattr(card, 'CD'): card.CD = 0
        return game_view


    def wait_for_connection(self, player_id: int):
        print(f"[*] Waiting P{player_id + 1}...")
        while True:
            try:
                conn, addr = self.srvSock.accept()
                print(f"[+] P{player_id + 1} connected from {addr}")

                # Set timeout only for connection phase, will be removed during lobby
                conn.settimeout(self.TIMEOUT_SEC)

                self.clients[player_id] = conn
                self.handshake(conn, player_id)  # Handshake ID and lobby data
                # Remove timeout for lobby selection (players may take time to decide)
                conn.settimeout(None)
                return True
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[!] P{player_id + 1} connection failed: {e}")

    def game_man(self):
        from core.enums import Winner
        from core.game import matchCreator
        
        # Create game with player data from lobby
        p1_data = self.player_data[0]
        p2_data = self.player_data[1]
        game = matchCreator(
            p1_data['name'], p1_data['deck_id'], p1_data['spec'],
            p2_data['name'], p2_data['deck_id'], p2_data['spec']
        )
        game.nextPhase()  # game actually starts!
        while game.winner == Winner.NONE:
            try:
                self.send_to(0, self.sanitize_state(game, 0))
                self.send_to(1, self.sanitize_state(game, 1))

                #Phase management:
                #The GameMan resolves a phase and then sends the player a sanitized copy of the state. The client responds and the cycle continues until someone wins.

                from core.enums import Phases
                if game.phase in [Phases.START, Phases.LOOT]:
                    print(f"[*] Auto-advancing phase {game.phase.name}...")
                    time.sleep(0.5)
                    game.nextPhase()
                    continue

                active = game.isPlaying

                self.clients[active].settimeout(None)
                try:
                    action_dict = self.recv_from(active)
                finally:
                    self.clients[active].settimeout(self.TIMEOUT_SEC)

                print(f"[*] P{active + 1} -> {action_dict['action'].name}")
                acting_player = active
                res = game.receiveAction(acting_player, action_dict['action'], action_dict['args'])
                self.send_to(acting_player, res)

            except ClientDisconnected as e:
                dropout = e.args[0]
                winner = 1 - dropout
                print(f"\n{C.RED}[!] P{dropout + 1} DISCONNESSO.{C.RESET}")
                print(f"{C.GREEN}[*] VITTORIA A TAVOLINO PER P{winner + 1}{C.RESET}")

                game.winner = Winner(winner + 1)

                try:
                    self.send_to(winner, self.sanitize_state(game, winner))
                except Exception as e:
                    print(f"[!] Cannot send winner the closing match data: {e}")
                    pass
                break
        self.cleanup()

    def cleanup(self):
        for c in self.clients:
            if c:
                try:
                    c.close()
                except Exception as e:
                    print(f"[!] Error while closing: {e}")
                    pass
        self.srvSock.close()

    @staticmethod
    def handshake(conn, player_id):
        # Send player ID
        raw_send(conn, player_id)

        lobby_data = {
            'decks': get_available_decks()
        }
        raw_send(conn, lobby_data)
    
    def handle_lobby_selection(self, player_id: int):
        """Handle player selection of specialization and deck"""
        conn = self.clients[player_id]
        
        # If this player already selected, just wait for the other
        if self.player_data[player_id] is not None:
            # Already selected, just wait for ready status
            while self.player_data[1 - player_id] is None:
                time.sleep(0.1)
            return
        
        # First, wait for deck selection
        deck_selected = None
        while deck_selected is None:
            try:
                deck_selection = self.recv_from(player_id)
                
                if not isinstance(deck_selection, dict):
                    raw_send(conn, {"valid": False, "error": "Invalid selection format", "step": "deck"})
                    continue
                
                deck_id = deck_selection.get('deck_id')
                
                # Validate deck exists
                available_decks = get_available_decks()
                if deck_id not in available_decks:
                    raw_send(conn, {"valid": False, "error": f"Invalid deck ID. Available: {available_decks}", "step": "deck"})
                    continue
                
                # Validate deck rules (60 cards, max 3 copies)
                is_valid, error_msg = validate_deck(deck_id)
                if not is_valid:
                    raw_send(conn, {"valid": False, "error": error_msg, "step": "deck"})
                    continue
                
                deck_selected = deck_id
                # Send available specializations for this deck
                available_specs = get_available_specializations(deck_id)
                raw_send(conn, {"valid": True, "step": "deck", "specializations": available_specs})
                
            except ClientDisconnected:
                raise
            except Exception as e:
                print(f"[!] Error in deck selection for P{player_id + 1}: {e}")
                raw_send(conn, {"valid": False, "error": str(e), "step": "deck"})
        
        # Then, wait for specialization and name selection
        while True:
            try:
                selection = self.recv_from(player_id)
                
                if not isinstance(selection, dict):
                    raw_send(conn, {"valid": False, "error": "Invalid selection format", "step": "spec"})
                    continue
                
                spec = selection.get('spec')
                name = selection.get('name', f"P{player_id + 1}")
                
                # Validate specialization (use deck-specific list)
                available_specs = get_available_specializations(deck_selected)
                if spec not in available_specs:
                    raw_send(conn, {"valid": False, "error": f"Invalid specialization. Available: {available_specs}", "step": "spec"})
                    continue
                
                # Store player data
                self.player_data[player_id] = {
                    'name': name,
                    'deck_id': deck_selected,
                    'spec': spec
                }
                
                print(f"[*] P{player_id + 1} selected: {name} | Spec: {spec} | Deck: {deck_selected}")
                raw_send(conn, {"valid": True, "message": "Selection confirmed", "step": "complete"})
                
                # Check if other player is ready
                if self.player_data[1 - player_id] is None:
                    raw_send(conn, {"status": "waiting", "message": "Waiting for opponent..."})
                    # Wait for other player to finish, then send ready
                    while self.player_data[1 - player_id] is None:
                        time.sleep(0.1)
                    # Other player finished, send ready to this player
                    raw_send(conn, {"status": "ready", "message": "Both players ready!"})
                else:
                    # Both players ready, notify both
                    # This player gets ready immediately
                    raw_send(conn, {"status": "ready", "message": "Both players ready!"})
                    # Also notify the other player who was waiting
                    # (The other player's thread is in the waiting loop and will also send ready,
                    # but we send it here too to ensure it's received)
                    if self.clients[1 - player_id]:
                        try:
                            raw_send(self.clients[1 - player_id], {"status": "ready", "message": "Both players ready!"})
                        except Exception as e:
                            print(f"[!] Could not notify P{2 - player_id}: {e}")
                break
                    
            except ClientDisconnected:
                raise
            except Exception as e:
                print(f"[!] Error in specialization selection for P{player_id + 1}: {e}")
                raw_send(conn, {"valid": False, "error": str(e), "step": "spec"})

    def send_to(self, player_idx, data):
        conn = self.clients[player_idx]
        if conn is None: raise ClientDisconnected(player_idx)
        try:
            raw_send(conn, data)
        except Exception:
            raise ClientDisconnected(player_idx)

    def recv_from(self, player_idx):
        conn = self.clients[player_idx]
        if conn is None: raise ClientDisconnected(player_idx)
        try:
            # recv è bloccante ma rispetta il settimeout(TIMEOUT_SEC)
            len_bytes = recv_exact(conn, 4)
            if not len_bytes: raise ClientDisconnected(player_idx)

            msg_len = int.from_bytes(len_bytes, byteorder='big')
            data = recv_exact(conn, msg_len)
            if data is None:
                raise ClientDisconnected(player_idx)
            return pickle.loads(data)
        except socket.timeout:
            print(f"[!] Timeout P{player_idx + 1}!")
            raise ClientDisconnected(player_idx)
        except Exception:
            raise ClientDisconnected(player_idx)

class C(StrEnum):
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"

if __name__ == "__main__":
    srv = DustServer()
    try:
        srv.run()
    except KeyboardInterrupt:
        srv.cleanup()