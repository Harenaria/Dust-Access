from client_views.fletapp.locals.locale import Locale
from core.enums import Phases

en_US:Locale = Locale("en_US", {
    'empty': "",
    'welcome': "welcome to the S&&S",
    'quick_match': "quick match",
    'create_room': "create lobby",
    'or': "or",
    'join_room': "join lobby",
    'enter_code': "enter code",
    'waiting_opponent': "please wait...",
    'decks': "decks",
    'accessor_name': "accessor name",
    'specs': "specs",
    'deploy': "deploy",
    'start_game': "start game",
    "turn": "Turn",
    Phases.SETUP.name : "Setup",
    Phases.START.name : "Start",
    Phases.LOOT.name : "Loot",
    Phases.PREPARATION.name : "Preparation",
    Phases.DUEL.name : "Duel",
    Phases.END.name : "End",
    "skill": "Skill",
    "weapon": "Weapon",
    "off-hand": "Off-Hand",
})