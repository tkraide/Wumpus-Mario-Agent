from __future__ import annotations

from enum import Enum, auto


class Direction(Enum):
    """Direções usadas por Mario para movimento e ataque."""

    UP = auto()
    RIGHT = auto()
    DOWN = auto()
    LEFT = auto()


class Action(Enum):
    """Conjunto de ações do agente."""

    MOVE_UP = auto()
    MOVE_RIGHT = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    AIM_UP = auto()
    AIM_RIGHT = auto()
    AIM_DOWN = auto()
    AIM_LEFT = auto()
    RESCUE = auto()
    SHOOT = auto()
    WAIT = auto()


MOVE_ACTION_TO_DIRECTION = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_RIGHT: Direction.RIGHT,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
}

AIM_ACTION_TO_DIRECTION = {
    Action.AIM_UP: Direction.UP,
    Action.AIM_RIGHT: Direction.RIGHT,
    Action.AIM_DOWN: Direction.DOWN,
    Action.AIM_LEFT: Direction.LEFT,
}

ACTION_TO_DIRECTION = {**MOVE_ACTION_TO_DIRECTION, **AIM_ACTION_TO_DIRECTION}
