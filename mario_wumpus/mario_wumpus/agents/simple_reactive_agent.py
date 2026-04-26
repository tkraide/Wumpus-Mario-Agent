from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept


class SimpleReactiveAgent(BaseAgent):
    """
    Estratégia:
    - se vê brilho, usa `GRAB`;
    - se sente fedor e ainda tem fireball, às vezes mira e sempre atira;
    - se sente fedor mas não tem fireball, ou sentir vento tenta voltar para baixo ou para esquerda(fugir do perigo);
    - se não sente nada, tenta ir para direita ou para cima.
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self._shoot_after_aim = False

    def reset(self) -> None:
        self._shoot_after_aim = False
        return None

    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        if self._shoot_after_aim:
            self._shoot_after_aim = False
            if percept.has_fireball:
                return Action.SHOOT
        
        if percept.glitter:
            return Action.RESCUE

        if percept.stink and percept.has_fireball:
            if self.rng.random() < 0.45:
                self._shoot_after_aim = True
                return Action.AIM_RIGHT if self.rng.random() < 0.22 else Action.AIM_UP
            return Action.SHOOT
        
        if (percept.stink and not percept.has_fireball) or percept.breeze:
            if self.rng.random() < 0.5:
                return Action.MOVE_DOWN
            else:
                return Action.MOVE_LEFT

        return self.rng.choice(
            [Action.MOVE_UP, Action.MOVE_RIGHT]
        )
