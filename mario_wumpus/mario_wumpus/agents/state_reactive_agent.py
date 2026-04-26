from __future__ import annotations

import random

from .base import BaseAgent
from ..core.actions import Action
from ..core.models import Percept


class StateReactiveAgent(BaseAgent):
    """
    Estratégia:
    - criar estados para guardar informações sobre o ambiente, como posições visitadas, seguras e possíveis perigosas;
    - atualizar o mapa mental com as novas informações do percept (mapeamento de segurança e registro de passos);
    Regras:
    - se vê brilho, usa Rescue;
    - Se sente stink e tem fireball, ele pode atirar. Ele pode cruzar as informações de onde sentiu fedor no passado para deduzir exatamente em qual célula o Bowser está, usar Action.AIM para virar para lá, e depois Action.SHOOT.
    - Olhar para as casas vizinhas e escolher para onde ir usando a seguinte prioridade:
        1. Casas seguras e não visitadas
        2. Casa vizinha que seja segura e já visitada(encontrar outro caminho).
        3. Casas possíveis de perigo (com base nos percepts anteriores)
        4. Nunca pisar em uma casa que não está na lista de self.seguras.
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.visitadas: set[tuple[int, int]] = set()
        self.seguras: set[tuple[int, int]] = set()
        self.possivel_perigo: set[tuple[int, int]] = set()
        self._stink_positions: set[tuple[int, int]] = set()
        self._pending_shot_after_aim = False
        self._last_move_attempt: Action | None = None
        self._min_row: int | None = 0
        self._max_row: int | None = None
        self._min_col: int | None = 0
        self._max_col: int | None = None

    def reset(self) -> None:
        self.visitadas.clear()
        self.seguras.clear()
        self.possivel_perigo.clear()
        self._stink_positions.clear()
        self._pending_shot_after_aim = False
        self._last_move_attempt = None
        self._min_row = 0
        self._max_row = None
        self._min_col = 0
        self._max_col = None
        return None

    def _adjacentes(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        row, col = pos
        return [(row - 1, col), (row, col + 1), (row + 1, col), (row, col - 1)]

    def _is_in_known_bounds(self, pos: tuple[int, int]) -> bool:
        row, col = pos
        if self._min_row is not None and row < self._min_row:
            return False
        if self._max_row is not None and row > self._max_row:
            return False
        if self._min_col is not None and col < self._min_col:
            return False
        if self._max_col is not None and col > self._max_col:
            return False
        return True

    def _acao_para_posicao(self, atual: tuple[int, int], alvo: tuple[int, int]) -> Action | None:
        ar, ac = atual
        tr, tc = alvo
        if tr == ar - 1 and tc == ac:
            return Action.MOVE_UP
        if tr == ar and tc == ac + 1:
            return Action.MOVE_RIGHT
        if tr == ar + 1 and tc == ac:
            return Action.MOVE_DOWN
        if tr == ar and tc == ac - 1:
            return Action.MOVE_LEFT
        return None

    def _aim_action_for(self, from_pos: tuple[int, int], to_pos: tuple[int, int]) -> Action | None:
        fr, fc = from_pos
        tr, tc = to_pos
        if tr == fr - 1 and tc == fc:
            return Action.AIM_UP
        if tr == fr and tc == fc + 1:
            return Action.AIM_RIGHT
        if tr == fr + 1 and tc == fc:
            return Action.AIM_DOWN
        if tr == fr and tc == fc - 1:
            return Action.AIM_LEFT
        return None

    def _registrar_borda_por_bump(self, pos_atual: tuple[int, int]) -> None:
        if self._last_move_attempt == Action.MOVE_UP:
            self._min_row = pos_atual[0]
        elif self._last_move_attempt == Action.MOVE_DOWN:
            self._max_row = pos_atual[0]
        elif self._last_move_attempt == Action.MOVE_RIGHT:
            self._max_col = pos_atual[1]
        elif self._last_move_attempt == Action.MOVE_LEFT:
            self._min_col = pos_atual[1]

    def _deduzir_celula_bowser(self) -> tuple[int, int] | None:
        candidatos: set[tuple[int, int]] | None = None
        for stink_pos in self._stink_positions:
            adj = set(self._adjacentes(stink_pos))
            adj = {p for p in adj if self._is_in_known_bounds(p)}
            candidatos = adj if candidatos is None else candidatos & adj

        if not candidatos:
            return None

        perigos_na_intersecao = [p for p in candidatos if p in self.possivel_perigo]
        if len(perigos_na_intersecao) == 1:
            return perigos_na_intersecao[0]

        if len(candidatos) == 1:
            return next(iter(candidatos))

        return None

    def _escolher_movimento_seguro(self, pos_atual: tuple[int, int]) -> Action | None:
        vizinhos = [p for p in self._adjacentes(pos_atual) if self._is_in_known_bounds(p)]

        nao_visitadas = [p for p in vizinhos if p in self.seguras and p not in self.visitadas]
        if nao_visitadas:
            alvo = self.rng.choice(nao_visitadas)
            return self._acao_para_posicao(pos_atual, alvo)

        revisitadas = [p for p in vizinhos if p in self.seguras and p in self.visitadas]
        if revisitadas:
            alvo = self.rng.choice(revisitadas)
            return self._acao_para_posicao(pos_atual, alvo)

        return None

    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        pos_atual = percept.position.as_tuple()

        if percept.bump:
            self._registrar_borda_por_bump(pos_atual)

        self.visitadas.add(pos_atual)
        self.seguras.add(pos_atual)
        self.possivel_perigo.discard(pos_atual)

        adjacentes = [p for p in self._adjacentes(pos_atual) if self._is_in_known_bounds(p)]
        if not percept.breeze and not percept.stink:
            for p in adjacentes:
                self.seguras.add(p)
                self.possivel_perigo.discard(p)
        else:
            for p in adjacentes:
                if p not in self.seguras:
                    self.possivel_perigo.add(p)

        if percept.stink:
            self._stink_positions.add(pos_atual)

        if percept.glitter:
            return Action.RESCUE

        if self._pending_shot_after_aim and percept.has_fireball:
            self._pending_shot_after_aim = False
            if Action.SHOOT in legal_actions:
                return Action.SHOOT

        if percept.stink and percept.has_fireball:
            bowser_pos = self._deduzir_celula_bowser()
            if bowser_pos is not None:
                aim_action = self._aim_action_for(pos_atual, bowser_pos)
                if aim_action is not None and aim_action in legal_actions:
                    self._pending_shot_after_aim = True
                    return aim_action
            if Action.SHOOT in legal_actions:
                return Action.SHOOT

        movimento_seguro = self._escolher_movimento_seguro(pos_atual)
        if movimento_seguro is not None and movimento_seguro in legal_actions:
            self._last_move_attempt = movimento_seguro
            return movimento_seguro

        self._last_move_attempt = None
        return Action.WAIT if Action.WAIT in legal_actions else self.rng.choice(legal_actions)
