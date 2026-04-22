from flet.core import alignment, border
from flet.core.bottom_sheet import BottomSheet
from flet.core.colors import Colors
from flet.core.column import Column
from flet.core.container import Container
from flet.core.control import Control
from flet.core.padding import Padding
from flet.core.page import Page
from flet.core.ref import Ref
from flet.core.row import Row
from flet.core.stack import Stack
from flet.core.text import Text
from flet.core.text_style import TextStyle
from flet.core.types import ScrollMode, MainAxisAlignment, FontWeight, CrossAxisAlignment
from flet.core.view import View

from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.action_buttons import MulliganButton, KeepButton, PlaceButton, PassButton, \
    EquipButton, ActivateButton, AttackButton, DiscardButton, CantripButton, ShowHandButton
from client_views.fletapp.components.action_indicators import ActionIndicators
from client_views.fletapp.components.choice_modal import ChoiceModal
from client_views.fletapp.components.game_overlays import LogTicker, DamageSplashes, ActionAnnouncementOverlay
from client_views.fletapp.components.game_sheets import HandSheet, DetailSheet, LogSheet, DeckSelectionSheet
from client_views.fletapp.components.game_tiles import StatTile, WeaponGroup, SkillSlot, CardTile, EquipSlot
from client_views.fletapp.components.effect_badges import EffectRow
from client_views.fletapp.locals.locale import Locale
from core.enums import Stats, CardType, Phases, Actions, Winner
from core.game import Game
from core.deck import get_cards_db


