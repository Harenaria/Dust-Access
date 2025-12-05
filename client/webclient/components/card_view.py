import flet as ft
from client.webclient.style import *


class CardView(ft.Container):
    def __init__(self, card_data, on_click_handler=None, on_hover_handler=None, is_opponent=False, in_hand=False,
                 selected=False, playable=True):
        super().__init__()
        self.card_data = card_data
        self.on_click_handler = on_click_handler
        self.on_hover_handler = on_hover_handler
        self.is_opponent = is_opponent
        self.in_hand = in_hand
        self.selected = selected
        self.playable = playable

        # Data parsing
        self.card_name = card_data.get('Name', 'Unknown')
        self.card_type = card_data.get('Type', 'Base')
        self.level = card_data.get('Level', 1)
        self.text = card_data.get('Text', '')
        self.current_cd = card_data.get('currentCD', 0)

        # Basic layout
        self.width = CARD_WIDTH
        self.height = CARD_HEIGHT
        self.border_radius = 8
        self.padding = 0
        self.on_click = self._handle_click
        self.on_hover = self._handle_hover

        # Tap Logic
        is_tapped = (not self.in_hand) and (self.current_cd > 0)
        self.rotate = ft.Rotate(angle=ROTATE_90 if is_tapped else 0, alignment=ft.alignment.center)
        self.animate_rotation = ft.Animation(300, ft.AnimationCurve.EASE_OUT)

        self.content = self._build_content()
        self._apply_styling()

    def _build_content(self):
        # FIX: Hide content ONLY if the name is "Covered" (Server masked it)
        # This allows Opponent Skills (which have real names) to be seen.
        if self.card_name == "Covered":
            return ft.Container(
                bgcolor=COLOR_SURFACE,
                border_radius=6,
                alignment=ft.alignment.center,
                content=ft.Icon(name="token", color=COLOR_BORDER, size=30)
            )

        header_color = CARD_COLORS.get(self.card_type, COLOR_SURFACE)

        # --- HEADER ---
        header = ft.Container(
            bgcolor=header_color, padding=5,
            content=ft.Row([
                ft.Text(self.card_name, size=11, weight=ft.FontWeight.BOLD, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS, color=COLOR_WHITE, expand=True),
                ft.Container(
                    width=18, height=18, bgcolor=COLOR_LEVEL_BADGE, border_radius=10,
                    alignment=ft.alignment.center,
                    content=ft.Text(str(self.level), size=9, weight="bold", color="white")
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        # --- BODY ---
        body = ft.Container(
            padding=6, expand=True, bgcolor=COLOR_SURFACE,
            content=ft.Column([
                ft.Text(self.card_type, size=9, italic=True, color=COLOR_TEXT_DIM),
                ft.Text(self.text, size=10, max_lines=5, overflow=ft.TextOverflow.ELLIPSIS, color=COLOR_TEXT),
            ])
        )

        # Overlay CD
        show_cd = (not self.in_hand) and (self.current_cd > 0)
        content = ft.Column([header, body], spacing=0)

        if show_cd:
            return ft.Stack([
                content,
                ft.Container(
                    bgcolor=with_opacity(0.85, COLOR_BLACK), alignment=ft.alignment.center, border_radius=6,
                    content=ft.Text(f"{self.current_cd}", size=36, weight=ft.FontWeight.BOLD, color=COLOR_ACCENT)
                )
            ])
        return content

    def _apply_styling(self):
        # FIX: Logic split for Opponent vs Player styling
        if self.is_opponent:
            if self.card_name == "Covered":
                # Hidden card (Hand)
                self.border = ft.border.all(1, COLOR_BORDER)
                self.bgcolor = "#222"
            else:
                # Visible Enemy Card (Skill on field) - RED BORDER
                self.border = ft.border.all(1, COLOR_HP)
                self.bgcolor = COLOR_SURFACE

            self.opacity = 1
        else:
            # Player Logic
            if self.in_hand and not self.playable:
                self.opacity = 0.6
                base_border = COLOR_UNPLAYABLE
            else:
                self.opacity = 1
                base_border = COLOR_PLAYABLE if (self.in_hand and self.playable) else COLOR_BORDER

            if self.selected:
                self.border = ft.border.all(2, COLOR_SELECTION)
                self.shadow = ft.BoxShadow(blur_radius=15, color=COLOR_SELECTION)
            else:
                is_ready_field = (not self.in_hand) and (self.current_cd == 0)
                final_color = COLOR_ACCENT if is_ready_field else base_border
                self.border = ft.border.all(1, final_color)
                self.shadow = None

            self.bgcolor = COLOR_SURFACE

    def _handle_click(self, e):
        if self.on_click_handler:
            self.on_click_handler(self.card_data)

    def _handle_hover(self, e):
        if self.on_hover_handler:
            self.on_hover_handler(self.card_data, e.data == "true")