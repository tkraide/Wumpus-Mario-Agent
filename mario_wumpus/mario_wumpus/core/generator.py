from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import random
from pathlib import Path

from ..config import WorldConfig
from .actions import Direction
from .models import Position, WorldState


@dataclass(slots=True)
class GeneratedLayout:
    """
    Layout gerado antes de virar um `WorldState`.
    """

    bowser: Position
    princess: Position
    pits: set[Position]
    safe_path: list[Position]


class WorldGenerator:
    """
    Gera mapas válidos para o ambiente.

    Regra: deve existir pelo menos um caminho do início até a princesa sem cair em poços.
    """

    def __init__(self, config: WorldConfig):
        self.config = config
        self.rng = random.Random(config.random_seed)

    def _start(self) -> Position:
        return Position(self.config.size - 1, 0)

    def _all_positions(self) -> list[Position]:
        n = self.config.size
        return [Position(r, c) for r in range(n) for c in range(n)]

    def _neighbors(self, pos: Position) -> list[Position]:
        n = self.config.size
        out: list[Position] = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = pos.row + dr, pos.col + dc
            if 0 <= rr < n and 0 <= cc < n:
                out.append(Position(rr, cc))
        return out

    def _random_safe_path(self, start: Position, target: Position) -> list[Position]:
        """
        Constrói um caminho Manhattan simples com ordem de eixos aleatória.
        """
        path = [start]
        current = start

        while current.row != target.row or current.col != target.col:
            moves: list[tuple[int, int]] = []
            if current.row < target.row:
                moves.append((1, 0))
            elif current.row > target.row:
                moves.append((-1, 0))
            if current.col < target.col:
                moves.append((0, 1))
            elif current.col > target.col:
                moves.append((0, -1))
            self.rng.shuffle(moves)
            dr, dc = moves[0]
            current = Position(current.row + dr, current.col + dc)
            path.append(current)
        return path

    def _is_reachable(
        self,
        start: Position,
        goal: Position,
        blocked: set[Position],
    ) -> bool:
        queue: deque[Position] = deque([start])
        seen = {start}
        while queue:
            current = queue.popleft()
            if current == goal:
                return True
            for nxt in self._neighbors(current):
                if nxt in blocked or nxt in seen:
                    continue
                seen.add(nxt)
                queue.append(nxt)
        return False

    def generate_layout(self) -> GeneratedLayout:
        """
        Gera layout aleatório respeitando as restrições de solvabilidade.
        """
        start = self._start()
        candidates = [p for p in self._all_positions() if p != start]
        princess = self.rng.choice(candidates)

        safe_path = self._random_safe_path(start, princess)
        safe_path_set = set(safe_path)

        bowser_candidates = [p for p in candidates if p != princess]
        if self.config.ensure_safe_path:
            bowser_candidates = [p for p in bowser_candidates if p not in safe_path_set]
            if not bowser_candidates:
                bowser_candidates = [p for p in candidates if p != princess]
        bowser = self.rng.choice(bowser_candidates)

        forbidden = {start, princess, bowser}
        pits: set[Position] = set()

        pit_candidates = [p for p in self._all_positions() if p not in forbidden]
        if self.config.ensure_safe_path:
            pit_candidates = [p for p in pit_candidates if p not in safe_path_set]

        self.rng.shuffle(pit_candidates)

        target_pits = self.config.max_pits
        for candidate in pit_candidates:
            if len(pits) >= target_pits:
                break
            test_blocked = set(pits)
            test_blocked.add(candidate)
            if self.config.ensure_safe_path:
                if not self._is_reachable(start, princess, test_blocked | {bowser}):
                    continue
            pits.add(candidate)

        return GeneratedLayout(
            bowser=bowser,
            princess=princess,
            pits=pits,
            safe_path=safe_path,
        )

    def build_state(self) -> WorldState:
        """
        Gera o estado inicial completo.
        """
        layout = self.generate_layout()
        start = self._start()
        state = WorldState(
            size=self.config.size,
            mario=start,
            mario_facing=Direction.RIGHT,
            bowser=layout.bowser,
            princess=layout.princess,
            pits=set(layout.pits),
        )
        state.visited.add(start.as_tuple())
        return state

    @staticmethod
    def load_state_from_json(path: str | Path) -> WorldState:
        """
        Carrega um estado inicial a partir de um arquivo JSON.

        Formato:
        {
          "size": 4,
          "bowser": [0, 2],
          "princess": [1, 3],
          "pits": [[1, 0], [2, 2]]
        }
        """
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        size = int(payload["size"])
        pits = {Position(int(r), int(c)) for r, c in payload.get("pits", [])}
        state = WorldState(
            size=size,
            mario=Position(size - 1, 0),
            mario_facing=Direction.RIGHT,
            bowser=Position(*payload["bowser"]),
            princess=Position(*payload["princess"]),
            pits=pits,
        )
        state.visited.add(state.mario.as_tuple())
        return state