class BoardView(View):
    def __init__(self,
                 page: Page,
                 localization: Locale,
                 room_code: str,
                 on_action,
                 on_rematch = None,
                 on_leave = None,
                 initial_state: Game | None = None,
                 p_id: int = 0):
        super().__init__(route="/game")
        self._page = page
        self.bgcolor = AppTheme.COLOR_BG
        self._page.padding = 0
        self._localization = localization
        self._room_code = room_code
        self._game: Game | None = initial_state
        self._on_action_callback = on_action
        self._on_rematch_callback = on_rematch
        self._on_leave_callback = on_leave
        # Identifiers
        self._this_id = p_id
        self._opponent_id = 1 - p_id
        
        # State
        self._current_action: Actions | None = None
        self._waiting_for_opp: bool = False
        self._last_hp = [0, 0]
        
        # Refs
        self._turn_text_ref = Ref[Text]()
        self._phase_text_ref = Ref[Text]()
        self._action_indicators: list[ActionIndicators | None] = [None, None] # For P1 and P2
        self._effect_rows: list[EffectRow | None] = [None, None]
        self._selected_counter: str | None = None

        # Boards
        self._opponent_board = Column(
            expand=True,
            horizontal_alignment= CrossAxisAlignment.CENTER,
            spacing=10
        )

        self._player_board = Column(
            expand=True,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=10,
            alignment=MainAxisAlignment.END # Align player board to bottom of its area
        )

        # Hand & Sheets
        self._hand_row_overlay = Row(scroll=ScrollMode.AUTO, spacing=5, alignment=MainAxisAlignment.CENTER) # For Mulligan Overlay
        
        self._hand_sheet = HandSheet(self._handle_hand_card_click)
        self._hand_sheet.on_dismiss = self._on_hand_dismiss
        
        self._detail_sheet = DetailSheet()
        self._log_history_sheet = LogSheet([])
        self._selection_sheet = DeckSelectionSheet(self._handle_selection_card_click)

        # Overlays & Feedback (from components)
        self._damage_splashes = DamageSplashes()
        self._log_ticker_comp = LogTicker(on_click=self._open_history)
        self._announcement_overlay = ActionAnnouncementOverlay(
            on_rematch=self._on_rematch_callback,
            on_leave=self._on_leave_callback
        )

        # Mulligan Overlay
        from flet.core.colors import Colors
        self._mulligan_overlay = Container(
            visible=False,
            expand=True,
            bgcolor=Colors.with_opacity(0.85, AppTheme.COLOR_BG),
            padding=20,
            alignment=alignment.center,
            content=self._hand_row_overlay
        )

        from flet.core.padding import Padding
        # Command Bar
        self._commands = Row(spacing=10)
        self._command_bar = Container(
            height=72,
            bgcolor=AppTheme.GREY,
            padding=Padding(15, 0, 15, 0),
            content=Row(
                alignment=MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=CrossAxisAlignment.CENTER,
                controls=[
                    Column(
                        spacing=0,
                        alignment=MainAxisAlignment.CENTER,
                        controls=[
                            Text("TURN 1", ref=self._turn_text_ref, font_family='Noto Sans', weight=FontWeight.W_600, color=AppTheme.COLOR_FG, size=10, style=TextStyle(letter_spacing=-1)),
                            Text("loading...", ref=self._phase_text_ref, font_family='Noto Sans', weight=FontWeight.W_200, size=24, style=TextStyle(letter_spacing=-1)),
                        ]
                    ),
                    self._commands
                ]
            )
        )

        if self._game:
            self.update_game(self._game)

        self.expand = True
        self.alignment = MainAxisAlignment.START
        
        # Main Layout: Stack for Board/Overlay + Command Bar
        main_content_area = Stack(
            expand=True,
            controls=[
                # Layer 0: Boards
                Column(
                    expand=True,
                    alignment=MainAxisAlignment.SPACE_BETWEEN, # Separate Opponent (Top) and Player (Bottom)
                    controls=[
                        Container(padding=10, content=self._opponent_board, expand=True), # Ensure container stretches
                        Container(padding=10, content=self._player_board, expand=True)
                    ]
                ),
                # Layer 1: Overlay
                self._mulligan_overlay,
                # Layer 2: Damage Splashes
                self._damage_splashes,
                # Layer 3: Announcements
                self._announcement_overlay
            ]
        )
        
        # Root Column to force full expansion structure
        root_layout = Column(
            expand=True,
            spacing=0,
            controls=[
                main_content_area,
                Container(padding=Padding(15, 0, 15, 10), content=self._log_ticker_comp),
                self._command_bar
            ]
        )
        
        self.controls = [root_layout]
        
    def _on_hand_dismiss(self, e):
        # Reset selection mode on dismiss if it was a HAND selection
        if self._current_action in [Actions.EQUIP, Actions.LEARN, Actions.CAST, Actions.DISCARD, Actions.ACTIVATE]:
            self._current_action = None
            self._selected_counter = None
            self.update_game(self._game) # Redraw/Revert title

    def build_player_board(self, p_index: int):
        if p_index >= len(self._game.players): return Container()
        p = self._game.players[p_index]
        is_me = (p_index == self._this_id)

        # Initialize Action Indicators if not exists
        if not self._action_indicators[p_index]:
            self._action_indicators[p_index] = ActionIndicators(p.hasTacticalAction, p.hasCombatAction)
        
        stat_col = Column(
            spacing=10,
            controls= [
                StatTile(Stats.POWER, p.currentPower),
                StatTile(Stats.EFFICIENCY, p.currentEfficiency),
                StatTile(Stats.TENACITY, p.currentTenacity),
                StatTile(Stats.SENSITIVITY, p.currentSensitivity)
            ]
        )
        # Initialize Effect Row if not exists
        self._init_effect_row(p_index, p)

        info_row = Column(
            spacing=0,
            controls=[
                Row(
                    spacing=10,
                    vertical_alignment=CrossAxisAlignment.CENTER,
                    controls=[
                        Text(p.accessorName, font_family='Noto Sans', color=AppTheme.COLOR_FG, size=24,
                             weight=FontWeight.W_400),
                        self._action_indicators[p_index] if self._action_indicators[p_index] else Container()
                    ]
                ),
                Row(
                    spacing=10,
                    vertical_alignment=CrossAxisAlignment.END,
                    controls=[
                        Text(f"lvl {p.level}", font_family='Noto Sans', color=AppTheme.COLOR_FG, size=16,
                             weight=FontWeight.W_200, style=TextStyle(letter_spacing=-1)),
                        Text(p.specialization.name.lower(), font_family='Noto Sans', color=AppTheme.COLOR_FG, size=16,
                             weight=FontWeight.W_200, style=TextStyle(letter_spacing=-1)),
                        Row(
                            spacing=2,
                            vertical_alignment=CrossAxisAlignment.END,
                            controls=[
                                Text(f"HP {p.currentHP}", font_family='Noto Sans', color=AppTheme.COLOR_FG, size=16,
                                     weight=FontWeight.W_200, style=TextStyle(letter_spacing=-1)),
                                Text(f"/{p.currentDurability}", font_family='Noto Sans', color=AppTheme.COLOR_FG,
                                     size=10, weight=FontWeight.W_600)
                            ],
                        ),
                    ]
                ),
                # Status Effects & Counters Row
                self._effect_rows[p_index] if self._effect_rows[p_index] else Container()
            ]
        )
        
        # Callbacks for Board Items
        def _on_w_click(e): self._handle_board_click(e.control.data, is_me)
        def _on_s_click(e): self._handle_board_click(e.control.data, is_me)
        
        weapon_row = WeaponGroup(
            p.equippedCards[CardType.WEAPON],
            p.equippedCards[CardType.OFF_HAND],
            _on_w_click, _on_w_click
        )

        # Armor
        def _on_a_click(e): self._handle_board_click(e.control.data, is_me)
        
        armor_row = Row(
            spacing=4, 
            controls=[
                EquipSlot(CardType.HEAD, p.equippedCards[CardType.HEAD], _on_a_click),
                EquipSlot(CardType.CHEST, p.equippedCards[CardType.CHEST], _on_a_click),
                EquipSlot(CardType.BRACERS, p.equippedCards[CardType.BRACERS], _on_a_click),
                EquipSlot(CardType.BOOTS, p.equippedCards[CardType.BOOTS], _on_a_click),
            ]
        )

        # Skills
        skills_row = Row(
            spacing=4,
            controls=[
                SkillSlot(i, s, _on_s_click)
                for i, s in enumerate(p.skillSlots)
            ]
        )

        return Row(
            expand=True,
            alignment=MainAxisAlignment.CENTER,
            controls=[
                #TODO: Avatar
                Column(
                    spacing=10,
                    controls=[info_row, weapon_row, armor_row, skills_row]
                ),
                stat_col
            ]
        )
        
    def _init_effect_row(self, p_index: int, p):
        if not self._effect_rows[p_index]:
            self._effect_rows[p_index] = EffectRow(p.statuses, p.counters, self._handle_badge_click)
        return self._effect_rows[p_index]

    def _handle_badge_click(self, e):
        data = e.control.data
        if not data: return
        name = data.get("name")
        is_activable = data.get("is_activable")

        # If Activation Mode
        if self._current_action == Actions.ACTIVATE:
            if is_activable:
                self._selected_counter = name
                self._page.snack_bar = BottomSheet(content=Container(padding=10, content=Text(f"Select a Skill to use {name} on")))
                self._page.snack_bar.open = True
                self._page.update()
                return

        # Default: Inspection (DetailSheet)
        # Search for a card with this name in the DB
        cards_db = get_cards_db()
        if name in cards_db.index:
            card_data = cards_db.loc[name].to_dict()
            from core.deck import Deck
            card_obj = Deck._create_card_instance(name, card_data)
            self._open_detail({"card": card_obj})
        else:
             # Fallback if not found in CSV yet
             from core.card import Card
             from core.enums import CardType, AccessorClass
             dummy = Card(name=name, Text="Effect active.", Flavor="Detailed info not found in Cards.csv.", cardType=CardType.COUNTER, acClass=AccessorClass.HEAVY)
             self._open_detail({"card": dummy})

    def _handle_board_click(self, data, is_me):
        if not data: return
        
        # If Pending Activate Selection
        if self._current_action == Actions.ACTIVATE and is_me:
             # Check if skill or equip
             c_type = data.get("type", "")
             card = data.get("card")
             
             if not card: return

             if c_type == "SKILL":
                 idx = data.get("index") # SkillSlot returns index
                 
                 if self._selected_counter:
                     # Counter Activation
                     self._page.run_task(self._on_action_callback, Actions.ACTIVATE, {
                         'source': 'COUNTER',
                         'counter': self._selected_counter,
                         'index': idx
                     })
                     self._selected_counter = None
                     self.update_game(self._game)
                     return

                 self._execute_with_choice(card, Actions.ACTIVATE, {'source': 'SKILL', 'index': idx})
                 return
             elif c_type in ["WEAPON", "OFFHAND", "EQUIP"]:
                 # Determine slot from tile type
                 if c_type == "WEAPON":
                     slot = CardType.WEAPON
                 elif c_type == "OFFHAND":
                     slot = CardType.OFF_HAND
                 else:
                     slot = data.get("slot") # EquipSlot passes the CardType slot
                 
                 if not slot: return
                 
                 # Send generic Activate on slot
                 self._execute_with_choice(card, Actions.ACTIVATE, {'source': 'EQUIP', 'slot': slot})
                 return

        # Default: Show Detail
        self._open_detail(data)

    def _open_detail(self, data: dict):
        if not data: return
        card = data.get("card")
        if not card: return

        self._detail_sheet.show_card(card)
        self._page.open(self._detail_sheet)
        self._page.update()

    def _open_history(self, e):
        if not self._game: return
        self._log_history_sheet.update_logs([entry.message for entry in self._game.logs.entries])
        self._page.open(self._log_history_sheet)
        self._page.update()

    def _open_selection_sheet(self, title: str, candidates: list):
        self._selection_sheet.update_selection(title, candidates)
        self._page.open(self._selection_sheet)
        self._page.update()

    def _handle_selection_card_click(self, e):
        data = e.control.data
        if not data: return
        card = data.get("card")
        # In this context, we just need the card object or its identifier to the server
        # For simplicity, we assume the server expects the name or index
        # We'll use CHOOSE_REWARD action
        self._page.run_task(self._on_action_callback, Actions.CHOOSE_REWARD, {'card_name': card.name})
        self._page.close(self._selection_sheet)
        self._page.update()

    def _command_helper(self, e):
        action = e.control.data
        if not action: return
        
        if action in [Actions.EQUIP, Actions.LEARN, Actions.CAST]:
            self._current_action = action
            self._open_hand_sheet(None) # Re-open/Refresh hand
        elif action == Actions.DISCARD:
            self._current_action = Actions.DISCARD
            self._open_hand_sheet(None)
        elif action == Actions.ACTIVATE:
            self._current_action = Actions.ACTIVATE
            self._page.snack_bar = BottomSheet(content=Container(padding=10, content=Text("Select a card on board to activate")))
            self._page.snack_bar.open = True
            self._page.update()
        elif action == Actions.PASS_PHASE:
            if self._game.phase == Phases.SETUP:
                self._waiting_for_opp = True # Lock locally
            self._page.run_task(self._on_action_callback, action, {})
        else:
             # Attack, Mulligan, etc
             self._page.run_task(self._on_action_callback, action, {})
            
    def _open_hand_sheet(self, e):
        self._update_hand_ui() # Refilter
        self._page.open(self._hand_sheet)
        self._page.update()
        
    def _handle_hand_card_click(self, e):
        data = e.control.data 
        if not data: return
        card = data.get("card")
        
        if self._current_action:
            # Execute Action with this card
            idx = self._game.players[self._this_id].hand.index(card) # Find index carefully?
            # Prefer passing index in data if possible, but card obj is unreliable for index?
            # Re-find index
            try:
                real_idx = self._game.players[self._this_id].hand.index(card)
            except ValueError:
                return # Error
            
            self._execute_with_choice(card, self._current_action, {'index': real_idx})
            
            # Close sheet
            self._page.close(self._hand_sheet)
            self._current_action = None
            self.update_game(self._game)
        else:
            self._open_detail(data)

    def _execute_with_choice(self, card, action, payload):
        
        choices = []
        if action in [Actions.LEARN, Actions.CAST] and hasattr(card, 'OnPlay') and getattr(card, 'ChoiceLabels', None):
             if len(card.OnPlay) > 1: choices = card.ChoiceLabels
        elif action == Actions.ACTIVATE and hasattr(card, 'OnActivate') and getattr(card, 'ChoiceLabels', None):
             if len(card.OnActivate) > 1: choices = card.ChoiceLabels
        
        if choices:
            def _dismiss(e):
                self._page.overlay.remove(dlg)
                self._page.update()

            def _on_choice(i):
                payload['choice'] = i
                _dismiss(None)
                self._page.run_task(self._on_action_callback, action, payload)
                # Action consumed
                self._current_action = None
                self.update_game(self._game)
            
            dlg = ChoiceModal(f"Choose option for {card.name}", choices, _on_choice, _dismiss)
            self._page.overlay.append(dlg)
            self._page.update()
        else:
            self._page.run_task(self._on_action_callback, action, payload)
            self._current_action = None
            self.update_game(self._game)

    def _update_hand_ui(self):
        if not self._game: return
        my_player = self._game.players[self._this_id]
        hand_cards = my_player.hand
        
        # Title logic
        title = "hand"
        candidates = hand_cards # Default all
        
        if self._current_action == Actions.EQUIP:
            title = "select a card to equip"
            candidates = [c for c in hand_cards if c.cardType in [CardType.WEAPON, CardType.DUAL, CardType.OFF_HAND,
                                                                 CardType.HEAD, CardType.CHEST, CardType.BRACERS, CardType.BOOTS]]
        elif self._current_action == Actions.LEARN:
             title = "select a card to learn"
             candidates = [c for c in hand_cards if c.cardType in [CardType.SKILL, CardType.INSTANT, CardType.ADVANCED]]
        elif self._current_action == Actions.CAST:
             title = "select a card to cast"
             candidates = [c for c in hand_cards if c.cardType == CardType.CANTRIP]
        elif self._current_action == Actions.DISCARD:
            title = "select a card to discard"
            # All cards valid
            
        self._hand_sheet.update_hand(title, candidates)
        
    def update_game(self, game: Game):
        self._game = game
        self._waiting_for_opp = False # Reset on update (server state dictates)
        
        if self._turn_text_ref.current:
            self._turn_text_ref.current.value = f"TURN {game.turn}"
        if self._phase_text_ref.current:
            self._phase_text_ref.current.value = f"{game.phase.name.lower()}"
        
        # Detect New Logs for Announcements
        if game.logs.entries:
            last_entry = game.logs.entries[-1]
            last_log = last_entry.message
            self._log_ticker_comp.update_log(last_log)
            upper_log = last_log.upper()
            if any(kw in upper_log for kw in ["REVEALS", "SEARCHES", "LEVEL UP", "LEARNS"]):
                    self._page.run_task(self._announcement_overlay.announce, last_log)
        
        # Update Boards
        self._player_board.controls = [self.build_player_board(self._this_id)]
        self._opponent_board.controls = [self.build_player_board(self._opponent_id)]
        
        # Update Action Indicators
        for i in range(2):
            if self._action_indicators[i]:
                self._action_indicators[i].update_actions(
                    game.players[i].hasTacticalAction,
                    game.players[i].hasCombatAction
                )
            if self._effect_rows[i]:
                self._effect_rows[i].update_effects(
                    game.players[i].statuses,
                    game.players[i].counters
                )
        
        # Update Overlay (Mulligan)
        my_player = game.players[self._this_id]
        overlay_tiles = [CardTile(c, lambda e: self._open_detail(e.control.data)) for c in my_player.hand]
        self._hand_row_overlay.controls = overlay_tiles
        self._mulligan_overlay.visible = (game.phase == Phases.SETUP)
        
        # Detect Damage for Splashes
        for i in range(2):
            new_hp = game.players[i].currentHP
            if self._last_hp[i] > new_hp:
                amount = self._last_hp[i] - new_hp
                is_opponent = (i == self._opponent_id)
                self._page.run_task(self._damage_splashes.show_splash, amount, is_opponent, self._page.width)
            self._last_hp[i] = new_hp

        # Update Hand Sheet
        self._update_hand_ui()
        
        # Commands Logic
        cmds: list[Control] = [ShowHandButton(self._open_hand_sheet)]
        
        is_my_turn = (self._this_id == game.isPlaying)
        is_setup = (game.phase == Phases.SETUP)
        pending_discard = (my_player.pending_discard > 0)
        
        # Check Winner
        if game.winner != Winner.NONE:
            self._handle_game_over(game.winner)
            self._commands.controls = cmds
            self._page.update()
            return

        if not is_my_turn and not is_setup:
             cmds = [Text("waiting...", font_family='Noto Sans', weight=FontWeight.W_400)]
        elif pending_discard:
             cmds = [ShowHandButton(self._open_hand_sheet), DiscardButton(self._command_helper)]
        else:
            match game.phase:
                case Phases.SETUP:
                    if game.ready_in_setup[self._this_id]:
                        cmds = [Text("waiting...", font_family='Noto Sans', weight=FontWeight.W_400)]
                    else:
                        cmds = [MulliganButton(self._command_helper), KeepButton(self._command_helper)]
                case Phases.PREPARATION:
                    cmds.extend([PlaceButton(self._command_helper), PassButton(self._command_helper)])
                case Phases.DUEL:
                    cmds.extend([EquipButton(self._command_helper), CantripButton(self._command_helper), ActivateButton(self._command_helper), AttackButton(self._command_helper), PassButton(self._command_helper)])
                case Phases.END:
                    if len(my_player.hand) > 5: cmds.append(DiscardButton(self._command_helper))
                    else: cmds.append(PassButton(self._command_helper))
        
        # Choice Pending UI (Spec effects)
        if game.players[self._this_id].choice_pending:
             if hasattr(game.players[self._this_id], 'choice_candidates') and game.players[self._this_id].choice_candidates:
                  self._open_selection_sheet("select your reward", game.players[self._this_id].choice_candidates)

        self._commands.controls = cmds
        self._page.update()

    def _handle_game_over(self, winner):
        msg = "draw"
        if winner == Winner.PLAYER1:
            msg = "victory" if self._this_id == 0 else "defeat"
        elif winner == Winner.PLAYER2:
            msg = "victory" if self._this_id == 1 else "defeat"
            
        self._page.run_task(self._announcement_overlay.announce, msg, True)
