from flet.core.icons import Icons

from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.tiles import Tile


def DeckTile(deck_id: int, deck_meta: dict, on_click):
    cl = deck_meta['classes'][0]
    cl1 = deck_meta['classes'][1] if len(deck_meta['classes']) > 1 else None #Dual-Class Decks support
    color = AppTheme.PURPLE #For debug purpose. It should never happen.
    color1 = None
    match cl:
        case 'Heavy':
            color = AppTheme.RED
        case 'Medium':
            color = AppTheme.GREEN_DARK
        case 'Light':
            color = AppTheme.BLUE_3
        case _:
            pass
    match cl1:
        case 'Heavy':
            color1 = AppTheme.RED
        case 'Medium':
            color1 = AppTheme.GREEN_DARK
        case 'Light':
            color1 = AppTheme.BLUE_3
        case _:
            pass
    deck_name: str = deck_meta['name']
    return Tile(on_click, deck_name, Icons.AMP_STORIES_OUTLINED, color, color1)

def SpecTile(spec_name:str, spec_class:str, on_click):
    color = AppTheme.PURPLE
    match spec_class:
        case 'Heavy':
            color = AppTheme.RED
        case 'Medium':
            color = AppTheme.GREEN_DARK
        case 'Light':
            color = AppTheme.BLUE_3
        case _:
            pass
    return Tile(on_click, spec_name, Icons.ACCOUNT_CIRCLE_OUTLINED, color)
