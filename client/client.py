import pickle
import threading
import os
import time
import sys
from urllib.parse import urlparse
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed


class GameClient:
    def __init__(self):
        # --- ROBUST URL CONSTRUCTION ---
        self.raw_host = os.environ.get("SERVER_HOST", "127.0.0.1")
        self.port = os.environ.get("SERVER_PORT", "8080")
        self.is_render = os.environ.get("RENDER") is not None

        # 1. Clean host
        host_str = self.raw_host
        if "://" in host_str:
            parsed = urlparse(host_str)
            host_str = parsed.netloc  # Extracts "dust-server.onrender.com"

        # 2. Protocol
        protocol = "wss" if self.is_render else "ws"

        # 3. Port (Only add if not standard 80/443 and not implied by Render URL)
        # On Render, SERVER_HOST via fromService usually has no port, but mapped to 443
        port_str = ""
        if not self.is_render:
            port_str = f":{self.port}"

        # 4. Final URI (Must point to /ws)
        self.uri = f"{protocol}://{host_str}{port_str}/ws"

        print(f"--- CLIENT CONFIG ---")
        print(f"Target URI: {self.uri}")
        print(f"Render Mode: {self.is_render}")
        print(f"---------------------")

        self.ws = None
        self.my_id = None
        self._lock = threading.RLock()
        self.player_name = "Player"

    def connect(self):
        print(f"[Client] Attempting connection to {self.uri}...")
        for i in range(5):  # 5 attempts
            try:
                # Increased timeout for slow cold starts
                self.ws = connect(self.uri, open_timeout=20, close_timeout=10)
                print("[Client] Connection ESTABLISHED!")
                return True
            except Exception as e:
                print(f"[Client] Connection attempt {i + 1} failed: {e}")
                time.sleep(2)

        print("[Client] FATAL: Could not connect to server.")
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
                self.ws.send(pickle.dumps(data))
            except Exception as e:
                print(f"[Client] Send Error: {e}")
                self.disconnect()

    def receive_data(self):
        if not self.ws: return None
        try:
            data = self.ws.recv()
            return pickle.loads(data)
        except ConnectionClosed:
            print("[Client] Connection closed by server.")
            self.disconnect()
            return None
        except Exception as e:
            print(f"[Client] Receive Error: {e}")
            return None

    # --- Methods ---
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

    def fetch_game_state(self):
        return self.receive_data()

    def send_action(self, action, args=None):
        if args is None: args = {}
        self._send_data({'action': action, 'args': args})