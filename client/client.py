import pickle
import threading
import os
import time
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed


class GameClient:
    def __init__(self):
        # 1. Recupera Configurazione
        self.raw_host = os.environ.get("SERVER_HOST", "127.0.0.1")
        self.port = os.environ.get("SERVER_PORT", "8080")
        self.is_render = bool(os.environ.get("RENDER"))

        # 2. Costruisci Base URI (gestisce sia IP locale che URL Render)
        if "://" in self.raw_host:
            # Se SERVER_HOST è un URL completo (es. https://myapp.onrender.com)
            base_uri = self.raw_host.replace("http://", "").replace("https://", "").replace("ws://", "").replace(
                "wss://", "")
            # Rimuovi trailing slash
            if base_uri.endswith("/"): base_uri = base_uri[:-1]
        else:
            base_uri = f"{self.raw_host}:{self.port}"

        # 3. Determina Protocollo
        protocol = "wss" if self.is_render else "ws"

        # 4. URI Finale (punta a /ws come definito nel server aiohttp)
        self.uri = f"{protocol}://{base_uri}/ws"

        print(f"[Client] Target Server: {self.uri}")

        self.ws = None
        self.my_id = None
        self._lock = threading.RLock()
        self.player_name = "Player"

    def connect(self):
        """Tenta la connessione con retry automatico (utile per spin-up cold start)"""
        max_retries = 3
        for i in range(max_retries):
            try:
                self.ws = connect(self.uri, open_timeout=10)  # 10s timeout
                print("[Client] Connected successfully.")
                return True
            except Exception as e:
                print(f"[Client] Connection attempt {i + 1} failed: {e}")
                time.sleep(1)
        return False

    def disconnect(self):
        with self._lock:
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                self.ws = None

    def _send_data(self, data):
        with self._lock:
            if not self.ws: return
            try:
                # Invia dati binari (Pickle)
                self.ws.send(pickle.dumps(data))
            except Exception as e:
                print(f"[Client] Send Error: {e}")
                self.disconnect()

    def receive_data(self):
        if not self.ws: return None
        try:
            # Websockets.sync gestisce il framing automaticamente
            data = self.ws.recv()
            return pickle.loads(data)
        except ConnectionClosed:
            print("[Client] Connection closed by server.")
            self.disconnect()
            return None
        except Exception as e:
            print(f"[Client] Receive Error: {e}")
            return None

    # --- LOBBY METHODS ---
    def wait_for_player_id(self):
        return self.receive_data()

    def fetch_lobby_decks(self):
        return self.receive_data()

    def send_deck_selection(self, deck_id):
        self._send_data({'deck_id': deck_id})

    def wait_for_lobby_response(self):
        return self.receive_data()

    def send_spec_selection(self, spec, name):
        self._send_data({'spec': spec, 'name': name})

    # --- GAME METHODS ---
    def fetch_game_state(self):
        return self.receive_data()

    def send_action(self, action, args=None):
        if args is None: args = {}
        self._send_data({'action': action, 'args': args})