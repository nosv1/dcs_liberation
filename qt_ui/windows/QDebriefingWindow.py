import logging
from typing import Callable, Dict, TypeVar

from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.debriefing import Debriefing

T = TypeVar("T")


class LossGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing, player: bool) -> None:
        super().__init__()

        self.add_loss_rows(
            debriefing.air_losses.by_type(player), lambda u: f"Aircraft: ({u})"
        )
        self.add_loss_rows(
            debriefing.front_line_losses_by_type(player), lambda u: f"Front Line: ({u})"
        )
        self.add_loss_rows(
            debriefing.convoy_losses_by_type(player), lambda u: f"Convoy: ({u})"
        )
        self.add_loss_rows(
            debriefing.cargo_ship_losses_by_type(player), lambda u: f"Cargo Ship: ({u})"
        )
        self.add_loss_rows(
            debriefing.airlift_losses_by_type(player), lambda u: f"Airlift: ({u})"
        )
        self.add_loss_rows(
            debriefing.ground_object_losses_by_type(player),
            lambda u: f"Objective Areas: ({u})",
        )
        self.add_loss_rows(
            debriefing.scenery_losses_by_type(player), lambda u: f"Scenery: ({u})"
        )
        self.add_loss_rows(
            debriefing.air_fields_by_type(player), lambda u: f"Airfields: ({u})"
        )
        self.add_loss_rows(
            debriefing.bafoons.by_type(player), lambda u: f"Bafoons: ({u})"
        )

        # TODO: Display dead ground object units and runways.

    def add_loss_rows(self, losses: Dict[T, int], header: Callable[[T], str]):

        if losses:
            total_losses_of_type = sum(losses.values())
            self.addWidget(
                QLabel(f"<b>{header(total_losses_of_type)}</b>"),
                self.rowCount(),
                0,
            )

        for unit_type, count in losses.items():
            row = self.rowCount()
            self.addWidget(QLabel(f"    {unit_type}"), row, 0)
            self.addWidget(QLabel(str(count)), row, 1)

        # add spacer row
        if losses:
            self.addWidget(QLabel(""), self.rowCount(), 0)


class ScrollingCasualtyReportContainer(QGroupBox):
    def __init__(self, debriefing: Debriefing, player: bool) -> None:
        country = debriefing.player_country if player else debriefing.enemy_country
        super().__init__(f"{country}'s lost units:")
        scroll_content = QWidget()
        scroll_content.setLayout(LossGrid(debriefing, player))
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_content)
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)


class QDebriefingWindow(QDialog):
    def __init__(self, debriefing: Debriefing):
        super(QDebriefingWindow, self).__init__()
        self.debriefing = debriefing

        self.setModal(True)
        self.setWindowTitle("Debriefing")
        self.setMinimumSize(600, 400)
        self.setWindowIcon(QIcon("./resources/icon.png"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self)
        header.setGeometry(0, 0, 655, 106)
        pixmap = QPixmap("./resources/ui/debriefing.png")
        header.setPixmap(pixmap)
        layout.addWidget(header)
        layout.addStretch()

        title = QLabel("<b>Casualty report</b>")
        layout.addWidget(title)

        player_lost_units = ScrollingCasualtyReportContainer(debriefing, player=True)
        layout.addWidget(player_lost_units)

        enemy_lost_units = ScrollingCasualtyReportContainer(debriefing, player=False)
        layout.addWidget(enemy_lost_units)

        okay = QPushButton("Okay")
        okay.clicked.connect(self.close)
        layout.addWidget(okay)
