# --- PATH CONFIGURATION ---
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any

import websockets
from websockets import ServerConnection

from core.deck import validate_deck
from core.enums import Actions
from core.game import matchCreator, Game
from core.utils import get_available_specializations, get_deck_metadata
from networking.room import Room
from networking.session_manager import SessionManager
from networking.utils import CSActions, sanitized_state, \
    GameEncoder, setup_logging, GLOBAL_PROTOCOL_VERSION

logger = logging.getLogger("WsServer")


class WsServer:
    def __init__(self):
        self.clients: Dict[str, websockets.ServerConnection] = dict()
        self.rooms: dict[str, Room] = {}
        # Used for Game initialization
        self.clientNames: Dict[str, str] = dict()  #client_id, accessor_name
        self.clientDecks: Dict[str, int] = dict()  #client_id, deck_id
        self.clientSpecs: Dict[str, str] = dict()  #client_id, spec_name
        self.clientReady: Dict[str, bool] = dict()

        self.SESSION_PATH = os.environ.get("SESSION_PATH", "sessions.json")
        self.session_manager: SessionManager = SessionManager(storage_path=self.SESSION_PATH)

        #used for keeping track of games
        self.games: Dict[str, Game] = dict()  #room_code, game_state

    async def register_client(self, websocket, client_id: str):
        """Register a new client connection"""
        self.clients[client_id] = websocket

        logger.info(f"WsClient {client_id} connected. Total clients: {len(self.clients)}")
        print(f"WsClient {client_id} connected. Total clients: {len(self.clients)}")

    async def unregister_client(self, client_id: str):
        """Remove client from registry"""
        if client_id in self.clients:
            self.clients.pop(client_id, None)
            #safe removal of client-related data that may or may not exist
            self.clientNames.pop(client_id, None)
            self.clientDecks.pop(client_id, None)
            self.clientSpecs.pop(client_id, None)
            self.clientReady.pop(client_id, None)

            rooms_to_delete = []

            for room_id in self.rooms:
                room = self.rooms[room_id]
                if client_id in room.clients:
                    room.clients.remove(client_id)

                    # GARBAGE COLLECTION:
                    # If the room is empty, mark it for deletion
                    if room.is_empty:
                        rooms_to_delete.append(room)

            # Execute deletion
            for room in rooms_to_delete:
                self.rooms.pop(room)
                # Also, we delete the game state to free memory
                if room.code in self.games:
                    self.games.pop(room.code, None)
                logger.info(f"Room {room.code} deleted (empty). Code freed.")
                print(f"Room {room.code} deleted (empty). Code freed.")

            logger.info(f"WsClient {client_id} disconnected. Remaining clients: {len(self.clients)}")
            print(f"WsClient {client_id} disconnected. Remaining clients: {len(self.clients)}")

    async def handle_client(self, conn: ServerConnection):
        """Handle individual client connection"""
        client_id = None
        try:
            # Wait for the FIRST message, which must be a HANDSHAKE
            message = await asyncio.wait_for(conn.recv(), timeout=5.0)
            data = json.loads(message)

            if data.get("type") != CSActions.HANDSHAKE.value:
                await conn.close(1008, "Policy Violation: Handshake required")
                return

            content = data.get("content", {})

            client_version = content.get("version")
            if client_version != GLOBAL_PROTOCOL_VERSION:
                await conn.send(json.dumps({
                    "type": CSActions.ERROR.value,
                    "content": "RELOAD_REQUIRED"
                }))
                return

            # Identify the client
            provided_id = content.get("client_id")
            provided_secret = content.get("session_secret")

            # Validation logic
            if provided_id and self.session_manager.validate_session(provided_id, provided_secret):
                client_id = provided_id
            else:
                client_id = str(uuid.uuid4())
                secret = str(uuid.uuid4())
                self.session_manager.create_session(client_id, secret)

            # Register and Send Handshake Ack
            self.clients[client_id] = conn
            await conn.send(json.dumps({
                "type": CSActions.HANDSHAKE.value,
                "content": {
                    "client_id": client_id,
                    "session_secret": self.session_manager.sessions[client_id]["secret"],
                    "is_reconnection": (client_id == provided_id)
                }
            }))

            async for message in conn:
                try:
                    data = json.loads(message)
                    print(f"Received from {client_id}: {data}")
                    await self.process_message(client_id, data)
                except json.JSONDecodeError:
                    await conn.send(json.dumps({
                        "type": CSActions.ERROR,
                        "from": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "content": "Invalid JSON format"
                    }))
                except Exception as e:
                    # 'exc_info=True' prints the full stack trace for debugging
                    logger.error(f"[ERR] {client_id} - Processing failed: {e}", exc_info=True)

        except asyncio.TimeoutError:
            logger.info(f"[NET] Handshake timeout. {client_id} disconnected.")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[NET] {client_id} - Disconnected")
        finally:
            await self.unregister_client(client_id)

    async def process_message(self, client_id: str, data: dict):
        """Process incoming client messages"""
        try:
            # Handle potential None or invalid values
            raw_type = data.get("type")
            if raw_type is None:
                raise ValueError("Missing type")
            else:
                message_type = CSActions(raw_type)
        except (ValueError, TypeError):
            logger.warning(f"[ERR] Invalid message type received from {client_id}")
            return
        room_code = data.get("room", "no_room")
        logger.info(f"[{room_code}] [{client_id}] Action: {message_type.name}")
        print(f"[{room_code}] [{client_id}] Action: {message_type.name}")

        match message_type:
            case CSActions.CREATE_ROOM:
                room_code = self._generate_room_code()
                is_private = data.get("content") == "private"
                self.rooms[room_code] = Room(
                    code=room_code,
                    host_id=client_id,
                    clients=[client_id],
                    is_private=is_private
                )
                if is_private:
                    logger.info(f"Client {client_id} created PRIVATE room {room_code}")
                else:
                    logger.info(f"Client {client_id} created public room {room_code}")
                message = {
                    "type": CSActions.ROOM_JOINED.value,
                    "room": room_code,
                    "from": "Server",
                    "timestamp": datetime.now().isoformat(),
                    "content": {"room": room_code, "client_id": client_id}
                }
                await self.clients[client_id].send(json.dumps(message))
                logger.info(f"Client {client_id} created room {room_code}")

            case CSActions.JOIN:
                # Extract Room Code reliably
                room_code = data.get("room")
                content = data.get("content")

                # Fallback if the client put the room code in content
                if not room_code:
                    if isinstance(content, str) and len(content) <= 6:  # Likely a room code
                        room_code = content
                    elif isinstance(content, dict):
                        room_code = content.get("room")

                # Extract Reconnection ID (if any): If content is a UUID string, it's an old_client_id
                old_client_id = content if (isinstance(content, str) and len(content) > 10) else None

                # Process Join/Rejoin
                if room_code and room_code in self.rooms:
                    if old_client_id and old_client_id in self.rooms[room_code].clients:
                        # REJOIN: Replace old connection with new one
                        idx = self.rooms[room_code].clients.index(old_client_id)
                        self.rooms[room_code].clients[idx] = client_id

                        # Transfer data (Names, Decks, etc.)
                        if old_client_id in self.clientNames: self.clientNames[client_id] = self.clientNames.pop(
                            old_client_id)
                        if old_client_id in self.clientDecks: self.clientDecks[client_id] = self.clientDecks.pop(
                            old_client_id)
                        if old_client_id in self.clientSpecs: self.clientSpecs[client_id] = self.clientSpecs.pop(
                            old_client_id)
                        if old_client_id in self.clientReady: self.clientReady[client_id] = self.clientReady.pop(
                            old_client_id)

                        logger.info(f"Client {client_id} successfully REJOINED {room_code}")
                    else:
                        # NORMAL JOIN
                        if client_id not in self.rooms[room_code].clients:
                            self.rooms[room_code].clients.append(client_id)
                        logger.info(f"Client {client_id} JOINED {room_code}")

                    # Always send confirmation
                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ROOM_JOINED.value,
                        "room": room_code,
                        "content": {"room": room_code, "client_id": client_id}
                    }))

                    # If the game is active, send full state
                    if room_code in self.games:
                        await self.send_update_to_clients("Server", room_code)
                    else:
                        await self._broadcast_lobby_state(room_code)

                else:
                    # ROOM NOT FOUND
                    logger.warning(f"Join rejected: Room {room_code} does not exist.")
                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ERROR.value,
                        "content": f"Room {room_code} no longer exists."
                    }))

            case CSActions.QUICK_MATCH:
                target_room = next((r for r in self.rooms.values()
                                    if r.is_joinable_via_quick_match), None)
                # Join or Create
                if target_room:
                    # --- JOIN LOGIC ---
                    code = str(target_room.code)
                    self.rooms[code].clients.append(client_id)
                    logger.info(f"Quick Match: Client {client_id} matched into {target_room}")

                    # Notify the JOINER Object of type Room is not JSON serializable

                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ROOM_JOINED.value,
                        "room": code,
                        "from": "Server",
                        "timestamp": datetime.now().isoformat(),
                        "content": {"room": code, "client_id": client_id}
                    }))
                    # Notify the WAITING PLAYER (Opponent)
                    opponent_id = self.rooms[target_room.code].clients[0]
                    if opponent_id in self.clients:
                        await self.clients[opponent_id].send(json.dumps({
                            "type": CSActions.INFO.value,
                            "content": "A player has found your room via Quick Match!"
                        }))
                    await self._broadcast_lobby_state(target_room.code)
                else:
                    new_room_code = self._generate_room_code()
                    self.rooms[new_room_code] = Room(
                        code=new_room_code,
                        host_id=client_id,
                        clients=[client_id],
                        is_private=False,
                    )
                    logger.info(f"Quick Match: No rooms found. Created {new_room_code}")

                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ROOM_JOINED.value,
                        "room": new_room_code,
                        "from": "Server",
                        "timestamp": datetime.now().isoformat(),
                        "content": {"room": new_room_code, "client_id": client_id}
                    }))
            case CSActions.GET_DECK:
                room_code = data.get("room")
                language = data.get("content") #localization name received
                if room_code in self.rooms:
                    message = {
                        "type": CSActions.DECKS_AVAILABLE.value,
                        "room": room_code,
                        "from": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "content": get_deck_metadata(language)
                    }
                    await self.clients[client_id].send(json.dumps(message))
            case CSActions.SEND_DECK:
                room_code = data.get("room")
                if room_code in self.rooms:
                    deck_id = data.get("content")
                    if validate_deck(deck_id)[0]:
                        self.clientDecks[client_id] = deck_id
                        message = {
                            "type": CSActions.DECK_ISVALID.value,
                            "room": room_code,
                            "from": client_id,
                            "timestamp": datetime.now().isoformat(),
                            "content": deck_id
                        }
                    else:
                        message = {
                            "type": CSActions.ERROR.value,
                            "room": room_code,
                            "from": client_id,
                            "timestamp": datetime.now().isoformat(),
                            "content": "Invalid deck!"
                        }
                    await self.clients[client_id].send(json.dumps(message))
                    await self._broadcast_lobby_state(room_code)
            case CSActions.GET_SPEC:
                room_code = data.get("room")
                if room_code in self.rooms:
                    deck_id = self.clientDecks[client_id]
                    specs = get_available_specializations(deck_id)
                    message = {
                        "type": CSActions.SPECS_AVAILABLE.value,
                        "room": room_code,
                        "from": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "content": specs
                    }
                    await self.clients[client_id].send(json.dumps(message))
            case CSActions.SEND_SPEC:
                room_code = data.get("room")
                if room_code in self.rooms:
                    spec = data.get("content")
                    self.clientSpecs[client_id] = spec
                    message = {
                        "type": CSActions.SPEC_ISVALID.value,
                        "room": room_code,
                        "from": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "content": "Specialization is accepted!"
                    }
                    await self.clients[client_id].send(json.dumps(message))
                    await self._broadcast_lobby_state(room_code)
            case CSActions.SET_NAME:
                accessor_name = data.get("content")
                room_code = data.get("room")
                self.clientNames[client_id] = accessor_name
                await self._broadcast_lobby_state(room_code)
            case CSActions.PLAYER_READY:
                client_id = data.get("content")
                room_code = data.get("room")
                self.clientReady[client_id] = True
                await self._broadcast_lobby_state(room_code)
            case CSActions.START_GAME:
                room_code = data.get("room")
                if not self._validate_room_membership(client_id, room_code): return

                # Only P1 can start the game
                if self.rooms[room_code].clients[0] != client_id:
                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ERROR.value,
                        "content": "Only the host can start the game."
                    }))
                    return
                for client in self.rooms[room_code].clients:
                    if not self.clientReady[client]:
                        await self.clients[client].send(json.dumps({
                            "type": CSActions.ERROR.value,
                            "from": "Server",
                            "timestamp": datetime.now().isoformat(),
                            "content": f"{client} is not ready."
                        }))
                        return
                # for now, only 2 player matches are supported
                if room_code in self.rooms and self.rooms[room_code].is_full:
                    p1_id = self.rooms[room_code].clients[0]
                    p2_id = self.rooms[room_code].clients[1]
                    game_state = matchCreator(
                        room_code,
                        self.clientNames.get(p1_id, "Player 1"),
                        self.clientDecks[p1_id],
                        self.clientSpecs[p1_id],
                        self.clientNames.get(p2_id, "Player 2"),
                        self.clientDecks[p2_id],
                        self.clientSpecs[p2_id]
                    )
                    self.games[room_code] = game_state
                    await self.send_update_to_clients(client_id, room_code)
                    logger.info(f"[{room_code}] MATCH STARTED between {p1_id} and {p2_id}")
                else:
                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ERROR.value,
                        "from": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "content": "Not enough players in the room!"
                    }))
                    logger.info(f"[{room_code}] Not enough players in the room to start a match.")
            case CSActions.ACTION_EXECUTED:
                if not self._validate_room_membership(client_id, room_code):
                    logger.warning(f"Security Alert: {client_id} tried to act in {room_code} without membership.")
                    await self.unregister_client(client_id)
                    return

                try:
                    action_and_args: tuple[int, Dict[str, Any]] = data.get("content")
                    action = Actions(data.get("content")[0])
                except (ValueError, TypeError):
                    logger.info(f"[ERR] Invalid action received from {client_id}")
                    return
                try:
                    pid = self.rooms[room_code].clients.index(client_id)
                    result = self.games[room_code].receiveAction(pid, action, action_and_args[1])
                except ValueError:
                    logger.error(f"Player {client_id} not found in room {room_code}")
                    return

                if result["valid"]:
                    if room_code in self.rooms:
                        await self.send_update_to_clients(client_id, room_code)
                        logger.info(f"[{room_code}] [{client_id}] Gameplay Move: {action.name}")
                        if "message" in result:
                            await self.clients[client_id].send(json.dumps({
                                "type": CSActions.INFO.value,
                                "from": "Server",
                                "timestamp": datetime.now().isoformat(),
                                "content": result["message"]
                            }))
                else:
                    logger.info(f"Action failed for {client_id}: {result['error']}")
                    await self.clients[client_id].send(json.dumps({
                        "type": CSActions.ERROR.value,
                        "from": "Server",
                        "timestamp": datetime.now().isoformat(),
                        "content": result["error"]
                    }))
            case CSActions.REMATCH:
                pass  #TODO: Rematch logic
            case _:
                pass

    def _generate_room_code(self, length=4) -> str:
        import random
        #Avoids ambiguous characters
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        max_attempts = 1000
        for _ in range(max_attempts):
            code = ''.join(random.choices(chars, k=length))
            if code not in self.rooms:
                return code
        logger.warning("Room codes saturated, increasing length.")
        return self._generate_room_code(length + 1)

    def _validate_room_membership(self, client_id: str, room_name: str) -> bool:
        if room_name not in self.rooms:
            return False
        return client_id in self.rooms[room_name].clients

    async def _broadcast_lobby_state(self, room_id: str):
        """
        Sends a packet to all clients in the room containing:
        - Player names
        - Player connection status (implicit)
        - Selected Decks
        """
        if room_id not in self.rooms: return
        print(f"[{room_id}] Broadcasting lobby state.")

        clients = self.rooms[room_id].clients

        # Build the state object
        lobby_data = {
            "room_id": room_id,
            "players": []
        }

        for i, cid in enumerate(clients):
            # Get the player's name or a default one
            name = self.clientNames.get(cid, f"Player {i + 1}")

            # Get ready status
            is_ready = (cid in self.clientDecks and cid in self.clientSpecs and cid in self.clientReady)

            lobby_data["players"].append({
                "id": cid,
                "index": i,  # 0 = Host, 1 = Challenger
                "name": name,
                "ready": is_ready
            })

        message = {
            "type": CSActions.LOBBY_UPDATE.value,
            "room": room_id,
            "from": "Server",
            "timestamp": datetime.now().isoformat(),
            "content": lobby_data
        }

        # Send the update to everyone in the room
        for cid in clients:
            if cid in self.clients:
                await self.clients[cid].send(json.dumps(message))

    async def send_update_to_clients(self, sender: str, room_code: str):
        print(f"[{room_code}] Sending game state update to all clients.")
        for i, cid in enumerate(self.rooms[room_code].clients):
            if cid not in self.clients:
                continue
            message = {
                "type": CSActions.UPDATED_STATE.value,
                "room": room_code,
                "from": sender,
                "timestamp": datetime.now().isoformat(),
                "content": json.dumps(
                    sanitized_state(self.games[room_code], i),
                    cls=GameEncoder  #useful as Game wouldn't be serializable otherwise
                )
                # every client gets their own sanitized state with only covered cards in the opponent's hand
            }
            await self.clients[cid].send(json.dumps(message))

    async def start_server(self):
        """Start the WebSocket networking"""
        asyncio.create_task(self._zombie_cleaner_loop())
        setup_logging()
        host = os.environ.get("HOST", "0.0.0.0")
        port = os.getenv("PORT", 8765)
        logger.info(f"Starting WebSocket networking on {host}:{port}")
        async with websockets.serve(
                self.handle_client,
                host,
                port,
                ping_interval=5,
                ping_timeout=3
        ):
            await asyncio.Future()

    async def _zombie_cleaner_loop(self):
        while True:
            self.session_manager.cleanup_zombies()
            await asyncio.sleep(3600)  # Run cleanup every hour


def server_factory() -> WsServer:
    server = WsServer()
    asyncio.run(server.start_server())
    return server


if __name__ == "__main__":
    server_factory()
