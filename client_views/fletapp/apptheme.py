import os
class AppTheme:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ASSET_DIR = os.path.join(_BASE_DIR, "assets")
    FONTS_DIR = os.path.join(ASSET_DIR, "fonts")
    COLOR_BG = "#000000"
    COLOR_FG = "#FFFFFF"
    GREY = "#1F1F1F"
    GREEN_LIGHT = "#8CBF26"
    GREEN_DARK = "#339933"
    BLUE_1 = "#00ABA9"
    BLUE_2 = "#1BA1E2"
    BLUE_3 = "#3E65FE"
    PURPLE = "#AA00FF"
    PINK_LIGHT = "#E671B8"
    PINK_DARK = "#FF0097"
    RED = "#E51400"
    RED_DARK = "#990000"
    YELLOW = "#F09609"
    BROWN = "#A05000"

