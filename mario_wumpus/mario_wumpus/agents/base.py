from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.actions import Action
from ..core.models import Percept


class BaseAgent(ABC):
    """
    Interface mínima para agentes.
    """

    def reset(self) -> None:
        """Hook opcional para reiniciar memória interna."""
        return None

    @abstractmethod
    def act(self, percept: Percept, legal_actions: list[Action]) -> Action:
        """
        Retorna a próxima ação.
        """
        raise NotImplementedError
