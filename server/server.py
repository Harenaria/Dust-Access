import asyncio
import pickle
import os
import logging
import pandas as pd
from aiohttp import web, WSMsgType
from core.deck import validate_deck, get_deck_specializations
from core.enums import Winner, Phases

# --- CONFIGURAZIONE LOGGING ---
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
    """Eccezione custom per gestire la disconnessione pulita"""
    pass


class GameServer:
    def __init__(self):
        self.clients = [None, None]  # Slot P1 e P2 (WebSocketResponse)
        self.player_data = [None, None]  # Dati Lobby
        self.connected_event = asyncio.Event()  # Segnale "Tutti Pronti"
        self.game_task = None  # Riferimento al task della partita

    async def health_check(self, request):
        """Risponde al ping di Render/Uptime robot"""
        return web.Response(text="Dust Access Server: Online", status=200)

    async def websocket_handler(self, request):
        """Gestisce l'upgrade e il ciclo di vita della connessione WebSocket"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Assegnazione Slot (0 o 1)
        if self.clients[0] is None:
            pid = 0
        elif self.clients[1] is None:
            pid = 1
        else:
            await ws.close(code=4000, message=b"Room Full")
            return ws

        self.clients[pid] = ws
        logger.info(f"Player {pid + 1} connected from {request.remote}")

        try:
            # 1. Handshake & Lobby
            await self.run_lobby_phase(pid)

            # 2. Sincronizzazione
            if pid == 0:
                logger.info("P1 Waiting for P2...")
                await self.connected_event.wait()
            else:
                logger.info("P2 Joined. Starting Game...")
                self.connected_event.set()

            # 3. Avvio Logica di Gioco (Singleton)
            if pid == 1:
                # Avvia il manager in background
                self.game_task = asyncio.create_task(self.game_manager())

            # 4. Keep-Alive Loop
            # In aiohttp, il handler deve rimanere vivo finché la connessione è aperta.
            # I messaggi di gioco vengono letti "a richiesta" dentro game_manager tramite self.recv_from,
            # ma qui dobbiamo gestire il ciclo principale di lettura per non chiudere il socket.
            # Tuttavia, poiché game_manager è un task separato che chiama recv_from,
            # dobbiamo evitare che questo loop "rubi" i messaggi.
            # TRUCCO: In questa architettura semplice, game_manager consumerà i messaggi.
            #         Qui ci mettiamo solo in attesa della chiusura.

            # Attendiamo che il socket si chiuda
            await ws.wait_closed()

        except ClientDisconnected:
            logger.warning(f"Player {pid + 1} disconnected cleanly during setup.")
        except Exception as e:
            logger.error(f"Unexpected error for P{pid + 1}: {e}", exc_info=True)
        finally:
            logger.info(f"Player {pid + 1} session ended.")
            self.clients[pid] = None
            # Se un giocatore esce, la partita è compromessa.
            # In un server reale resetteremmo la stanza, qui lasciamo terminare il processo.
            if self.game_task: self.game_task.cancel()

        return ws

    # --- COMUNICAZIONE ---

    async def raw_send(self, pid, data):
        """Invia dati serializzati al client specificato"""
        ws = self.clients[pid]
        if ws is None or ws.closed:
            raise ClientDisconnected(pid)
        try:
            await ws.send_bytes(pickle.dumps(data))
        except Exception:
            raise ClientDisconnected(pid)

    async def recv_from(self, pid):
        """
        Legge il prossimo messaggio dal client specifico.
        Questa funzione è chiamata dal Game Manager.
        """
        ws = self.clients[pid]
        if ws is None or ws.closed:
            raise ClientDisconnected(pid)

        try:
            # receive() restituisce il prossimo messaggio dalla coda interna di aiohttp
            msg = await ws.receive()

            if msg.type == WSMsgType.BINARY:
                return pickle.loads(msg.data)
            elif msg.type == WSMsgType.CLOSE:
                raise ClientDisconnected(pid)
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WS Error P{pid + 1}: {ws.exception()}")
                raise ClientDisconnected(pid)
            else:
                return None  # Ignora ping/pong o text frame non previsti
        except Exception:
            raise ClientDisconnected(pid)

    # --- LOGICA LOBBY ---

    async def run_lobby_phase(self, pid):
        # Send ID & Decks
        await self.raw_send(pid, pid)
        await self.raw_send(pid, {'decks': get_available_decks()})

        # Deck Selection Loop
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

        # Spec Selection Loop
        while True:
            msg = await self.recv_from(pid)
            spec = msg.get('spec')
            name = msg.get('name', f"Player {pid + 1}")

            if spec not in get_available_specializations(deck_id):
                await self.raw_send(pid, {"valid": False, "error": "Invalid Spec", "step": "spec"})
                continue

            self.player_data[pid] = {'name': name, 'deck_id': deck_id, 'spec': spec}
            await self.raw_send(pid, {"valid": True, "step": "complete"})

            # Sync Wait for Opponent
            other_pid = 1 - pid
            if self.player_data[other_pid] is None:
                await self.raw_send(pid, {"status": "waiting"})
                while self.player_data[other_pid] is None:
                    await asyncio.sleep(0.2)

            await self.raw_send(pid, {"status": "ready"})
            break

    # --- LOGICA PARTITA ---

    async def broadcast_state(self, game):
        """Invia lo stato sanificato a entrambi i giocatori"""
        for i in [0, 1]:
            try:
                state = self.sanitize_state(game, i)
                await self.raw_send(i, state)
            except ClientDisconnected:
                pass  # Gestito dal loop principale

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

        logger.info("Initializing Game Engine...")
        p1, p2 = self.player_data
        game = matchCreator(p1['name'], p1['deck_id'], p1['spec'], p2['name'], p2['deck_id'], p2['spec'])

        # Start
        game.nextPhase()
        await self.broadcast_state(game)

        while True:
            try:
                # 1. Check Win Condition
                if game.winner != Winner.NONE:
                    logger.info(f"GAME OVER. Winner: {game.winner.name}")
                    await self.broadcast_state(game)
                    break

                # 2. Auto Phases (Start/Loot)
                if game.phase in [Phases.START, Phases.LOOT]:
                    await asyncio.sleep(0.5)  # Ritardo estetico
                    game.nextPhase()
                    await self.broadcast_state(game)
                    continue

                # 3. Wait for Input
                active_pid = game.isPlaying

                # Timeout di sicurezza (10 min) per non bloccare risorse zombie
                try:
                    action_data = await asyncio.wait_for(self.recv_from(active_pid), timeout=600.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout for Player {active_pid + 1}")
                    game.winner = Winner(1 - active_pid + 1)
                    continue

                # 4. Process Action
                logger.info(f"Action from P{active_pid + 1}: {action_data['action'].name}")
                result = game.receiveAction(active_pid, action_data['action'], action_data['args'])

                # 5. Feedback
                await self.raw_send(active_pid, result)
                await self.broadcast_state(game)

            except ClientDisconnected as e:
                # Vittoria a tavolino
                loser = e.args[0]
                logger.info(f"Player {loser + 1} surrendered (disconnected).")
                game.winner = Winner(1 - loser + 1)
                await self.broadcast_state(game)
                break
            except Exception as e:
                logger.critical(f"Game Logic Crash: {e}", exc_info=True)
                break

        logger.info("Match finished.")


# --- ENTRY POINT ---

async def init_app():
    server = GameServer()
    app = web.Application()

    # Rotte
    app.router.add_get('/', server.health_check)  # HTTP
    app.router.add_get('/ws', server.websocket_handler)  # WebSocket

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Aiohttp entry point
    web.run_app(init_app(), port=port)