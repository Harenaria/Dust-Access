import flet as ft

def with_opacity(opacity: float, hex_color: str) -> str:
    if hex_color.startswith("#"): hex_color = hex_color[1:]
    if len(hex_color) == 6:
        alpha = int(opacity * 255)
        alpha = max(0, min(255, alpha))
        return f"#{alpha:02x}{hex_color}"
    return f"#{hex_color}"

# --- Palette ---
COLOR_BACKGROUND = "#121212"
COLOR_SURFACE = "#1e1e1e"
COLOR_ACCENT = "#00e5ff"
COLOR_HP = "#ff1744"
COLOR_ENERGY = "#ff9100"
COLOR_TEXT = "#eeeeee"
COLOR_TEXT_DIM = "#9e9e9e"
COLOR_BORDER = "#37474f"

# States
COLOR_PLAYABLE = "#00e676"
COLOR_UNPLAYABLE = "#424242"
COLOR_SELECTION = "#ffea00"

COLOR_BLACK = "#000000"
COLOR_WHITE = "#ffffff"
COLOR_LEVEL_BADGE = "#2962ff"

CARD_COLORS = {
    'Weapon': "#3e2723", 'Skill': "#263238", 'Instant': "#ef6c00",
    'Equip': "#1a237e", 'Cantrip': "#4a148c", 'Base': "#424242"
}

# Dimensions
CARD_WIDTH = 110 # Increased width for better reading
CARD_HEIGHT = 150 # Increased height
SIDEBAR_WIDTH = 280
ROTATE_90 = 1.57