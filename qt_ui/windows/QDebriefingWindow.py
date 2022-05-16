import logging
import re
from typing import Callable, Dict, TypeVar

from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from game.debriefing import Debriefing


T = TypeVar("T")


class LossGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing, player: bool) -> None:
        super().__init__()

        self.add_loss_rows(
            debriefing.air_losses.by_type(player), lambda c: f"Aircraft ({c})"
        )
        self.add_loss_rows(
            debriefing.front_line_losses_by_type(player), lambda c: f"Front line ({c})"
        )
        self.add_loss_rows(
            debriefing.convoy_losses_by_type(player), lambda c: f"Convoy ({c})"
        )
        self.add_loss_rows(
            debriefing.cargo_ship_losses_by_type(player), lambda c: f"Cargo ship ({c})"
        )
        self.add_loss_rows(
            debriefing.airlift_losses_by_type(player), lambda c: f"Airlift ({c})"
        )
        self.add_loss_rows(
            debriefing.ground_objects_by_type(player),
            lambda c: f"Objective areas ({c})",
        )
        self.add_loss_rows(
            debriefing.building_losses_by_type(player), lambda c: f"Buildings ({c})"
        )
        self.add_loss_rows(
            debriefing.air_fields_by_type(player), lambda c: f"Air fields ({c})"
        )
        self.add_loss_rows(
            debriefing.bafoons.by_type(player), lambda c: f"Bafoons ({c})"
        )

        # self.removeWidget(self.itemAtPosition(self.rowCount() - 1, 0))  # FIXME... guess this doesn't work to remove the spacer row at the end
        self.setRowStretch(self.rowCount(), 1)

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

        report_layout = QGridLayout()

        player_lost_units = QGroupBox(f"{self.debriefing.player_country}'s lost units:")
        player_lost_units.setLayout(LossGrid(debriefing, player=True))
        report_layout.addWidget(player_lost_units, 0, 0)

        enemy_lost_units = QGroupBox(f"{self.debriefing.enemy_country}'s lost units:")
        enemy_lost_units.setLayout(LossGrid(debriefing, player=False))
        report_layout.addWidget(enemy_lost_units, 0, 1)

        layout.addLayout(report_layout)

        okay = QPushButton("Okay")
        okay.clicked.connect(self.close)
        layout.addWidget(okay)
