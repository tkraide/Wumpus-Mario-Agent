from __future__ import annotations

from dataclasses import dataclass

@dataclass(slots=True)
class WorldConfig:
    """
    Configuração do ambiente.

    Attributes
    ----------
    size:
        Tamanho do tabuleiro quadrado.
    pit_density:
        Fração aproximada de células com poços.
    ensure_safe_path:
        Garante pelo menos um caminho do início até a princesa,
        livre de Bowser e de poços.
    return_to_start_after_rescue:
        Se True, Mario precisa resgatar a princesa e voltar ao início.
    reveal_world_on_game_over:
        Se True, o renderer revela o mapa ao final do episódio.
    random_seed:
        Seed opcional de reprodutibilidade.
    """

    size: int = 4
    pit_density: float = 0.18
    ensure_safe_path: bool = True
    return_to_start_after_rescue: bool = False
    reveal_world_on_game_over: bool = True
    random_seed: int | None = None

    @property
    def max_pits(self) -> int:
        """Número padrão de poços em função do tamanho do mapa."""
        free_cells = self.size * self.size - 2  # início e princesa/Bowser
        raw = int(round(self.size * self.size * self.pit_density))
        return max(1, min(raw, max(1, free_cells // 3)))


@dataclass(slots=True)
class RenderConfig:
    """
    Configuração visual do app em Pygame.
    """

    window_width: int = 1200
    window_height: int = 800
    fps: int = 60
    board_margin: int = 36
    background_color: tuple[int, int, int] = (25, 30, 45)
    panel_color: tuple[int, int, int, int] = (18, 22, 30, 185)
    text_color: tuple[int, int, int] = (245, 245, 245)
    accent_color: tuple[int, int, int] = (245, 198, 70)
    danger_color: tuple[int, int, int] = (220, 80, 80)
    water_color: tuple[int, int, int] = (68, 132, 232)
    island_color: tuple[int, int, int] = (80, 182, 84)
    bridge_color: tuple[int, int, int] = (210, 188, 119)
