import flet as ft
import os
import logging

# ... (I tuoi import: LobbyView, GameView, GameClient) ...
from client.webclient.lobby_view import LobbyView
from client.webclient.game_view import GameView
from client.client import GameClient

# Configurazione Log per vedere cosa succede su Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FletApp")


def main(page: ft.Page):
    page.title = "Dust Access Simulator"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # Inizializza il client
    client = GameClient()

    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(LobbyView(page, client))
        elif page.route == "/game":
            page.views.append(GameView(page, client))
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/")


def client_runner():
    # --- CONFIGURAZIONE DI RETE CRITICA PER RENDER ---

    # 1. Recupera la PORTA fornita da Render (default 8080 per locale)
    server_port = int(os.environ.get("PORT", 8080))

    # 2. Imposta l'HOST.
    # SU RENDER DEVE ESSERE "0.0.0.0".
    # In locale va bene anche "127.0.0.1".
    server_host = "0.0.0.0"

    logger.info(f"Avvio Flet Web App su {server_host}:{server_port}")

    # 3. Avvia Flet
    ft.app(
        target=main,
        view=ft.WEB_BROWSER,  # Fondamentale per la modalità web
        port=server_port,
        host=server_host
    )


if __name__ == "__main__":
    client_runner()