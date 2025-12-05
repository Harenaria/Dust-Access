import flet as ft
from collections import Counter
from client.webclient.style import *


# ... (ActionLamp e StatBadge rimangono uguali a prima) ...
def ActionLamp(active, color, tooltip):
    return ft.Container(
        width=15, height=8, border_radius=2,
        bgcolor=color if active else "#222",
        border=ft.border.all(1, color if active else "#444"),
        shadow=ft.BoxShadow(blur_radius=6, color=color) if active else None,
        tooltip=tooltip
    )


def StatBadge(icon_name, value, label, color=COLOR_TEXT):
    return ft.Column([
        ft.Icon(name=icon_name, size=14, color=color),
        ft.Text(str(value), size=12, weight=ft.FontWeight.BOLD, color=color),
        ft.Text(label, size=8, color=COLOR_TEXT_DIM)
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)


class PlayerDashboard(ft.Container):
    # ... (PlayerDashboard rimane invariato, copialo dal passo precedente se necessario) ...
    def __init__(self, player_data, is_me=True):
        super().__init__()
        self.player_data = player_data
        self.is_me = is_me
        self.padding = 8
        self.bgcolor = "#1a1a1a"
        self.border_radius = 8
        self.border = ft.border.all(1, COLOR_BORDER)
        self.width = 220
        self.update_view()

    def update_data(self, player_data):
        if not player_data: return
        self.player_data = player_data
        self.update_view()

    def update_view(self):
        name = "Unknown"
        level = 1
        hp_str = "0/1"
        stats = {}
        counters = []
        has_tact = False
        has_comb = False

        if self.player_data:
            name = self.player_data.get('name', 'Unknown')
            level = self.player_data.get('level', 1)
            hp_str = self.player_data.get('hp', '0/1')
            stats = self.player_data.get('stats', {})
            counters = self.player_data.get('counters', [])
            has_tact = self.player_data.get('hasTactical', False)
            has_comb = self.player_data.get('hasCombat', False)

        try:
            parts = str(hp_str).split('/')
            cur = int(float(parts[0]))
            max_ = int(float(parts[1])) if len(parts) > 1 else 1
            if max_ <= 0: max_ = 1
            hp_pct = max(0.0, min(1.0, cur / max_))
        except:
            hp_pct, cur, max_ = 0, 0, 1

        lamps = ft.Row([
            ActionLamp(has_tact, COLOR_ACCENT, "Tactical Action"),
            ActionLamp(has_comb, COLOR_HP, "Combat Action")
        ], spacing=4)

        status_text = f"{cur} / {max_}"
        status_color = COLOR_WHITE
        if cur <= 0:
            status_text = "DEAD"
            status_color = COLOR_TEXT_DIM

        self.content = ft.Column([
            ft.Row([
                ft.Stack([ft.CircleAvatar(content=ft.Text(str(level), size=10), radius=16, bgcolor="#333")]),
                ft.Column([
                    ft.Row([ft.Text(name[:12], weight=ft.FontWeight.BOLD, size=12), lamps],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(status_text, size=16, weight=ft.FontWeight.BOLD, color=status_color),
                    ft.ProgressBar(value=hp_pct, color=COLOR_HP, bgcolor="#440000", height=6),
                ], spacing=2, expand=True)
            ], spacing=8),

            ft.Container(
                bgcolor="#222", padding=4, border_radius=4, margin=ft.margin.only(top=5),
                content=ft.Row([
                    StatBadge("flash_on", stats.get('Power', 0), "PWR", COLOR_HP),
                    StatBadge("shield", stats.get('Tenacity', 0), "TEN", "#90caf9"),
                    StatBadge("speed", stats.get('Efficiency', 0), "EFF", "#a5d6a7"),
                    StatBadge("wifi", stats.get('Sensitivity', 0), "SEN", "#ce93d8"),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
            ),

            ft.Row([
                ft.Container(bgcolor="#4a148c", padding=2, border_radius=2, content=ft.Text(f"{k} x{v}", size=8))
                for k, v in Counter(counters).items()
            ], wrap=True, spacing=2)
        ], spacing=2)


class PaperDoll(ft.Container):
    # FIX: Added on_hover_handler
    def __init__(self, equipped_cards, on_card_click, on_hover_handler=None):
        super().__init__()
        self.on_click = on_card_click
        self.on_hover_handler = on_hover_handler  # New
        self.padding = 5
        self.bgcolor = "#111"
        self.border_radius = 8
        self.border = ft.border.all(1, "#333")
        self.update_slots(equipped_cards)

    def update_slots(self, equipped_cards):
        SLOT_DIM = 45

        def slot(name, icon, visible=True):
            if not visible:
                return ft.Container(width=SLOT_DIM, height=SLOT_DIM, bgcolor="transparent")

            card = equipped_cards.get(name)
            color = COLOR_ACCENT if card else "#444"
            content = ft.Icon(name=icon, size=20, color=color)

            if card:
                content = ft.Column([
                    content,
                    ft.Text(card['Name'][:6], size=7, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=0)

            # FIX: Hover support via MouseRegion or on_hover of Container
            container = ft.Container(
                width=SLOT_DIM, height=SLOT_DIM,
                bgcolor="#252525", border=ft.border.all(1, color), border_radius=4,
                content=content,
                on_click=lambda e: self.on_click(name, card) if card else None,  # Pass Slot Name AND Card Data
                on_hover=lambda e: self.on_hover_handler(card, e.data == "true") if (
                            card and self.on_hover_handler) else None,
                # tooltip=f"{name}: {card['Name']}" if card else name # Tooltip redundant with inspector
            )
            return container

        row1 = ft.Row([slot('', '', False), slot('Head', 'face'), slot('', '', False)], spacing=2)
        row2 = ft.Row([slot('Weapon', 'colorize'), slot('Chest', 'shield'), slot('Off-Hand', 'back_hand')], spacing=2)
        row3 = ft.Row([slot('', '', False), slot('Bracers', 'watch'), slot('', '', False)], spacing=2)
        row4 = ft.Row([slot('', '', False), slot('Boots', 'directions_walk'), slot('', '', False)], spacing=2)

        self.content = ft.Column([row1, row2, row3, row4], spacing=2, alignment=ft.MainAxisAlignment.CENTER)