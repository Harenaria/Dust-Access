import asyncio
import json
import logging
import random
from collections import deque
from typing import Optional, TYPE_CHECKING

import websockets
from websockets.asyncio.client import ClientConnection

from core.game import Game
from networking.utils import CSActions, GLOBAL_PROTOCOL_VERSION

if TYPE_CHECKING:
    # Imported only for static type checking; avoids circular imports at runtime
    from client_views.view_interface import ViewInterface


class WsClient:
    def __init__(self, uri: str, client_implementation: "ViewInterface"):
        self.uri = uri
        # We keep this for sending, but we won't rely on it for receiving logic
        self.websocket: Optional[ClientConnection] = None
        self.client_id: Optional[str] = None
        self.room_name: Optional[str] = None
        self.message_queue = deque(maxlen=10)
        self.running = False
        self.connected = False
        self.reconnect_interval = 5
        self.logger = logging.getLogger(f"DustAccessClient")
        self.game_state: Optional[Game] = None
        self.client_implementation: "ViewInterface" = client_implementation
        self.session_secret: Optional[str] = None

        self.reconnect_attempt = 0
        self.base_delay = 1.0  # Start with 1 second
        self.max_delay = 30.0  # Never wait more than 30 seconds
        self.factor = 2.0  # Double the delay each time

    async def start(self):
        """Start the client with automatic reconnection logic."""
        self.running = True
        await self.receive_messages()

    async def receive_messages(self):
        """
        The Main Loop tries to connect and then loops to receive messages forever.
        """
        while self.running:
            try:
                self.logger.info(f"Connecting to {self.uri}...")
                print(f"Connecting to {self.uri}...")
                async with websockets.connect(self.uri) as ws:
                    handshake_msg = {
                        "type": CSActions.HANDSHAKE.value,
                        "content": {
                            "version": GLOBAL_PROTOCOL_VERSION,
                            "client_id": self.client_id,
                            "session_secret": self.session_secret  # You'll need to add this field to WsClient
                        }
                    }
                    await ws.send(json.dumps(handshake_msg))
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(response)
                        # Process handshake data...
                    except asyncio.TimeoutError:
                        self.logger.error("Server handshake timed out. Retrying...")
                        continue

                    if data.get("type") == CSActions.HANDSHAKE.value:
                        content = data["content"]
                        self.client_id = content["client_id"]
                        self.session_secret = content["session_secret"]
                        # Notify the Flet implementation to save these
                        await self.client_implementation.on_handshake_complete(content)
                    else:
                        #Handshake has failed!
                        continue
                    self.reconnect_attempt = 0
                    self.websocket = ws
                    self.connected = True
                    self.logger.info("Connected!")
                    print("Connected to server!")
                        # This only happens on rejoining, so this defines the automatic reconnection to the same room in case of unstable connections.
                    if self.client_id and self.room_name:
                        rejoin_msg = {
                            "type": CSActions.JOIN.value,
                            "room": self.room_name,
                            "content": self.client_id
                        }
                         # We send this directly, bypassing the queue so it hits first
                        await ws.send(json.dumps(rejoin_msg))

                    # Flush Queue (Send messages that accumulated while offline)
                    await self._flush_queue(ws)

                    # Message Loop (Iterate over the connection directly)
                    # This loop automatically exits if the connection closes.
                    async for message in ws:
                        if not self.running:
                            break

                        try:
                            data = json.loads(message)
                            await self.handle_message(data)
                        except json.JSONDecodeError:
                            self.logger.error("Received invalid JSON")
                        except Exception as e:
                            self.logger.error(f"Error handling message: {e}")
                    self.connected = False


            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError):
                self.logger.warning("Connection lost (Server closed connection). Retrying...")
            except (OSError, websockets.exceptions.InvalidURI, websockets.exceptions.InvalidHandshake) as e:
                # Connection failed or dropped
                self.logger.warning(f"Connection issue: {e}. Retrying in {self.reconnect_interval}s...")

            except Exception as e:
                self.logger.error(f"Unexpected error in client loop: {e}", exc_info=True)

            finally:
                # Cleanup when the 'async with' block exits (connection lost)
                self.websocket = None
                if self.running:
                    await self._handle_backoff()

    async def _handle_backoff(self):
        """Calculates and sleeps for the exponential backoff duration."""
        delay = min(
            self.max_delay,
            self.base_delay * (self.factor ** self.reconnect_attempt)
        )

        # Add a random amount (0% to 50% of the delay) to distribute concurrent reconnections
        jitter = delay * 0.5 * random.random()
        total_sleep = delay + jitter

        self.logger.warning(
            f"Connection lost. Retrying in {total_sleep:.2f}s "
            f"(Backoff: {delay:.1f}s, Jitter: {jitter:.1f}s)"
        )

        self.reconnect_attempt += 1
        await asyncio.sleep(total_sleep)
    async def _flush_queue(self, ws: ClientConnection):
        """Ensure the queue is emptied after connection."""
        while self.message_queue:
            msg = self.message_queue.popleft()
            try:
                await ws.send(msg)
            except Exception as e:
                self.logger.error(f"Flush failed: {e}")
                self.message_queue.appendleft(msg) # Put it back
                break

    async def send_message(self, message: dict):
        """Industry-grade send with connection-wait and safety return."""
        message_str = json.dumps(message)

        # If we are currently connecting, wait a bit
        for _ in range(20):
            if self.websocket:
                try:
                    await self.websocket.send(message_str)
                    return
                except Exception as e:
                    self.logger.error(f"Send failed: {e}")
                    break  # Exit loop to queue it instead

            if not self.running:
                break
            await asyncio.sleep(0.1)

        self.logger.info("Socket not ready, queuing message.")
        self.message_queue.append(message_str)

    async def disconnect(self):
        """Gracefully stop the client."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def handle_message(self, data: dict):
        print(f"Received: {data}")
        msg_type = data.get("type")
        msg_content = data.get("content")
        try:
            msg_type = CSActions(msg_type)
        except ValueError:
            self.logger.warning(f"Unknown message type received: {msg_type}")
            return
        match msg_type:
            case CSActions.LOBBY_UPDATE:
                await self.client_implementation.update_lobby(data.get("content"))
            case CSActions.UPDATED_STATE:
                game_data = json.loads(msg_content)
                self.game_state = Game.dict_deserializer(game_data)
                await self.client_implementation.update_to_state(self.game_state)
            case CSActions.ROOM_JOINED:
                if isinstance(msg_content, dict):
                    self.room_name = msg_content.get("room")
                    self.client_id = msg_content.get("client_id")
                else:
                    self.room_name = msg_content
                await self.client_implementation.interpret_message(data)
            case CSActions.ERROR:
                error_msg = str(msg_content)
                self.logger.error(error_msg)
                await self.client_implementation.handle_error(error_msg)
            case CSActions.INFO:
                info_msg = str(msg_content)
                self.logger.info(info_msg)
                await self.client_implementation.show_info(info_msg)
            case _:
                # Other messages require custom handling that depends on the view.
                await self.client_implementation.interpret_message(data)


