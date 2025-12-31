import flet as ft
from flet.core.alignment import Alignment
from flet.core.colors import Colors
from flet.core.container import Container
from flet.core.page import Page
from flet.core.types import FontWeight, MainAxisAlignment, CrossAxisAlignment, ScrollMode
from flet.core.view import View

from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.slots import SkillSlot, EquipSlot, WeaponGroup, StatTile, HandCard
from client_views.fletapp.locals.locale import Locale
from core.enums import CardType, Actions, Phases
from core.game import Game


class BoardView(View):
    def __init__(self,
                 page: Page,
                 localization: Locale,
                 room_code: str,
                 on_action,
                 initial_state: Game | None = None,
                 p_id: int = 0):
        super().__init__(route="/game")
        self._page = page
        self._page.bgcolor = AppTheme.COLOR_BG
        self._page.padding = 0
        self._localization = localization
        self._room_code = room_code
        self._game: Game | None = initial_state
        self._on_action_callback = on_action

        # Identifiers
        self._this_id = p_id
        self._opponent_id = 1 - p_id

        # Refs
        self._turn_text_ref = ft.Ref[ft.Text]()
        self._phase_text_ref = ft.Ref[ft.Text]()

        # Layout Containers
        self._opponent_board = ft.Column(spacing=10)
        self._player_board = ft.Column(spacing=10)
        self._hand_row = ft.Row(scroll=ScrollMode.HIDDEN, spacing=5)

        # Context Menu
        self._detail_sheet = ft.BottomSheet(
            content=Container(padding=20, bgcolor=AppTheme.GREY),
            dismissible=True
        )

        self._build_ui()

        if self._game:
            self.update_game(self._game)

    def _build_ui(self):
        # 1. Header
        header = Container(
            height=60,
            bgcolor=Colors.with_opacity(0.9, "#111111"),
            padding=ft.padding.symmetric(horizontal=20),
            content=ft.Row(
                alignment=MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(spacing=0, alignment=MainAxisAlignment.CENTER, controls=[
                        ft.Text("DUST ACCESS", size=10, weight=FontWeight.W_300,
                                color=Colors.with_opacity(0.7, AppTheme.COLOR_FG)),
                        ft.Text("MATCH IN PROGRESS", size=14, weight=FontWeight.BOLD, color=AppTheme.COLOR_FG)
                    ]),
                    ft.Column(spacing=0, alignment=MainAxisAlignment.CENTER,
                              horizontal_alignment=CrossAxisAlignment.END, controls=[
                            ft.Text("PHASE", size=10, weight=FontWeight.W_300, color=AppTheme.YELLOW),
                            ft.Text("LOADING", ref=self._phase_text_ref, size=14, weight=FontWeight.BOLD,
                                    color=AppTheme.COLOR_FG)
                        ])
                ]
            )
        )

        # 2. Board Area
        board_area = Container(
            expand=True,
            alignment=Alignment(0, 0),
            content=Container(
                padding=10,
                content=ft.Column(
                    scroll=ScrollMode.AUTO,
                    spacing=20,
                    controls=[
                        # Opponent
                        ft.Column(spacing=5, controls=[
                            ft.Text("OPPONENT", size=10, weight=FontWeight.BOLD,
                                    color=Colors.with_opacity(0.5, AppTheme.COLOR_FG)),
                            self._opponent_board
                        ]),

                        ft.Divider(color=Colors.with_opacity(0.1, AppTheme.COLOR_FG)),

                        # Player
                        ft.Column(spacing=5, controls=[
                            ft.Text("ACCESSOR (YOU)", size=10, weight=FontWeight.BOLD,
                                    color=Colors.with_opacity(0.5, AppTheme.COLOR_FG)),
                            self._player_board
                        ]),
                        Container(height=100)
                    ]
                )
            )
        )

        # 3. Action Bar / Hand
        footer = Container(
            bgcolor=Colors.with_opacity(0.95, "#000000"),
            border=ft.border.only(top=ft.border.BorderSide(1, AppTheme.GREY)),
            padding=10,
            content=self._hand_row
        )

        self.controls = [
            ft.Column(
                expand=True,
                spacing=0,
                controls=[header, board_area, footer]
            )
        ]

    def update_game(self, game: Game):
        self._game = game

        # Header Updates
        if self._phase_text_ref.current:
            self._phase_text_ref.current.value = f"{game.phase.name} - TURN {game.turn}"

        if len(self._game.players) > self._opponent_id:
            self._opponent_board.controls = [self._render_player_strip(self._opponent_id, is_me=False)]

        if len(self._game.players) > self._this_id:
            self._player_board.controls = [self._render_player_strip(self._this_id, is_me=True)]
            self._render_hand()

        self._page.update()

    def _render_player_strip(self, p_index: int, is_me: bool):
        if p_index >= len(self._game.players): return Container()
        p = self._game.players[p_index]

        # Status Row
        hp_percent = p.currentHP / p.currentDurability if p.currentDurability > 0 else 0

        status_row = ft.Row(
            alignment=MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                # Avatar
                ft.Row(controls=[
                    ft.CircleAvatar(
                        radius=24,
                        bgcolor=AppTheme.BLUE_3 if is_me else AppTheme.RED,
                        content=ft.Text(p.accessorName[:2], weight=FontWeight.BOLD, color=AppTheme.COLOR_FG)
                    ),
                    ft.Column(spacing=1, controls=[
                        ft.Text(p.accessorName, weight=FontWeight.BOLD, size=16),
                        ft.Stack([
                            Container(width=100, height=4, bgcolor=AppTheme.GREY),
                            Container(width=100 * hp_percent, height=4, bgcolor=AppTheme.GREEN_LIGHT),
                        ]),
                        ft.Text(f"{p.currentHP}/{p.currentDurability}", size=10,
                                color=Colors.with_opacity(0.6, AppTheme.COLOR_FG))
                    ])
                ]),
                # Stats
                ft.Row(spacing=2, controls=[
                    StatTile("PWR", p.currentPower, AppTheme.RED),
                    StatTile("TEN", p.currentTenacity, AppTheme.GREY),
                    StatTile("EFF", p.currentEfficiency, AppTheme.BLUE_2),
                    StatTile("SNS", p.currentSensitivity, AppTheme.PINK_DARK),
                ])
            ]
        )

        # Equipments
        # FIX: Explicitly pass in_hand=False to prevent KeyError on 'index' lookup
        weapon_row = WeaponGroup(
            p.equippedCards[CardType.WEAPON],
            p.equippedCards[CardType.OFF_HAND],
            lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None,
            lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None
        )

        armor_row = ft.Row(spacing=4, controls=[
            EquipSlot("HEAD", p.equippedCards[CardType.HEAD],
                      lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None),
            EquipSlot("BODY", p.equippedCards[CardType.CHEST],
                      lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None),
            EquipSlot("ARM", p.equippedCards[CardType.BRACERS],
                      lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None),
            EquipSlot("LEG", p.equippedCards[CardType.BOOTS],
                      lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None),
        ])

        # Skills
        skills_row = ft.Row(
            spacing=4,
            controls=[
                SkillSlot(i, s, lambda e: self._open_detail(e.control.data, in_hand=False, is_me=is_me) if is_me else None)
                for i, s in enumerate(p.skillSlots)
            ]
        )

        return ft.Column(
            spacing=10,
            controls=[status_row, weapon_row, armor_row, skills_row]
        )

    def _create_action_button(self, text: str, icon: str, color: str, action: Actions):
        """Helper to create standardized action buttons for the hand bar."""
        return Container(
            width=64, height=64,
            bgcolor=color,
            border=ft.border.all(2, AppTheme.COLOR_FG),
            on_click=lambda e: self._safe_action(action),
            content=ft.Column(alignment=MainAxisAlignment.CENTER, controls=[
                ft.Icon(icon, color=AppTheme.COLOR_FG),
                ft.Text(text, size=9, weight=FontWeight.BOLD)
            ])
        )

    def _render_hand(self):
        player = self._game.players[self._this_id]
        controls = []

        # --- ACTION BUTTON LOGIC ---
        if self._game.phase == Phases.SETUP:

            # Check if we are already ready (Server State)
            is_ready = False
            if hasattr(self._game, 'ready_in_setup') and len(self._game.ready_in_setup) > self._this_id:
                is_ready = self._game.ready_in_setup[self._this_id]

            if is_ready:
                # 1a. ALREADY CONFIRMED: Show Waiting State
                controls.append(
                    Container(
                        height=64, padding=10,
                        alignment=Alignment(0, 0),
                        content=ft.Text("WAITING...", size=10, weight=FontWeight.BOLD,
                                        color=Colors.with_opacity(0.5, AppTheme.COLOR_FG))
                    )
                )
            else:
                # 1b. NOT READY: Show Actions
                controls.append(
                    self._create_action_button("KEEP", ft.Icons.CHECK, AppTheme.GREEN_DARK, Actions.PASS_PHASE)
                )

                # Check if player has already used Mulligan
                has_used_mulligan = False
                if hasattr(self._game, 'hasMulligan') and len(self._game.hasMulligan) > self._this_id:
                    has_used_mulligan = self._game.hasMulligan[self._this_id]

                if not has_used_mulligan:
                    controls.append(
                        self._create_action_button("MULLIGAN", ft.Icons.REFRESH, AppTheme.YELLOW, Actions.MULLIGAN)
                    )

        else:
            # 2. NORMAL PHASE: Pass Turn
            controls.append(
                self._create_action_button("PASS", ft.Icons.SKIP_NEXT, AppTheme.RED_DARK, Actions.PASS_PHASE)
            )

        # --- RENDER CARDS ---
        for i, card in enumerate(player.hand):
            controls.append(
                HandCard(i, card, on_click=lambda e: self._open_detail(e.control.data, in_hand=True))
            )

        self._hand_row.controls = controls

    # --- Interaction Logic ---

    def _open_detail(self, data: dict, in_hand: bool = False, is_me: bool = True):
        if not data or not is_me: return
        card = data.get("card")
        if not card: return

        # Build Action Buttons
        actions = []

        if in_hand:
            # Context: Hand
            idx = data["index"]
            # We prevent actions during SETUP unless strictly needed, but viewing details is fine.
            # Actions.PLAY/EQUIP are generally blocked by server in Setup anyway.

            if self._game.phase != Phases.SETUP:
                if card.cardType in [CardType.WEAPON, CardType.DUAL, CardType.HEAD, CardType.CHEST, CardType.BRACERS,
                                     CardType.BOOTS, CardType.OFF_HAND]:
                    actions.append(self._btn("EQUIP", Actions.EQUIP, idx, AppTheme.BLUE_3))
                elif card.cardType in [CardType.SKILL, CardType.INSTANT, CardType.CANTRIP]:
                    actions.append(self._btn("PLAY", Actions.PLAY, idx, AppTheme.BLUE_3))

                actions.append(self._btn("DISCARD", Actions.DISCARD, idx, AppTheme.GREY))
        else:
            # Context: Field
            c_type = data.get("type")
            idx = data.get("index", 0)
            slot = data.get("slot", "")

            if c_type == "SKILL":
                actions.append(self._btn("ACTIVATE", Actions.ACTIVATE, idx, AppTheme.GREEN_DARK,
                                         extra={'source': 'SKILL', 'index': idx}))
            elif c_type == "EQUIP":
                actions.append(self._btn("USE EFFECT", Actions.ACTIVATE, 0, AppTheme.PURPLE,
                                         extra={'source': 'EQUIP', 'slot': slot}))
            elif c_type == "WEAPON":
                actions.append(self._btn("ATTACK", Actions.ATTACK, 0, AppTheme.RED, extra={'source': 'WEAPON'}))

        # Bottom Sheet Content
        content = ft.Container(
            height=400,
            padding=10,
            content=ft.Column(
                controls=[
                    ft.Row(alignment=MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text(card.name, size=24, weight=FontWeight.W_200),
                        Container(padding=5, bgcolor=AppTheme.BLUE_1,
                                  content=ft.Text(f"LVL {card.level}", weight=FontWeight.BOLD, size=12))
                    ]),
                    ft.Divider(),
                    ft.Container(expand=True, content=ft.Column(scroll=ScrollMode.AUTO, controls=[
                        ft.Text(card.Text, size=16),
                        ft.Text(f"\n{card.Flavor}", size=12, italic=True,
                                color=Colors.with_opacity(0.6, AppTheme.COLOR_FG))
                    ])),
                    ft.Divider(),
                    ft.Row(alignment=MainAxisAlignment.END, spacing=10, controls=actions)
                ]
            )
        )

        self._detail_sheet.content = content
        self._page.open(self._detail_sheet)
        self._page.update()

    def _btn(self, text, action, index, color, extra=None):
        return ft.ElevatedButton(
            text=text,
            bgcolor=color,
            color=AppTheme.COLOR_FG,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0)),
            on_click=lambda e: self._safe_action(action, index, extra, close_sheet=True)
        )

    def _safe_action(self, action: Actions, index: int = 0, extra: dict = None, close_sheet: bool = False):
        if close_sheet:
            self._page.close(self._detail_sheet)

        payload = {"index": index}
        if extra: payload.update(extra)

        if self._on_action_callback:
            # Flet's native way to fire-and-forget an async callback from a UI event
            self._page.run_task(self._on_action_callback, action, payload)
        else:
            print(f"[UI DEBUG] Action: {action} | Payload: {payload} (No Callback Linked)")