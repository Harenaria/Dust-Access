import flet as ft
import os
from client.webclient.lobby_view import LobbyView
from client.webclient.game_view import GameView
from client.client import GameClient

def main(page: ft.Page):
    page.title = "Dust Access Simulator"
    page.theme_mode = ft.ThemeMode.DARK # Forza dark mode
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
    port = int(os.environ.get("PORT", 8550))

    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"

    print(f"Avvio Flet Client su http://{host}:{port}")
    ft.app(target=main, view=ft.WEB_BROWSER, port=port, host=host)


if __name__ == "__main__":
    client_runner()