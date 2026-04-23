from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .actions import Action, Direction


@dataclass(frozen=True, slots=True)
class Position:
    """Posição 2D no tabuleiro."""

    row: int
    col: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.row, self.col)


@dataclass(slots=True)
class Percept:
    """
    Percepção parcial recebida pelo agente.

    O agente não recebe o mapa verdadeiro, apenas sinais locais e
    algumas variáveis de estado relevantes.
    """

    position: Position
    facing: Direction
    breeze: bool
    stink: bool
    glitter: bool
    bump: bool
    scream: bool
    rescued_princess: bool
    alive: bool
    has_fireball: bool
    visited: frozenset[tuple[int, int]] = frozenset()

    def as_dict(self) -> dict[str, Any]:
        return {
            "position": self.position.as_tuple(),
            "facing": self.facing.name,
            "breeze": self.breeze,
            "stink": self.stink,
            "glitter": self.glitter,
            "bump": self.bump,
            "scream": self.scream,
            "rescued_princess": self.rescued_princess,
            "alive": self.alive,
            "has_fireball": self.has_fireball,
            "visited": sorted(self.visited),
        }


@dataclass(slots=True)
class WorldState:
    """Estado verdadeiro do mundo."""

    size: int
    mario: Position
    mario_facing: Direction
    bowser: Position
    princess: Position
    pits: set[Position] = field(default_factory=set)
    visited: set[tuple[int, int]] = field(default_factory=set)
    bowser_alive: bool = True
    princess_rescued: bool = False
    alive: bool = True
    has_fireball: bool = True
    terminal: bool = False
    success: bool = False
    step_count: int = 0
    score: float = 0.0


@dataclass(slots=True)
class Transition:
    """
    Resultado de uma chamada a `env.step(...)`.
    """

    percept: Percept
    reward: float
    done: bool
    info: dict[str, Any]
    action: Action
