import asyncio
import pickle
import os
import logging
import pandas as pd
from aiohttp import web, WSMsgType
from core.deck import validate_deck, get_deck_specializations
from core.enums import Winner, Phases

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DustServer")


# --- HELPER FUNCTIONS ---
def get_available_specializations(deck_id=None):
    if deck_id is not None:
        deck_specs = get_deck_specializations(deck_id)
        if deck_specs: return deck_specs
    try:
        df = pd.read_csv("./data/Specializations.csv")
        return df[df['isBase'] == 1]['Name'].tolist()
    except Exception:
        return ["Scraper", "Crawler", "Querist"]


def get_available_decks():
    decks = []
    data_dir = "./data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith('.csv') and filename != 'Specializations.csv':
                try:
                    decks.append(int(filename.replace('.csv', '')))
                except:
                    continue
    return sorted(decks)


class ClientDisconnected(Exception):
    """Custom exception to handle clean disconnections inside game logic"""
    pass


class GameServer:
    def __init__(self):
        # WebSocket connections
        self.clients = [None, None]
        # Incoming message queues for each player (decouples network from logic)
        self.queues = [asyncio.Queue(), asyncio.Queue()]
        # Lobby Data
        self.player_data = [None, None]
        # Sync Event
        self.connected_event = asyncio.Event()
        # Background Task
        self.game_task = None

    async def health_check(self, request):
        """HTTP Endpoint for Render Health Checks"""
        return web.Response(text="Dust Access Server: Online", status=200)

    async def websocket_handler(self, request):
        """Main WebSocket Handler: manages connection lifecycle and reading loop"""
        # Heartbeat keeps connection alive through proxies/load balancers
        ws = web.WebSocketResponse(heartbeat=30.0)
        await ws.prepare(request)

        # Assign Player ID (0 or 1)
        if self.clients[0] is None:
            pid = 0
        elif self.clients[1] is None:
            pid = 1
        else:
            # Room full
            await ws.close(code=4000, message=b"Room Full")
            return ws

        self.clients[pid] = ws
        # Clear queue on new connection to remove old messages
        self.queues[pid] = asyncio.Queue()

        logger.info(f"Player {pid + 1} connected from {request.remote}")

        try:
            # --- LOBBY PHASE ---
            # We run lobby logic directly here before starting the read loop
            # But we need a way to read messages.
            # To simplify, we start a background task for the Lobby/Game logic
            # and keep this function strictly for Reading from socket.

            if pid == 0:
                # P1 initializes the shared logic when P2 isn't there yet?
                # No, simpler: P1 waits.
                pass

            # Start a task to handle the Logic for this specific player's setup
            setup_task = asyncio.create_task(self.run_player_setup(pid))

            # --- READ LOOP (Keeps Socket Open) ---
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    # Put data into the queue for the logic to consume
                    try:
                        data = pickle.loads(msg.data)
                        await self.queues[pid].put(data)
                    except Exception as e:
                        logger.error(f"Deserialization error P{pid + 1}: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WS Connection closed with exception {ws.exception()}")

            # If loop breaks, connection is closed
            logger.info(f"Player {pid + 1} socket closed.")

        except Exception as e:
            logger.error(f"Unexpected error in handler P{pid + 1}: {e}", exc_info=True)
        finally:
            # Cleanup
            self.clients[pid] = None
            if self.game_task and not self.game_task.done():
                logger.info("Cancelling Game Task due to disconnect...")
                self.game_task.cancel()

        return ws

    # --- LOGIC HANDLING ---

    async def run_player_setup(self, pid):
        """Handles Handshake, Lobby and Sync for a specific player"""
        try:
            # 1. Handshake
            await self.raw_send(pid, pid)
            await self.raw_send(pid, {'decks': get_available_decks()})

            # 2. Lobby Selection
            await self.handle_lobby_selection(pid)

            # 3. Synchronization
            if pid == 0:
                logger.info("P1 Logic: Waiting for P2...")
                await self.connected_event.wait()
            else:
                logger.info("P2 Logic: Triggering Game Start...")
                self.connected_event.set()

            # 4. Start Central Game Manager (Only P1 triggers this to avoid duplicates)
            # Actually, let's have P1 trigger it to ensure single source of truth
            if pid == 0:
                logger.info("P1 Logic: Starting Game Manager...")
                self.game_task = asyncio.create_task(self.game_manager())

        except ClientDisconnected:
            logger.warning(f"Player {pid + 1} logic stopped (Disconnected)")
        except Exception as e:
            logger.error(f"Error in P{pid + 1} setup: {e}", exc_info=True)

    # --- COMMUNICATION PRIMITIVES ---

    async def raw_send(self, pid, data):
        """Sends data to the socket"""
        ws = self.clients[pid]
        if ws is None or ws.closed:
            raise ClientDisconnected(pid)
        try:
            await ws.send_bytes(pickle.dumps(data))
        except Exception:
            raise ClientDisconnected(pid)

    async def recv_from(self, pid):
        """Waits for a message from the internal queue"""
        # This creates the blocking effect for the game logic
        # while allowing the heartbeat loop to run in background.
        if self.clients[pid] is None:
            raise ClientDisconnected(pid)

        try:
            # Wait for data from queue
            data = await self.queues[pid].get()
            return data
        except Exception:
            raise ClientDisconnected(pid)

    # --- LOBBY IMPLEMENTATION ---

    async def handle_lobby_selection(self, pid):
        # Deck Selection
        deck_id = None
        while deck_id is None:
            msg = await self.recv_from(pid)
            d_id = msg.get('deck_id')

            if d_id not in get_available_decks():
                await self.raw_send(pid, {"valid": False, "error": "Invalid Deck", "step": "deck"})
                continue

            valid, err = validate_deck(d_id)
            if not valid:
                await self.raw_send(pid, {"valid": False, "error": err, "step": "deck"})
                continue

            deck_id = d_id
            await self.raw_send(pid, {"valid": True, "step": "deck",
                                      "specializations": get_available_specializations(deck_id)})

        # Spec Selection
        while True:
            msg = await self.recv_from(pid)
            spec = msg.get('spec')
            name = msg.get('name', f"Player {pid + 1}")

            if spec not in get_available_specializations(deck_id):
                await self.raw_send(pid, {"valid": False, "error": "Invalid Spec", "step": "spec"})
                continue

            self.player_data[pid] = {'name': name, 'deck_id': deck_id, 'spec': spec}
            await self.raw_send(pid, {"valid": True, "step": "complete"})

            # Wait for other player data
            other_pid = 1 - pid
            if self.player_data[other_pid] is None:
                await self.raw_send(pid, {"status": "waiting"})
                while self.player_data[other_pid] is None:
                    # Check if client disconnected while waiting
                    if self.clients[pid] is None: raise ClientDisconnected(pid)
                    await asyncio.sleep(0.2)

            await self.raw_send(pid, {"status": "ready"})
            break

    # --- GAME LOOP ---

    async def broadcast_state(self, game):
        for i in [0, 1]:
            try:
                state = self.sanitize_state(game, i)
                await self.raw_send(i, state)
            except ClientDisconnected:
                pass

    @staticmethod
    def sanitize_state(real_game, player_idx_to_send_to):
        import copy
        view = copy.deepcopy(real_game)
        opp_idx = 1 - player_idx_to_send_to
        for card in view.players[opp_idx].hand:
            card.name = "Covered"
            card.Text = "?"
            card.PowerIncrease = 0
            if not hasattr(card, 'CD'): card.CD = 0
        return view

    async def game_manager(self):
        from core.game import matchCreator

        logger.info("--- MATCH STARTING ---")
        p1, p2 = self.player_data
        game = matchCreator(p1['name'], p1['deck_id'], p1['spec'], p2['name'], p2['deck_id'], p2['spec'])

        game.nextPhase()
        await self.broadcast_state(game)

        while True:
            try:
                # 1. Check Win
                if game.winner != Winner.NONE:
                    logger.info(f"WINNER DECIDED: {game.winner.name}")
                    await self.broadcast_state(game)
                    break

                # 2. Auto Phases
                if game.phase in [Phases.START, Phases.LOOT]:
                    await asyncio.sleep(0.5)
                    game.nextPhase()
                    await self.broadcast_state(game)
                    continue

                # 3. Wait for Input
                active_pid = game.isPlaying

                try:
                    # Wait for input with timeout
                    action_data = await asyncio.wait_for(self.recv_from(active_pid), timeout=600.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout P{active_pid + 1}")
                    game.winner = Winner(1 - active_pid + 1)
                    continue

                logger.info(f"P{active_pid + 1} Action: {action_data['action'].name}")
                result = game.receiveAction(active_pid, action_data['action'], action_data['args'])

                await self.raw_send(active_pid, result)
                await self.broadcast_state(game)

            except ClientDisconnected as e:
                loser = e.args[0]
                logger.info(f"Player {loser + 1} Disconnected. Forfeit.")
                game.winner = Winner(1 - loser + 1)
                await self.broadcast_state(game)
                break
            except Exception as e:
                logger.critical(f"Game Logic Error: {e}", exc_info=True)
                break

        logger.info("--- MATCH ENDED ---")


# --- APP FACTORY ---

async def init_app():
    server = GameServer()
    app = web.Application()

    # Routes
    app.router.add_get('/', server.health_check)  # HTTP for Render
    app.router.add_get('/ws', server.websocket_handler)  # WebSocket for Client

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"[*] AIOHTTP Server starting on port {port}")
    web.run_app(init_app(), port=port)