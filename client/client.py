import pickle
import threading
import os
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed


class GameClient:
    def __init__(self):
        self.host = os.environ.get("SERVER_HOST", "127.0.0.1")
        port = os.environ.get("SERVER_PORT", "8080")

        protocol = "wss" if os.environ.get("RENDER") else "ws"

        # Costruzione URI
        if "://" in self.host:
            self.uri = self.host
        else:
            self.uri = f"{protocol}://{self.host}:{port}"

        print(f"[Client] Connecting to: {self.uri}")

        self.ws = None
        self.my_id = None
        self._lock = threading.RLock()
        self.player_name = "Player"

    def connect(self):
        try:
            # Open a blocking WebSocket connection
            self.ws = connect(self.uri)
            return True
        except Exception as e:
            print(f"Connection Error: {e}")
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
            if not self.ws: raise ConnectionError("Not connected")
            try:
                # Serialize and send as binary frame
                serialized = pickle.dumps(data)
                self.ws.send(serialized)
            except Exception:
                self.disconnect()
                raise

    def receive_data(self):
        if not self.ws: return None
        try:
            # Receive binary frame (WebSocket handles length automatically)
            data = self.ws.recv()
            if not data: return None
            return pickle.loads(data)
        except ConnectionClosed:
            self.disconnect()
            return None
        except Exception as e:
            print(f"Receive Error: {e}")
            return None

    # --- Lobby Methods ---
    def wait_for_player_id(self):
        self.my_id = self.receive_data()
        return self.my_id

    def fetch_lobby_decks(self):
        return self.receive_data()

    def send_deck_selection(self, deck_id):
        self._send_data({'deck_id': deck_id})

    def wait_for_lobby_response(self):
        return self.receive_data()

    def send_spec_selection(self, spec_name, player_name):
        self._send_data({'spec': spec_name, 'name': player_name})

    # --- Game Methods ---
    def fetch_game_state(self):
        return self.receive_data()

    def send_action(self, action_enum, args=None):
        if args is None: args = {}
        payload = {'action': action_enum, 'args': args}
        try:
            self._send_data(payload)
        except:
            pass