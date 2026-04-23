from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept


class GreedyAgent(BaseAgent):
    """
    Agente heurístico demonstrativo.

    Estratégia:
    - se vê brilho, usa `GRAB`;
    - se sente fedor e ainda tem fireball, às vezes atira;
    - prefere movimentos para células ainda não visitadas;
    - evita `WAIT`.

    Este agente não é ótimo nem completo;
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def reset(self) -> None:
        return None

    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        if percept.glitter:
            return Action.RESCUE

        if percept.stink and percept.has_fireball and self.rng.random() < 0.45:
            return Action.SHOOT

        row, col = percept.position.as_tuple()
        candidates = [
            (Action.MOVE_UP, (row - 1, col)),
            (Action.MOVE_RIGHT, (row, col + 1)),
            (Action.MOVE_DOWN, (row + 1, col)),
            (Action.MOVE_LEFT, (row, col - 1)),
        ]

        unseen = [act for act, pos in candidates if pos not in percept.visited]
        if unseen:
            return self.rng.choice(unseen)

        return self.rng.choice(
            [Action.MOVE_UP, Action.MOVE_RIGHT, Action.MOVE_DOWN, Action.MOVE_LEFT]
        )
