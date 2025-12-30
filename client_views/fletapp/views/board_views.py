from flet.core.column import Column
from flet.core.container import Container
from flet.core.page import Page
from flet.core.row import Row
from flet.core.text import Text
from flet.core.types import FontWeight, MainAxisAlignment, CrossAxisAlignment
from flet.core.view import View

from client_views.fletapp.locals.locale import Locale
from client_views.fletapp.apptheme import AppTheme
from client_views.fletapp.components.slots import SkillSlot, WieldSlots
from client_views.fletapp.utils import Grid
from core.enums import CardType, Phases
from core.game import Game
from core.player import Player


class SkillGrid(Grid):
    def __init__(self, players: list[Player]):
        rows = len(players)
        cols = max((len(p.skillSlots) for p in players), default=0)
        super().__init__(rows, cols, Container)


class BoardView(View):
    def player_board(self, player_id, isMe: bool):
        player = self._game.players[player_id]
        pname = "loading..." if player_id < 0 else player.accessorName
        hp = 30 if player_id < 0 else player.currentHP
        dur = 30 if player_id < 0 else player.currentDurability
        power = 0 if player_id < 0 else player.currentPower
        eff = 0 if player_id < 0 else player.currentEfficiency
        ten = 0 if player_id < 0 else player.currentTenacity
        sens = 0 if player_id < 0 else player.currentSensitivity

        pavatar = Container() #TODO: Avatar
        pstats = Column(controls= [
                                Text(value=str(power), size=24, font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.RED),
                                Text(value=str(eff), size=24, font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.BLUE_2),
                                Text(value=str(ten), size=24, font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.COLOR_FG),
                                Text(value=str(sens), size=24, font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.PINK_DARK),
        ])

        pinfo = Row(controls= [
                                Text(pname, size=24, font_family='Noto Sans', weight=FontWeight.W_200, color=AppTheme.YELLOW),
                                Container(
                                            content= Row(controls=[
                                                Text(str(hp), size=36, font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.COLOR_FG),
                                                Text(f"/{str(dur)} hp", size=24, font_family='Noto Sans', weight=FontWeight.W_200, color=AppTheme.COLOR_FG),])
                                )
        ])
        sk1 = self._skillslots.set(player_id, 0, SkillSlot(self._localization, 0, player.skillSlots[0]))
        sk2 = self._skillslots.set(player_id, 1, SkillSlot(self._localization, 1, player.skillSlots[1]))
        sk3 = self._skillslots.set(player_id, 2, SkillSlot(self._localization, 2, player.skillSlots[2]))
        sk4 = self._skillslots.set(player_id, 3, SkillSlot(self._localization, 3, player.skillSlots[3]))
        pskills = Row(controls=[
            # TODO: Refine Skill Slots
            sk1, sk2, sk3, sk4
        ])
        #TODO: Refine Wield Slots
        self._wieldslots[player_id] = WieldSlots(self._localization, player.equippedCards[CardType.WEAPON], player.equippedCards[CardType.OFF_HAND])

        if isMe:
            return Row(
                    alignment=MainAxisAlignment.CENTER,
                    expand=True,
                    controls=[
                        pavatar,
                        pstats,
                        Column(controls=[pinfo, pskills]),
                        self._wieldslots[player_id]
                    ]
            )
        else:
            return Row(
                    alignment=MainAxisAlignment.CENTER,
                    expand=True,
                    controls=[
                        self._wieldslots[player_id],
                        Column(controls=[pinfo, pskills]),
                        pstats,
                        pavatar
                    ]
            )

    def __init__(self, page: Page, localization: Locale, room_code: str, initial_state: Game | None = None):
        super(BoardView, self).__init__(route="/game")
        self._page = page
        self._page.window.min_width = 568 #iPhone SE size
        self._page.window.min_height = 320 #iPhone SE size

        self._localization = localization
        self._room_code = room_code
        self._game: Game | None = initial_state
        self._this_id:int = -1
        self._opponent_id:int = -2
        self._turn_counter:int = 1
        self._phase:Phases = Phases.SETUP

        self._player_main_board = Container()
        self._opponent_main_board = Container()
        self._skillslots: SkillGrid = SkillGrid(self._game.players if self._game else [])

        # the wielded equipment containers interact with themselves by design,
        # and the row has a fixated number of easily distinguishable elements,
        # so we do not keep them directly.
        self._wieldslots: list = [Row() for _ in range(len(self._game.players))] if self._game else []
        self._header_bar = Container(
            bgcolor=AppTheme.GREY,
            content= Row(
                controls= [
                    Row(
                        expand=True,
                        controls= [
                            Row(controls= [
                                Text(self._localization['turn'] + f" {self._turn_counter}", size=24,
                                     font_family='Noto Sans', weight=FontWeight.W_400, color=AppTheme.COLOR_FG),
                                Text("-", size=24, font_family='Noto Sans', weight=FontWeight.W_400,
                                     color=AppTheme.COLOR_FG),
                                Text(self._localization[self._phase.name], size=24, font_family='Noto Sans',
                                     weight=FontWeight.W_400, color=AppTheme.COLOR_FG),
                            ])
                            #TODO: put buttons here if the other components are not shown
                        ]
                    )
                ]
            )
        )
        self.controls = [
            Column(
                horizontal_alignment=CrossAxisAlignment.CENTER,
                alignment=MainAxisAlignment.CENTER,
                expand=True,
                controls=[
                    self._opponent_main_board,
                    self._player_main_board,
                ]
            ),
            self._header_bar
        ]
        if isinstance(self._game, Game):
            self.update_game(self._game)

    def update_player_boards(self):
        self._player_main_board.content = self.player_board(self._this_id, True)
        self._opponent_main_board.content = self.player_board(self._opponent_id, False)

        if self._player_main_board.page:
            self._player_main_board.update()

        if self._opponent_main_board.page:
            self._opponent_main_board.update()

    def update_game(self, game) -> None:
        self._game = game
        if self._this_id == -1 and self._game.players:
            p0_hand = self._game.players[0].hand
            if p0_hand and hasattr(p0_hand[0], 'name') and p0_hand[0].name == "Covered":
                self._this_id = 1
            else:
                self._this_id = 0
            self._opponent_id = 1 - self._this_id
            self._turn_counter = self._game.turn
            self._phase = self._game.phase
        self._skillslots = SkillGrid(self._game.players)
        self._wieldslots: list = [Row() for _ in range(len(self._game.players))]
        self.update_player_boards()
        if self._header_bar.page:
            self._header_bar.update()

