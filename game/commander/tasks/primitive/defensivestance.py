from __future__ import annotations

from game.commander.tasks.frontlinestancetask import FrontLineStanceTask
from game.ground_forces.combat_stance import CombatStance


class DefensiveStance(FrontLineStanceTask):
    @property
    def stance(self) -> CombatStance:
        return CombatStance.DEFENSIVE

    @property
    def have_sufficient_front_line_advantage(self) -> bool:
        return self.ground_force_balance >= 0.5
