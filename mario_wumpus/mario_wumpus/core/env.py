from __future__ import annotations

from dataclasses import replace

from ..config import WorldConfig
from .actions import ACTION_TO_DIRECTION, AIM_ACTION_TO_DIRECTION, MOVE_ACTION_TO_DIRECTION, Action, Direction
from .generator import WorldGenerator
from .models import Percept, Position, Transition, WorldState


class WumpusEnv:
    """
    Motor do ambiente.

    Regras principais:
    - Mario começa no canto inferior esquerdo.
    - Se entrar em poço, morre.
    - Se entrar na célula de Bowser enquanto Bowser estiver vivo, morre.
    - `RESCUE` resgata a princesa quando Mario está na mesma célula.
    - `SHOOT` dispara uma fireball na direção atual.
    """

    def __init__(self, config: WorldConfig | None = None):
        self.config = config or WorldConfig()
        self.generator = WorldGenerator(self.config)
        self.state: WorldState | None = None
        self._last_bump = False
        self._last_scream = False
        self._safe_path: list[Position] = []

    def reset(self, seed: int | None = None, state: WorldState | None = None) -> Percept:
        """
        Reinicia o episódio.

        Parameters
        ----------
        seed:
            Seed opcional para regenerar o gerador.
        state:
            Estado pronto, em caso de mapas fixos.
        """
        if seed is not None:
            self.config.random_seed = seed
            self.generator = WorldGenerator(self.config)

        if state is None:
            layout = self.generator.generate_layout()
            self._safe_path = list(layout.safe_path)
            self.state = WorldState(
                size=self.config.size,
                mario=Position(self.config.size - 1, 0),
                mario_facing=Direction.RIGHT,
                bowser=layout.bowser,
                princess=layout.princess,
                pits=set(layout.pits),
            )
        else:
            self.state = state
            self._safe_path = []

        self.state.visited.add(self.state.mario.as_tuple())
        self._last_bump = False
        self._last_scream = False
        return self.get_percept()

    @property
    def legal_actions(self) -> list[Action]:
        """
        Conjunto de ações aceitas em qualquer passo.
        """
        return list(Action)

    def clone_state(self) -> WorldState:
        """
        Retorna uma cópia rasa dos estados.
        """
        if self.state is None:
            raise RuntimeError("Environment not reset.")
        return replace(
            self.state,
            pits=set(self.state.pits),
            visited=set(self.state.visited),
        )

    def get_percept(self) -> Percept:
        """
        Monta a percepção local a partir do estado verdadeiro.
        """
        if self.state is None:
            raise RuntimeError("Environment not reset.")

        state = self.state
        breeze = any(n in state.pits for n in self.neighbors(state.mario))
        stink = state.bowser_alive and any(n == state.bowser for n in self.neighbors(state.mario))
        glitter = (state.mario == state.princess) and not state.princess_rescued

        return Percept(
            position=state.mario,
            facing=state.mario_facing,
            breeze=breeze,
            stink=stink,
            glitter=glitter,
            bump=self._last_bump,
            scream=self._last_scream,
            rescued_princess=state.princess_rescued,
            alive=state.alive,
            has_fireball=state.has_fireball,
            visited=frozenset(state.visited),
        )

    def in_bounds(self, pos: Position) -> bool:
        """
        Verifica limites do tabuleiro.
        """
        if self.state is None:
            raise RuntimeError("Environment not reset.")
        return 0 <= pos.row < self.state.size and 0 <= pos.col < self.state.size

    def neighbors(self, pos: Position) -> list[Position]:
        """
        Vizinhança ortogonal da posição.
        """
        if self.state is None:
            raise RuntimeError("Environment not reset.")
        out: list[Position] = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = Position(pos.row + dr, pos.col + dc)
            if self.in_bounds(nxt):
                out.append(nxt)
        return out

    def _move_target(self, action: Action) -> Position:
        assert self.state is not None
        drdc = {
            Action.MOVE_UP: (-1, 0),
            Action.MOVE_RIGHT: (0, 1),
            Action.MOVE_DOWN: (1, 0),
            Action.MOVE_LEFT: (0, -1),
        }
        dr, dc = drdc[action]
        return Position(self.state.mario.row + dr, self.state.mario.col + dc)

    def _bowser_line_hit(self) -> tuple[bool, list[tuple[int, int]]]:
        """
        Verifica se a fireball atinge Bowser e devolve o traçado percorrido.
        """
        assert self.state is not None
        drdc = {
            Direction.UP: (-1, 0),
            Direction.RIGHT: (0, 1),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
        }
        dr, dc = drdc[self.state.mario_facing]
        current = self.state.mario
        ray: list[tuple[int, int]] = []
        while True:
            current = Position(current.row + dr, current.col + dc)
            if not self.in_bounds(current):
                break
            ray.append(current.as_tuple())
            if current == self.state.bowser and self.state.bowser_alive:
                return True, ray
        return False, ray

    def _apply_hazards(self) -> None:
        """
        Verifica morte por poço ou Bowser.
        """
        assert self.state is not None
        if self.state.mario in self.state.pits:
            self.state.alive = False
            self.state.terminal = True
            self.state.success = False
            return
        if self.state.bowser_alive and self.state.mario == self.state.bowser:
            self.state.alive = False
            self.state.terminal = True
            self.state.success = False

    def _check_victory(self) -> None:
        """
        Atualiza condição de sucesso.
        """
        assert self.state is not None
        if not self.state.princess_rescued:
            return
        if self.config.return_to_start_after_rescue:
            if self.state.mario == Position(self.state.size - 1, 0):
                self.state.terminal = True
                self.state.success = True
        else:
            self.state.terminal = True
            self.state.success = True

    def step(self, action: Action) -> Transition:
        """
        Aplica uma ação no ambiente.
        """
        if self.state is None:
            raise RuntimeError("Environment not reset.")
        if self.state.terminal:
            return Transition(
                percept=self.get_percept(),
                reward=0.0,
                done=True,
                info={"message": "Episode already finished."},
                action=action,
            )

        self._last_bump = False
        self._last_scream = False
        self.state.step_count += 1

        reward = -1.0
        info: dict[str, object] = {
            "fireball_path": [],
            "safe_path": [p.as_tuple() for p in self._safe_path],
        }

        if action in MOVE_ACTION_TO_DIRECTION:
            self.state.mario_facing = MOVE_ACTION_TO_DIRECTION[action]
            target = self._move_target(action)
            if self.in_bounds(target):
                self.state.mario = target
                self.state.visited.add(target.as_tuple())
            else:
                self._last_bump = True
                reward -= 2.0

        elif action in AIM_ACTION_TO_DIRECTION:
            self.state.mario_facing = AIM_ACTION_TO_DIRECTION[action]
            reward -= 0.15

        elif action == Action.SHOOT:
            if not self.state.has_fireball:
                reward -= 4.0
            else:
                self.state.has_fireball = False
                hit, ray = self._bowser_line_hit()
                info["fireball_path"] = ray
                if hit:
                    self.state.bowser_alive = False
                    self._last_scream = True
                    reward += 30.0
                else:
                    reward -= 5.0

        elif action == Action.RESCUE:
            if self.state.mario == self.state.princess and not self.state.princess_rescued:
                self.state.princess_rescued = True
                reward += 150.0
            else:
                reward -= 2.0

        elif action == Action.WAIT:
            reward -= 0.5

        self._apply_hazards()
        if not self.state.alive:
            reward -= 120.0

        self._check_victory()
        if self.state.success:
            reward += 200.0

        self.state.score += reward
        percept = self.get_percept()
        info.update(
            {
                "alive": self.state.alive,
                "success": self.state.success,
                "score": self.state.score,
                "bowser_alive": self.state.bowser_alive,
                "princess_rescued": self.state.princess_rescued,
            }
        )

        return Transition(
            percept=percept,
            reward=reward,
            done=self.state.terminal,
            info=info,
            action=action,
        )
