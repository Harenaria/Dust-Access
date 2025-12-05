import flet as ft
import threading
import time
import traceback

from flet.core.types import TextAlign, FontWeight

from client.webclient.components.player_view import PlayerDashboard, PaperDoll
from client.webclient.components.card_view import CardView
from client.webclient.style import *
from core.enums import Actions, Phases, CardType, Winner


class GameView(ft.View):
    def __init__(self, page: ft.Page, client):
        super().__init__()
        self.route = "/game"
        self.page = page
        self.client = client
        self.game_state = None
        self.bgcolor = COLOR_BACKGROUND
        self.padding = 0

        # --- STATE ---
        self.selection = None

        # --- LEFT PANEL: LOGS ---
        self.log_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        self.log_panel = ft.Container(
            content=self.log_list, width=220, bgcolor="#080808",
            border=ft.border.only(right=ft.border.BorderSide(1, COLOR_BORDER)), padding=10
        )

        # --- RIGHT PANEL: INSPECTOR & CONTROLS ---

        # Inspector
        self.inspector_content = ft.Column([
            ft.Icon(name="visibility", color=COLOR_TEXT_DIM, size=40),
            ft.Text("Hover to inspect\nClick to select", color=COLOR_TEXT_DIM, italic=True, text_align=TextAlign.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        self.card_inspector = ft.Container(
            content=self.inspector_content,
            expand=True,
            border=ft.border.all(1, COLOR_BORDER),
            bgcolor=COLOR_SURFACE, border_radius=6, padding=10,
            alignment=ft.alignment.center
        )

        # Action Area
        self.btn_execute = ft.ElevatedButton(
            "EXECUTE", on_click=self.execute_action,
            icon="play_arrow", bgcolor=COLOR_ACCENT, color="black",
            width=200
        )
        self.txt_hint = ft.Text("", size=11, color=COLOR_TEXT_DIM, text_align=TextAlign.CENTER, italic=True)
        self.action_area = ft.Container(content=self.txt_hint, alignment=ft.alignment.center, height=40)

        self.actions_row = ft.Row(wrap=True, spacing=5, alignment=ft.MainAxisAlignment.CENTER)
        self.phase_col = ft.Column(spacing=2)
        self.txt_turn_info = ft.Text("WAITING SYNC...", size=12, weight=FontWeight.BOLD, color=COLOR_WHITE, text_align=TextAlign.CENTER)

        self.right_panel = ft.Container(
            width=SIDEBAR_WIDTH, bgcolor="#080808", padding=10,
            border=ft.border.only(left=ft.border.BorderSide(1, COLOR_BORDER)),
            content=ft.Column([
                ft.Container(content=self.txt_turn_info, bgcolor="#222", padding=5, border_radius=4,
                             alignment=ft.alignment.center),
                ft.Divider(color=COLOR_BORDER),
                ft.Text("PHASE TRACKER", size=10, weight=FontWeight.BOLD, color=COLOR_ACCENT),
                self.phase_col,
                ft.Divider(color=COLOR_BORDER),
                ft.Text("ACTIONS", size=10, weight=FontWeight.BOLD, color=COLOR_ACCENT),
                self.action_area,
                ft.Divider(color="transparent", height=5),
                self.actions_row,
                ft.Divider(color=COLOR_BORDER),
                ft.Text("INSPECTOR", size=10, weight=FontWeight.BOLD, color=COLOR_ACCENT),
                self.card_inspector
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        )

        # --- CENTER BOARD ---
        self.opp_dash = PlayerDashboard(None, is_me=False)
        self.opp_doll = PaperDoll({}, None, self.on_hover)

        # FIX: Changed spacing from -20 to 5 to avoid overlap
        self.opp_hand = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=5)

        self.opp_skills = ft.Row(alignment=ft.MainAxisAlignment.CENTER)

        self.player_dash = PlayerDashboard(None, is_me=True)
        self.player_doll = PaperDoll({}, self.on_equip_click, self.on_hover)
        self.player_skills = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        self.player_hand = ft.ListView(horizontal=True, spacing=5, height=CARD_HEIGHT + 10, padding=5)

        # Zones
        self.opp_zone = ft.GestureDetector(
            on_tap=self.deselect,
            content=ft.Container(
                expand=4, bgcolor=with_opacity(0.02, COLOR_HP), padding=10,
                content=ft.Column([
                    self.opp_hand,
                    ft.Row([self.opp_dash, self.opp_doll], alignment=ft.MainAxisAlignment.CENTER, spacing=30),
                    self.opp_skills
                ], alignment=ft.MainAxisAlignment.START, spacing=10)
            )
        )

        self.player_zone = ft.GestureDetector(
            on_tap=self.deselect,
            content=ft.Container(
                expand=5, bgcolor=with_opacity(0.02, COLOR_ACCENT), padding=10,
                content=ft.Column([
                    self.player_skills,
                    ft.Row([self.player_dash, self.player_doll], alignment=ft.MainAxisAlignment.CENTER, spacing=30),
                    ft.Divider(color="transparent", height=10),
                    self.player_hand
                ], alignment=ft.MainAxisAlignment.END, spacing=5)
            )
        )

        self.center_board = ft.Column([self.opp_zone, ft.Divider(height=1, color="#333"), self.player_zone],
                                      expand=True, spacing=0)
        self.controls = [ft.Row([self.log_panel, self.center_board, self.right_panel], expand=True, spacing=0)]

        self.running = True
        threading.Thread(target=self.loop, daemon=True).start()

    # --- LOGIC ---

    def loop(self):
        while self.running:
            try:
                data = self.client.fetch_game_state()
                if isinstance(data, dict) and 'players' not in data: continue

                if data:
                    self.game_state = data
                    self.page.run_thread(self.render)

                    if hasattr(data, 'winner') and data.winner.value != 0:
                        print(f"DEBUG: Winner detected: {data.winner}")
                        time.sleep(0.5)
                        self.page.run_thread(self.game_over, data.winner)
                        self.running = False
                        break
                else:
                    self.page.run_thread(self.log_msg, "Connection Terminated.", True)
                    if self.game_state and hasattr(self.game_state, 'winner') and self.game_state.winner.value != 0:
                        self.page.run_thread(self.game_over, self.game_state.winner)
                    self.running = False
            except:
                traceback.print_exc()
                self.running = False
            time.sleep(0.5)

    def is_card_playable(self, card_data, player):
        players = self.game_state.players
        active_player = players[self.game_state.isPlaying]
        if active_player.accessorName != player.accessorName:
            return False

        phase = self.game_state.phase
        ctype = card_data['Type']
        level = card_data.get('Level', 1)

        if phase == Phases.END:
            return len(player.hand) > 5

        if level > player.level: return False
        has_tactical = player.hasTacticalAction

        if phase == Phases.PREPARATION:
            return ctype in ['Skill', 'Instant']
        elif phase == Phases.DUEL:
            if ctype == 'Cantrip': return True
            if ctype in ['Weapon', 'Head', 'Chest', 'Bracers', 'Boots', 'Off-Hand', 'Dual']:
                return has_tactical
            return False
        return False

    def render(self):
        if not self.game_state or isinstance(self.game_state, dict): return

        players = self.game_state.players
        me = next((p for p in players if p.accessorName == self.client.player_name), None)
        opp = next((p for p in players if p.accessorName != self.client.player_name), None)
        if not me: return

        active_p_name = players[self.game_state.isPlaying].accessorName
        self.txt_turn_info.value = f"TURN {self.game_state.turn} | {active_p_name}"
        self.txt_turn_info.color = COLOR_ACCENT if active_p_name == me.accessorName else COLOR_HP

        self.player_dash.update_data(self._p_data(me))
        self.player_doll.update_slots({k: self._c_data(v) for k, v in me.equippedCards.items()})
        if opp:
            self.opp_dash.update_data(self._p_data(opp))
            self.opp_doll.update_slots({k: self._c_data(v) for k, v in opp.equippedCards.items()})

        self.phase_col.controls.clear()
        visible_phases = [Phases.START, Phases.LOOT, Phases.PREPARATION, Phases.DUEL, Phases.END]
        for p in visible_phases:
            is_active = (self.game_state.phase == p)
            color = COLOR_ACCENT if is_active else "#444"
            icon = "radio_button_checked" if is_active else "radio_button_unchecked"
            weight = FontWeight.BOLD if is_active else FontWeight.NORMAL
            self.phase_col.controls.append(
                ft.Container(bgcolor="#222" if is_active else None, padding=2, border_radius=4, content=ft.Row(
                    [ft.Icon(icon, size=12, color=color), ft.Text(p.name, size=10, color=color, weight=weight)])))

        self.actions_row.controls.clear()
        active_player_idx = self.game_state.isPlaying
        is_my_turn = (players[active_player_idx].accessorName == me.accessorName)
        phase = self.game_state.phase
        my_idx = 0 if players[0].accessorName == me.accessorName else 1

        pass_text = "PASS PHASE"
        if phase == Phases.SETUP:
            pass_text = "READY"
        elif phase == Phases.PREPARATION:
            pass_text = "TO DUEL"
        elif phase == Phases.DUEL:
            pass_text = "END DUEL"
        elif phase == Phases.END:
            pass_text = "END TURN"

        disable_pass = not is_my_turn
        if phase == Phases.END and len(me.hand) > 5: disable_pass = True

        btn_pass = ft.ElevatedButton(pass_text, on_click=self.pass_phase,
                                     bgcolor="#444" if not disable_pass else "#222",
                                     color="white" if not disable_pass else "#666", disabled=disable_pass)
        self.actions_row.controls.append(btn_pass)

        if is_my_turn:
            if phase == Phases.SETUP and not self.game_state.hasMulligan[my_idx]:
                self.actions_row.controls.append(
                    ft.ElevatedButton("MULLIGAN", on_click=self.mulligan, bgcolor=COLOR_SURFACE, color=COLOR_TEXT))
            if phase == Phases.DUEL and me.hasCombatAction:
                self.actions_row.controls.append(
                    ft.ElevatedButton("ATTACK", on_click=self.attack, icon="gavel", bgcolor=COLOR_HP, color="white"))

        # Hand
        self.player_hand.controls.clear()
        for i, card in enumerate(me.hand):
            c_data = self._c_data(card)
            c_data['id'] = i
            is_playable = self.is_card_playable(c_data, me)
            is_sel = (self.selection and self.selection['source'] == 'HAND' and self.selection['index'] == i)
            if phase == Phases.END and len(me.hand) > 5: is_playable = True

            self.player_hand.controls.append(
                CardView(c_data, lambda d, idx=i: self.on_select('HAND', idx, d), self.on_hover,
                         in_hand=True, selected=is_sel, playable=is_playable)
            )

        # Skills
        self.player_skills.controls.clear()
        for i in range(4):
            card = me.skillSlots[i] if i < len(me.skillSlots) else None
            if card:
                c_data = self._c_data(card)
                is_sel = (self.selection and self.selection['source'] == 'SKILL' and self.selection['index'] == i)
                self.player_skills.controls.append(
                    CardView(c_data, lambda d, idx=i: self.on_select('SKILL', idx, d), self.on_hover,
                             in_hand=False, selected=is_sel)
                )
            else:
                self.player_skills.controls.append(
                    ft.Container(width=CARD_WIDTH, height=CARD_HEIGHT, border=ft.border.all(1, "#222"),
                                 bgcolor="#151515", content=ft.Text("EMPTY", size=10, color="#333"),
                                 alignment=ft.alignment.center))

        # Opponent Hand (Visible Backs)
        self.opp_hand.controls.clear()
        self.opp_skills.controls.clear()
        if opp:
            for _ in range(len(opp.hand)):
                # FIX: Enhanced Card Back style
                self.opp_hand.controls.append(
                    ft.Container(
                        width=45, height=65,  # Slightly larger
                        bgcolor="#37474f",  # Blue Grey
                        border=ft.border.all(2, "#cfd8dc"),  # Light border
                        border_radius=4,
                        # content=ft.Icon(name="token", size=20, color="#444"), # Optional icon
                        alignment=ft.alignment.center
                    )
                )
            for card in opp.skillSlots:
                if card:
                    self.opp_skills.controls.append(
                        CardView(self._c_data(card), is_opponent=True, on_hover_handler=self.on_hover))

        if self.game_state.logs:
            current_len = len(self.log_list.controls)
            if len(self.game_state.logs) > current_len:
                for msg in self.game_state.logs[current_len:]:
                    self.log_msg(msg)

        self.update_action_area(me, is_my_turn)
        self.page.update()

    # --- INTERACTION ---

    def deselect(self, e):
        if self.selection:
            self.selection = None
            self.card_inspector.content = self.inspector_content
            self.card_inspector.alignment = ft.alignment.center
            players = self.game_state.players
            me = next((p for p in players if p.accessorName == self.client.player_name), None)
            self.update_action_area(me, players[self.game_state.isPlaying].accessorName == me.accessorName)
            self.render()

    def on_hover(self, card_data, is_hovering):
        if is_hovering:
            self.update_inspector(card_data)
        else:
            if self.selection:
                self.update_inspector(self.selection['data'])
            else:
                self.card_inspector.content = self.inspector_content
                self.card_inspector.alignment = ft.alignment.center
                self.page.update()

    def on_select(self, source, index, card_data):
        if self.selection and self.selection['index'] == index and self.selection['source'] == source:
            self.deselect(None)
        else:
            self.selection = {'source': source, 'index': index, 'data': card_data}
            self.update_inspector(card_data)
        self.render()

    def update_inspector(self, card_data):
        self.card_inspector.alignment = ft.alignment.top_left
        self.card_inspector.content = ft.Column([
            ft.Row([
                ft.Text(card_data['Name'], size=18, weight=FontWeight.BOLD, color=COLOR_WHITE, expand=True),
                ft.Container(bgcolor=COLOR_LEVEL_BADGE, padding=5, border_radius=10,
                             content=ft.Text(f"Lv {card_data.get('Level', 1)}", size=10, weight=FontWeight.BOLD))
            ]),
            ft.Row([ft.Container(bgcolor="#333", padding=5, content=ft.Text(card_data['Type'], size=10))]),
            ft.Divider(color="#444"),
            ft.Text(card_data['Text'], size=13, color=COLOR_WHITE),
            ft.Divider(color="#444"),
            ft.Text(f"CD: {card_data.get('CD', 0)}", color=COLOR_ACCENT, weight=FontWeight.BOLD)
        ], scroll=ft.ScrollMode.AUTO)
        self.page.update()

    def on_equip_click(self, slot_name, card_data):
        if not card_data: return
        self.on_select('EQUIP', slot_name, card_data)

    def update_action_area(self, me, is_my_turn):
        phase = self.game_state.phase

        if not is_my_turn:
            self.txt_hint.value = "OPPONENT TURN - PLEASE WAIT..."
            self.txt_hint.color = COLOR_HP
            self.action_area.content = self.txt_hint
            self.btn_execute.disabled = True
            return

        self.txt_hint.color = COLOR_TEXT_DIM

        if not self.selection:
            hint = ""
            if phase == Phases.PREPARATION:
                hint = "Select a Skill or Instant from Hand to play."
            elif phase == Phases.DUEL:
                hint = "Select Weapon/Equip from Hand to Equip, or use Skills/Items."
            elif phase == Phases.END:
                if len(me.hand) > 5:
                    hint = f"Hand limit exceeded. Select {len(me.hand) - 5} card(s) to DISCARD."
                else:
                    hint = "End of Turn."
            else:
                hint = "Waiting..."
            self.txt_hint.value = hint
            self.action_area.content = self.txt_hint
            return

        src = self.selection['source']
        c_type = self.selection['data']['Type']

        txt = "INVALID"
        disabled = True
        action_color = COLOR_ACCENT

        if src == 'HAND':
            if phase == Phases.PREPARATION and c_type in ['Skill', 'Instant']:
                txt = "DEPLOY SKILL";
                disabled = False
            elif phase == Phases.DUEL:
                if c_type == 'Cantrip':
                    txt = "CAST CANTRIP"; disabled = False
                elif c_type in ['Weapon', 'Head', 'Chest', 'Bracers', 'Boots', 'Off-Hand', 'Dual']:
                    txt = "EQUIP"; disabled = False
            elif phase == Phases.END:
                if len(me.hand) > 5: txt = "DISCARD"; action_color = COLOR_HP; disabled = False

        elif src == 'SKILL':
            if phase == Phases.DUEL:
                txt = "ACTIVATE SKILL"
                if self.selection['data']['currentCD'] == 0:
                    disabled = False
                else:
                    txt = "COOLDOWN"

        elif src == 'EQUIP':
            if phase == Phases.DUEL:
                txt = "ACTIVATE"
                disabled = False

        self.btn_execute.text = txt
        self.btn_execute.disabled = disabled
        self.btn_execute.bgcolor = action_color if not disabled else "#333"
        self.btn_execute.color = "black" if not disabled else "#888"
        self.action_area.content = self.btn_execute

    def execute_action(self, e):
        if not self.selection: return
        src = self.selection['source']
        idx = self.selection['index']
        phase = self.game_state.phase

        action = None
        args = {}

        if src == 'HAND':
            args = {'index': idx}
            c_type = self.selection['data']['Type']
            if phase == Phases.PREPARATION:
                action = Actions.PLAY
            elif phase == Phases.DUEL:
                if c_type == 'Cantrip':
                    action = Actions.PLAY
                else:
                    action = Actions.EQUIP
            elif phase == Phases.END:
                action = Actions.DISCARD

        elif src == 'SKILL':
            action = Actions.ACTIVATE
            args = {'source': 'SKILL', 'index': idx}

        elif src == 'EQUIP':
            action = Actions.ACTIVATE
            args = {'source': 'EQUIP', 'slot': idx}

        if action:
            self.client.send_action(action, args)
            self.selection = None
            self.btn_execute.disabled = True
            self.txt_hint.value = "Processing..."
            self.action_area.content = self.txt_hint
            self.page.update()

    def pass_phase(self, e):
        self.client.send_action(Actions.PASS_PHASE)

    def mulligan(self, e):
        self.client.send_action(Actions.MULLIGAN)

    def attack(self, e):
        self.client.send_action(Actions.ATTACK)

    def _p_data(self, p):
        if not p: return {}
        try:
            raw_hp = getattr(p, 'currentHP', 0)
            raw_dur = getattr(p, 'currentDurability', 30)
            cur = int(float(raw_hp))
            dur = int(float(raw_dur))
            if dur <= 0: dur = 1
        except:
            cur, dur = 0, 1

        return {
            'name': getattr(p, 'accessorName', 'Unknown'),
            'level': getattr(p, 'level', 1),
            'hp': f"{cur}/{dur}",
            'stats': {'Power': getattr(p, 'currentPower', 0), 'Tenacity': getattr(p, 'currentTenacity', 0),
                      'Efficiency': getattr(p, 'currentEfficiency', 0),
                      'Sensitivity': getattr(p, 'currentSensitivity', 0)},
            'counters': getattr(p, 'counters', []),
            'hasTactical': getattr(p, 'hasTacticalAction', False),
            'hasCombat': getattr(p, 'hasCombatAction', False)
        }

    def _c_data(self, c):
        if not c: return {}
        t = c.cardType.value if hasattr(c.cardType, 'value') else c.cardType
        cd_val = getattr(c, 'CD', getattr(c, 'cd', 0))
        return {
            'Name': getattr(c, 'name', 'Unknown'), 'Type': t, 'Level': getattr(c, 'level', 1),
            'Text': getattr(c, 'Text', ''), 'CD': cd_val, 'currentCD': getattr(c, 'currentCD', 0)
        }

    def log_msg(self, msg, is_error=False):
        color = COLOR_HP if is_error else "#81c784" if "damage" in msg else COLOR_TEXT
        self.log_list.controls.append(ft.Text(f"> {msg}", color=color, size=11, font_family="Consolas"))
        self.page.update()

    def game_over(self, winner):
        try:
            me_idx = self.client.my_id
            did_i_win = (winner.value == (me_idx + 1))

            title = "MISSION ACCOMPLISHED" if did_i_win else "CRITICAL FAILURE"
            bg_color = COLOR_ACCENT if did_i_win else COLOR_HP
            msg = f"Winner: {self.game_state.players[winner.value - 1].accessorName}"

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text(title, weight=ft.FontWeight.BOLD, color=bg_color),
                content=ft.Text(msg, size=16),
                actions=[ft.TextButton("EXIT", on_click=lambda e: self.page.go("/"))],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.open(dlg)
            self.page.update()
        except Exception as e:
            print(f"Error showing Game Over dialog: {e}")
            traceback.print_exc()