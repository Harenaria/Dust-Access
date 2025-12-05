import threading

from client.client import GameClient
from client.webclient.style import *
from core.deck import get_deck_specializations


class LobbyView(ft.View):
    def __init__(self, page: ft.Page, client: GameClient):
        super().__init__()
        self.route = "/"
        self.page = page
        self.client = client
        self.page.title = "Dust Access // Login"
        self.bgcolor = COLOR_BACKGROUND
        self.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.decks_data = {}
        self.selected_deck_id = None
        self.selected_spec_name = None

        # --- UI Controls ---
        self.title_text = ft.Text("DUST ACCESS", size=40, weight=ft.FontWeight.BOLD, color=COLOR_ACCENT,
                                  font_family="Consolas")
        self.subtitle = ft.Text("System Link Initialization...", color=COLOR_TEXT_DIM)

        self.player_name_field = ft.TextField(
            label="Accessor ID (Name)", width=300,
            bgcolor=COLOR_SURFACE, border_color=COLOR_BORDER, color=COLOR_TEXT
        )
        self.connect_button = ft.ElevatedButton(
            "ESTABLISH CONNECTION", on_click=self.connect_click,
            bgcolor=COLOR_ACCENT, color="black", width=300, height=50
        )
        self.status_text = ft.Text("", color=COLOR_HP)

        self.deck_dropdown = ft.Dropdown(
            label="Select Loadout", width=300, visible=False,
            bgcolor=COLOR_SURFACE, border_color=COLOR_BORDER, color=COLOR_TEXT,
            on_change=self.deck_selected
        )
        self.spec_dropdown = ft.Dropdown(
            label="Select Specialization", width=300, visible=False,
            bgcolor=COLOR_SURFACE, border_color=COLOR_BORDER, color=COLOR_TEXT,
            on_change=self.spec_selected
        )
        self.ready_button = ft.ElevatedButton(
            "INITIATE SEQUENCE", on_click=self.ready_click, disabled=True, visible=False,
            bgcolor="#4caf50", color="white", width=300, height=50
        )

        self.container = ft.Container(
            padding=40,
            border=ft.border.all(1, COLOR_ACCENT),
            border_radius=10,
            # FIX: Use helper instead of ft.colors.with_opacity
            bgcolor=with_opacity(0.05, COLOR_ACCENT),
            content=ft.Column(
                [
                    self.title_text,
                    self.subtitle,
                    ft.Divider(color="transparent", height=20),
                    self.player_name_field,
                    self.connect_button,
                    self.status_text,
                    self.deck_dropdown,
                    self.spec_dropdown,
                    ft.Divider(color="transparent", height=20),
                    self.ready_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        self.controls = [
            ft.Row([self.container], alignment=ft.MainAxisAlignment.CENTER)
        ]

    def connect_click(self, e):
        if not self.player_name_field.value:
            self.status_text.value = "Identity required."
            self.page.update()
            return

        self.client.player_name = self.player_name_field.value
        self.status_text.value = "Connecting to Neural Network..."
        self.status_text.color = COLOR_ACCENT
        self.connect_button.disabled = True
        self.player_name_field.disabled = True
        self.page.update()
        threading.Thread(target=self.connect_and_wait, daemon=True).start()

    def connect_and_wait(self):
        if self.client.connect():
            self.client.my_id = self.client.wait_for_player_id()
            self.page.run_thread(self.update_status, "Connected. Waiting for peer link...", True)
            lobby_update = self.client.wait_for_lobby_response()
            if lobby_update:
                self.decks_data = lobby_update.get('decks', [])
                self.page.run_thread(self.display_decks)
            else:
                self.page.run_thread(self.update_status, "Data packet loss.", False)
        else:
            self.page.run_thread(self.update_status, "Connection failed. Server offline?", False)

    def display_decks(self):
        self.deck_dropdown.options.clear()
        if self.decks_data:
            for deck_id in self.decks_data:
                self.deck_dropdown.options.append(ft.dropdown.Option(key=str(deck_id), text=f"Loadout #{deck_id}"))
        else:
            self.deck_dropdown.options.append(ft.dropdown.Option(text="No data found", disabled=True))

        self.connect_button.visible = False
        self.deck_dropdown.visible = True
        self.page.update()

    def deck_selected(self, e):
        try:
            self.selected_deck_id = int(e.control.value) if e.control.value else None
        except:
            self.selected_deck_id = None

        self.selected_spec_name = None
        self.spec_dropdown.value = None
        self.spec_dropdown.visible = False
        self.ready_button.visible = False

        if self.selected_deck_id is not None:
            self.update_spec_list(self.selected_deck_id)
            self.spec_dropdown.visible = True
        self.page.update()

    def update_spec_list(self, deck_id):
        self.spec_dropdown.options.clear()
        specs = get_deck_specializations(deck_id)
        if specs:
            for spec_name in specs:
                self.spec_dropdown.options.append(ft.dropdown.Option(key=spec_name, text=spec_name))
        self.page.update()

    def spec_selected(self, e):
        self.selected_spec_name = e.control.value
        if self.selected_deck_id is not None and self.selected_spec_name:
            self.ready_button.visible = True
            self.ready_button.disabled = False
        self.page.update()

    def ready_click(self, e):
        self.ready_button.disabled = True
        self.deck_dropdown.disabled = True
        self.spec_dropdown.disabled = True
        self.status_text.value = "Sending configuration..."
        self.page.update()
        threading.Thread(target=self.send_selection_and_wait, daemon=True).start()

    def send_selection_and_wait(self):
        self.client.send_deck_selection(self.selected_deck_id)
        self.client.send_spec_selection(self.selected_spec_name, self.player_name_field.value)
        self.page.run_thread(self.update_status, "Configuration locked. Awaiting duel initialization...", True)

        while True:
            response = self.client.wait_for_lobby_response()
            if not response: break

            if response.get('status') == 'game_starting' or (
                    response.get('step') == 'complete' and response.get('valid')):
                self.page.go("/game")
                break
            elif response.get('valid') == False:
                self.page.run_thread(self.update_status, f"Error: {response.get('message')}", False)
                break

    def update_status(self, message, success=True):
        self.status_text.value = message
        self.status_text.color = COLOR_ACCENT if success else COLOR_HP
        self.page.update()