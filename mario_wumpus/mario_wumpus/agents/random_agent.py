from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept


class RandomAgent(BaseAgent):
    """
    Agente baseline bem simples.

    - se houver brilho, tenta `RESCUE`;
    - caso contrário, escolhe aleatoriamente entre mover, esperar ou atirar.
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        print("Agente Aleatório!")
 
    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        if percept.glitter:
            return Action.RESCUE
        options = [
            Action.MOVE_UP,
            Action.MOVE_RIGHT,
            Action.MOVE_DOWN,
            Action.MOVE_LEFT,
            Action.WAIT,
        ]
        if percept.has_fireball:
            options.append(Action.SHOOT)
        return self.rng.choice(options)
