import asyncio
import pickle
import os
import pandas as pd
import websockets
from core.deck import validate_deck, get_deck_specializations
from core.enums import Winner, Phases


# --- HELPER FUNCTIONS ---
def get_available_specializations(deck_id=None):
    if deck_id is not None:
        deck_specs = get_deck_specializations(deck_id)
        if deck_specs: return deck_specs
    try:
        df = pd.read_csv("./data/Specializations.csv")
        return df[df['isBase'] == 1]['Name'].tolist()
    except:
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
    pass


class DustServer:
    def __init__(self):
        self.clients = [None, None]
        self.player_data = [None, None]
        self.connected_event = asyncio.Event()  # To signal when 2 players are ready

    async def run(self):
        port = int(os.environ.get("PORT", 8080))
        print(f"[*] WebSocket Server listening on 0.0.0.0:{port}")

        # Start the WebSocket server
        async with websockets.serve(self.handler, "0.0.0.0", port):
            await asyncio.Future()  # Run forever

    async def handler(self, websocket):
        """Handle new connections"""
        if self.clients[0] is None:
            player_id = 0
        elif self.clients[1] is None:
            player_id = 1
        else:
            await websocket.close()  # Room full
            return

        print(f"[+] P{player_id + 1} connected")
        self.clients[player_id] = websocket

        try:
            # 1. Handshake
            await self.raw_send(player_id, player_id)
            await self.raw_send(player_id, {'decks': get_available_decks()})

            # 2. Lobby Selection
            await self.handle_lobby_selection(player_id)

            # Wait for both to be ready
            if player_id == 0:
                print("[*] P1 Ready, waiting for P2...")
                await self.connected_event.wait()
            else:
                print("[*] P2 Ready, starting game...")
                self.connected_event.set()

            # 3. Game Loop (Only ran by P1 task logically, or shared?)
            # Actually, with asyncio, we can run the game manager in a separate task
            # once both are ready.
            if player_id == 1:  # Trigger game start when P2 joins
                asyncio.create_task(self.game_man())

            # Keep connection alive while game_man runs elsewhere
            # We need to keep this handler open to receive messages?
            # Ideally, game_man handles recv via self.recv_from
            # So we just wait here until closed.
            await websocket.wait_closed()

        except Exception as e:
            print(f"[!] Error/Disconnect P{player_id + 1}: {e}")
        finally:
            self.clients[player_id] = None
            print(f"[-] P{player_id + 1} disconnected")

    async def raw_send(self, pid, data):
        ws = self.clients[pid]
        if not ws: raise ClientDisconnected(pid)
        try:
            await ws.send(pickle.dumps(data))
        except:
            raise ClientDisconnected(pid)

    async def recv_from(self, pid):
        ws = self.clients[pid]
        if not ws: raise ClientDisconnected(pid)
        try:
            data = await ws.recv()
            return pickle.loads(data)
        except:
            raise ClientDisconnected(pid)

    async def handle_lobby_selection(self, player_id):
        # Deck
        deck_id = None
        while deck_id is None:
            msg = await self.recv_from(player_id)
            d_id = msg.get('deck_id')
            if d_id not in get_available_decks():
                await self.raw_send(player_id, {"valid": False, "error": "Invalid Deck", "step": "deck"})
                continue
            valid, err = validate_deck(d_id)
            if not valid:
                await self.raw_send(player_id, {"valid": False, "error": err, "step": "deck"})
                continue
            deck_id = d_id
            await self.raw_send(player_id, {"valid": True, "step": "deck",
                                            "specializations": get_available_specializations(deck_id)})

        # Spec
        while True:
            msg = await self.recv_from(player_id)
            spec = msg.get('spec')
            name = msg.get('name', f"P{player_id + 1}")
            if spec not in get_available_specializations(deck_id):
                await self.raw_send(player_id, {"valid": False, "error": "Invalid Spec", "step": "spec"})
                continue

            self.player_data[player_id] = {'name': name, 'deck_id': deck_id, 'spec': spec}
            await self.raw_send(player_id, {"valid": True, "step": "complete"})

            # Wait for other player data
            other_id = 1 - player_id
            if not self.player_data[other_id]:
                await self.raw_send(player_id, {"status": "waiting"})
                while not self.player_data[other_id]:
                    await asyncio.sleep(0.1)

            await self.raw_send(player_id, {"status": "ready"})
            break

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

    async def game_man(self):
        from core.game import matchCreator

        print("[*] Initializing Match...")
        p1, p2 = self.player_data
        game = matchCreator(p1['name'], p1['deck_id'], p1['spec'], p2['name'], p2['deck_id'], p2['spec'])
        game.nextPhase()

        # Send initial state
        await self.broadcast_state(game)

        while True:
            try:
                from core.enums import Phases

                # Check winner
                if game.winner != Winner.NONE:
                    print(f"[*] WINNER: {game.winner.name}")
                    await self.broadcast_state(game)
                    break

                # Auto Phase
                if game.phase in [Phases.START, Phases.LOOT]:
                    await asyncio.sleep(0.5)
                    game.nextPhase()
                    await self.broadcast_state(game)
                    continue

                # Wait for Action
                active = game.isPlaying
                try:
                    # Async wait for input
                    action_dict = await asyncio.wait_for(self.recv_from(active), timeout=600)  # 10 min timeout
                except asyncio.TimeoutError:
                    print(f"[!] Timeout P{active}")
                    game.winner = Winner(1 - active + 1)
                    continue

                print(f"[*] P{active + 1} -> {action_dict['action'].name}")
                res = game.receiveAction(active, action_dict['action'], action_dict['args'])

                # Send result to active player
                await self.raw_send(active, res)

                # Broadcast updated state to both
                await self.broadcast_state(game)

            except ClientDisconnected as e:
                dropout = e.args[0]
                print(f"[!] P{dropout + 1} Left")
                game.winner = Winner(1 - dropout + 1)
                await self.broadcast_state(game)  # Notify remaining
                break
            except Exception as e:
                print(f"[!] Critical Game Error: {e}")
                import traceback
                traceback.print_exc()
                break

        print("[*] Match Ended.")
        # Optional: Close connections or reset

    async def broadcast_state(self, game):
        try:
            await self.raw_send(0, self.sanitize_state(game, 0))
        except:
            pass
        try:
            await self.raw_send(1, self.sanitize_state(game, 1))
        except:
            pass


if __name__ == "__main__":
    server = DustServer()
    asyncio.run(server.run())