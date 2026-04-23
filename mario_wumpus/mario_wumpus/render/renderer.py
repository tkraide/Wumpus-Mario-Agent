from __future__ import annotations

from dataclasses import dataclass
import math
import random
import time

import pygame

from ..config import RenderConfig
from ..core.actions import Direction
from ..core.models import Percept, Position, Transition, WorldState
from .assets import AssetManager
from .ui import Button, draw_text


@dataclass(slots=True)
class FireballEffect:
    """
    Efeito visual curto para o ataque do Mario.
    """

    path: list[tuple[int, int]]
    created_at: float
    duration: float = 0.85

    def is_alive(self, now: float) -> bool:
        return (now - self.created_at) <= self.duration


class GameRenderer:
    """
    Renderer principal da partida.
    """

    def __init__(self, screen: pygame.Surface, assets: AssetManager, render_cfg: RenderConfig):
        self.screen = screen
        self.assets = assets
        self.render_cfg = render_cfg
        self.font_title = pygame.font.SysFont("arial", 34, bold=True)
        self.font_ui = pygame.font.SysFont("arial", 24)
        self.font_small = pygame.font.SysFont("arial", 18)
        self.show_full_world = False
        self.effects: list[FireballEffect] = []
        self._board_signature: tuple | None = None
        self._board_island_variants: dict[tuple[int, int], str] = {}
        self._island_asset_names = [
            "island_variant_1.png",
            "island_variant_2.png",
            "island_variant_3.png",
        ]

    def board_rect(self) -> pygame.Rect:
        """
        Região reservada ao tabuleiro.
        """
        width, height = self.screen.get_size()
        margin = self.render_cfg.board_margin
        left_width = int(width * 0.72)
        return pygame.Rect(margin, margin, left_width - 2 * margin, height - 2 * margin)

    def grid_rect(self, size: int) -> pygame.Rect:
        """
        Região efetiva usada pelo grid.
        """
        return self.board_rect()

    def hud_rect(self) -> pygame.Rect:
        """
        Região lateral de HUD.
        """
        width, height = self.screen.get_size()
        margin = self.render_cfg.board_margin
        board = self.board_rect()
        x = board.right + margin
        return pygame.Rect(x, margin, width - x - margin, height - 2 * margin)

    def cell_rect(self, size: int, row: int, col: int) -> pygame.Rect:
        """
        Retângulo de uma célula no tabuleiro.
        """
        board = self.grid_rect(size)
        cell_w = board.width / size
        cell_h = board.height / size
        return pygame.Rect(
            int(board.x + col * cell_w),
            int(board.y + row * cell_h),
            int(math.ceil(cell_w)),
            int(math.ceil(cell_h)),
        )

    def _entity_anchor(self, board_size: int, cell: pygame.Rect) -> tuple[int, int]:
        """
        Ponto-base onde entidades "pisam" sobre a ilha.
        """
        island_top = self._island_top_rect(cell)
        return (island_top.centerx, island_top.centery + max(4, island_top.height // 5))

    def handle_transition(self, transition: Transition) -> None:
        """
        Atualiza efeitos visuais a partir de uma transição.
        """
        path = transition.info.get("fireball_path", [])
        if path:
            self.effects.append(FireballEffect(path=list(path), created_at=time.time()))

    def render(
        self,
        state: WorldState,
        percept: Percept,
        last_transition: Transition | None = None,
        agent_name: str = "Manual",
        game_over_reveal: bool = True,
    ) -> None:
        """
        Renderiza o frame inteiro da partida.
        """
        self.screen.fill(self.render_cfg.background_color)
        self._ensure_board_art(state)
        self._draw_board_background(state)
        reveal = self.show_full_world or (game_over_reveal and state.terminal)

        self._draw_grid(state.size)
        self._draw_cells(state, percept, reveal=reveal)
        self._draw_hud(state, percept, agent_name)
        self._draw_effects(state)
        pygame.display.flip()

    def _draw_board_background(self, state: WorldState) -> None:
        """
        Fundo do tabuleiro com água, pontes e ilhas em arte.
        """
        board = self.board_rect()
        self._draw_procedural_board(state.size, board)
        pygame.draw.rect(self.screen, (255, 255, 255), board, width=2, border_radius=24)

    def _draw_procedural_board(self, size: int, rect: pygame.Rect) -> None:
        """
        Desenha água, ilhas e corredores entre ilhas.
        """
        pygame.draw.rect(self.screen, self.render_cfg.water_color, rect, border_radius=24)

        for row in range(size):
            for col in range(size):
                cell = self.cell_rect(size, row, col)
                if col + 1 < size:
                    self._draw_bridge_between_cells(cell, self.cell_rect(size, row, col + 1), horizontal=True)
                if row + 1 < size:
                    self._draw_bridge_between_cells(cell, self.cell_rect(size, row + 1, col), horizontal=False)

        for row in range(size):
            for col in range(size):
                cell = self.cell_rect(size, row, col)
                self._draw_island(size, row, col, cell)

    def _board_state_signature(self, state: WorldState) -> tuple:
        pits = tuple(sorted((pit.row, pit.col) for pit in state.pits))
        return (
            state.size,
            (state.bowser.row, state.bowser.col),
            (state.princess.row, state.princess.col),
            pits,
        )

    def _ensure_board_art(self, state: WorldState) -> None:
        signature = self._board_state_signature(state)
        if signature == self._board_signature:
            return
        rng = random.Random(repr(signature))
        self._board_island_variants = {}
        for row in range(state.size):
            for col in range(state.size):
                self._board_island_variants[(row, col)] = rng.choice(self._island_asset_names)
        self._board_signature = signature

    def _island_sprite_rect(self, cell: pygame.Rect) -> pygame.Rect:
        max_width = int(cell.width * 0.94)
        max_height = int(cell.height * 0.68)
        src_w, src_h = self.assets.source_size("island_variant_1.png")
        scale = min(max_width / src_w, max_height / src_h)
        width = max(48, int(src_w * scale))
        height = max(24, int(src_h * scale))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (cell.centerx, cell.centery + int(cell.height * 0.08))
        return rect

    def _island_base_rect(self, cell: pygame.Rect) -> pygame.Rect:
        sprite = self._island_sprite_rect(cell)
        width = max(30, int(sprite.width * 0.50))
        height = max(18, int(sprite.height * 0.16))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (sprite.centerx, sprite.top + int(sprite.height * 0.57))
        return rect

    def _island_top_rect(self, cell: pygame.Rect) -> pygame.Rect:
        sprite = self._island_sprite_rect(cell)
        width = max(34, int(sprite.width * 0.50))
        height = max(16, int(sprite.height * 0.18))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (sprite.centerx, sprite.top + int(sprite.height * 0.36))
        return rect

    def _draw_bridge_between_cells(self, src_cell: pygame.Rect, dst_cell: pygame.Rect, horizontal: bool) -> None:
        """
        Desenha a ponte com sprite dedicado, mantendo conexão entre bordas das ilhas.
        """
        src_top = self._island_top_rect(src_cell)
        dst_top = self._island_top_rect(dst_cell)

        if self.assets.exists("bridge.png"):
            if horizontal:
                y = src_top.centery
                left = src_top.right - max(2, src_top.width // 18)
                right = dst_top.left + max(2, dst_top.width // 18)
                width = max(24, right - left)
                height = max(18, int(min(src_cell.height, dst_cell.height) * 0.20))
                surf = self.assets.load_surface("bridge.png", trim=True)
                surf = pygame.transform.rotate(surf, -90)
                surf = pygame.transform.smoothscale(surf, (width, height))
                rect = surf.get_rect(center=((left + right) // 2, y))
            else:
                x = src_top.centerx
                top = src_top.bottom - max(2, src_top.height // 12)
                bottom = dst_top.top + max(2, dst_top.height // 12)
                width = max(18, int(min(src_cell.width, dst_cell.width) * 0.20))
                height = max(24, bottom - top)
                surf = self.assets.load_surface("bridge.png", trim=True, size=(width, height))
                rect = surf.get_rect(center=(x, (top + bottom) // 2))
            self.screen.blit(surf, rect)
            return

        border = (118, 88, 52)
        fill = self.render_cfg.bridge_color
        if horizontal:
            y = src_top.centery
            left = src_top.right - 2
            right = dst_top.left + 2
            h = max(8, int(min(src_cell.height, dst_cell.height) * 0.08))
            rect = pygame.Rect(left, y - h // 2, max(8, right - left), h)
        else:
            x = src_top.centerx
            top = src_top.bottom - 2
            bottom = dst_top.top + 2
            w = max(8, int(min(src_cell.width, dst_cell.width) * 0.08))
            rect = pygame.Rect(x - w // 2, top, w, max(8, bottom - top))
        pygame.draw.rect(self.screen, border, rect.inflate(4, 4), border_radius=max(4, rect.height // 2, rect.width // 2))
        pygame.draw.rect(self.screen, fill, rect, border_radius=max(4, rect.height // 2, rect.width // 2))

    def _draw_island(self, board_size: int, row: int, col: int, cell: pygame.Rect) -> None:
        """
        Desenha a ilha usando uma das variantes em PNG.
        """
        sprite_rect = self._island_sprite_rect(cell)
        shadow_rect = sprite_rect.inflate(-max(10, sprite_rect.width // 7), -max(28, sprite_rect.height // 4))
        shadow_rect.move_ip(0, max(4, cell.height // 24))
        shadow = pygame.Surface((shadow_rect.width + 10, shadow_rect.height + 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (18, 34, 52, 88), shadow.get_rect().inflate(-10, -10))
        self.screen.blit(shadow, (shadow_rect.x - 5, shadow_rect.y - 5))

        asset_name = self._board_island_variants.get((row, col), self._island_asset_names[0])
        surf = self.assets.load_surface(asset_name, size=sprite_rect.size)
        self.screen.blit(surf, sprite_rect)

    def _draw_grid(self, size: int) -> None:
        """
        Grade sutil para leitura do tabuleiro.
        """
        for row in range(size):
            for col in range(size):
                cell = self.cell_rect(size, row, col)
                pygame.draw.rect(self.screen, (20, 20, 28), cell, width=1, border_radius=4)

    def _draw_cells(self, state: WorldState, percept: Percept, reveal: bool) -> None:
        """
        Desenha entidades e overlays do mapa.
        """
        size = state.size

        current_pos = (state.mario.row, state.mario.col)
        for row, col in state.visited:
            cell = self.cell_rect(size, row, col)
            island = self._island_top_rect(cell).inflate(24, 16)

            overlay = pygame.Surface((cell.width, cell.height), pygame.SRCALPHA)
            overlay.fill((255, 248, 185, 28))
            self.screen.blit(overlay, cell.topleft)

            glow = pygame.Surface((island.width + 14, island.height + 14), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 235, 140, 72), glow.get_rect().inflate(-8, -8))
            self.screen.blit(glow, glow.get_rect(center=island.center))

            pygame.draw.rect(self.screen, (255, 244, 180), cell, width=2, border_radius=8)
            pygame.draw.ellipse(self.screen, (250, 238, 150), island, width=3)

            if (row, col) != current_pos:
                marker_r = max(4, min(cell.width, cell.height) // 18)
                marker_center = (cell.left + max(12, cell.width // 7), cell.top + max(12, cell.height // 7))
                pygame.draw.circle(self.screen, (255, 232, 120), marker_center, marker_r)
                pygame.draw.circle(self.screen, (150, 110, 35), marker_center, marker_r, width=1)

        if reveal:
            for pit in state.pits:
                self._draw_pit(state.size, pit.row, pit.col)
            if state.bowser_alive:
                self._draw_bowser(state.size, state.bowser.row, state.bowser.col)
            if not state.princess_rescued:
                princess_pos = (state.princess.row, state.princess.col)
                if princess_pos != current_pos:
                    princess_cell = self.cell_rect(size, state.princess.row, state.princess.col)
                    self._draw_cell_badges(princess_cell, ["star.png"])
                self._draw_princess(state.size, state.princess.row, state.princess.col)

        self._draw_current_percepts(state, percept)
        self._draw_mario(state)
        self._draw_aim_indicator_on_cell(state)

        if state.princess_rescued:
            self._draw_rescued_princess_with_mario(state)

    def _draw_current_percepts(self, state: WorldState, percept: Percept) -> None:
        """
        Desenha ícones de brisa, fedor e estrela sem sobreposição.
        """
        cell = self.cell_rect(state.size, percept.position.row, percept.position.col)
        icons: list[str] = []
        if percept.breeze:
            icons.append("breeze.png")
        if percept.stink:
            icons.append("stink.png")
        if percept.glitter:
            icons.append("star.png")
        self._draw_cell_badges(cell, icons)

    def _draw_cell_badges(self, cell: pygame.Rect, asset_names: list[str]) -> None:
        """
        Distribui até três ícones em posições fixas da célula.
        """
        if not asset_names:
            return

        slot_centers = [
            (cell.left + int(cell.width * 0.18), cell.top + int(cell.height * 0.18)),
            (cell.right - int(cell.width * 0.18), cell.top + int(cell.height * 0.18)),
            (cell.right - int(cell.width * 0.18), cell.bottom - int(cell.height * 0.18)),
            (cell.left + int(cell.width * 0.18), cell.bottom - int(cell.height * 0.18)),
        ]
        n = min(len(asset_names), len(slot_centers))
        icon_box = max(21, min(64, int(min(cell.width, cell.height) * (0.26 if n <= 2 else 0.22))))

        for idx, asset_name in enumerate(asset_names[:len(slot_centers)]):
            center = slot_centers[idx]
            shadow = pygame.Surface((icon_box + 16, icon_box + 16), pygame.SRCALPHA)
            pygame.draw.circle(
                shadow,
                (10, 14, 20, 78),
                shadow.get_rect().center,
                max(12, icon_box // 2),
            )
            self.screen.blit(shadow, shadow.get_rect(center=(center[0], center[1] + 2)))

            icon = self._fit_surface_within(asset_name, icon_box, icon_box)
            self.screen.blit(icon, icon.get_rect(center=center))

    def _fit_surface_within(self, asset_name: str, max_w: int, max_h: int) -> pygame.Surface:
        """
        Carrega um asset preservando a razão de aspecto dentro da caixa dada.
        """
        base = self.assets.load_surface(asset_name, trim=True)
        base_w = max(1, base.get_width())
        base_h = max(1, base.get_height())
        scale = min(max_w / base_w, max_h / base_h)
        draw_w = max(8, int(base_w * scale))
        draw_h = max(8, int(base_h * scale))
        return pygame.transform.smoothscale(base, (draw_w, draw_h))

    def _draw_pit(self, board_size: int, row: int, col: int) -> None:
        """
        Desenha a versão de ilha com poço
        """
        cell = self.cell_rect(board_size, row, col)
        sprite_rect = self._island_sprite_rect(cell)
        surf = self.assets.load_surface("pit_island.png", size=sprite_rect.size)
        self.screen.blit(surf, sprite_rect)

    def _draw_bowser(self, board_size: int, row: int, col: int) -> None:
        """
        Desenha Bowser animado.
        """
        cell = self.cell_rect(board_size, row, col)
        anchor_x, anchor_y = self._entity_anchor(board_size, cell)
        surf = self.assets.load_animation(
            "bowser.gif",
            size=(max(36, int(cell.width * 0.48)), max(36, int(cell.height * 0.44))),
            frame_time=0.12,
        ).frame_at(time.time())
        rect = surf.get_rect(midbottom=(anchor_x, anchor_y))
        self.screen.blit(surf, rect)

    def _draw_princess(self, board_size: int, row: int, col: int) -> None:
        """
        Desenha a princesa animada.
        """
        cell = self.cell_rect(board_size, row, col)
        anchor_x, anchor_y = self._entity_anchor(board_size, cell)
        surf = self.assets.load_animation(
            "princesa.gif",
            size=(max(30, int(cell.width * 0.34)), max(42, int(cell.height * 0.40))),
            frame_time=0.10,
        ).frame_at(time.time())
        rect = surf.get_rect(midbottom=(anchor_x, anchor_y))
        self.screen.blit(surf, rect)

    def _draw_mario(self, state: WorldState) -> None:
        """
        Desenha Mario com sprite coerente com a direção atual.
        """
        cell = self.cell_rect(state.size, state.mario.row, state.mario.col)
        anchor_x, anchor_y = self._entity_anchor(state.size, cell)

        if state.mario_facing == Direction.LEFT:
            anim = self.assets.load_animation(
                "MarioEsquerda.gif",
                size=(max(28, int(cell.width * 0.30)), max(36, int(cell.height * 0.38))),
                frame_time=0.08,
            )
        else:
            anim = self.assets.load_animation(
                "MarioDireita.gif",
                size=(max(28, int(cell.width * 0.30)), max(36, int(cell.height * 0.38))),
                frame_time=0.08,
            )

        surf = anim.frame_at(time.time())
        rect = surf.get_rect(midbottom=(anchor_x, anchor_y))
        self.screen.blit(surf, rect)

    def _draw_aim_indicator_on_cell(self, state: WorldState) -> None:
        """
        Mostra a direção de mira usando o ícone de espada.
        """
        cell = self.cell_rect(state.size, state.mario.row, state.mario.col)
        icon_box = max(20, min(33, int(min(cell.width, cell.height) * 0.18)))
        target_w = icon_box
        target_h = icon_box

        #
        #target_w = max(34, min(42, int(cell.width * 0.34)))
        #target_h = max(20, min(33, int(cell.height * 0.20)))

        base = self.assets.load_surface("sword.png", trim=True)
        base_ratio = max(1e-6, base.get_width() / max(1, base.get_height()))
        draw_w = target_w
        draw_h = max(10, int(draw_w / base_ratio))
        if draw_h > target_h:
            draw_h = target_h
            draw_w = max(10, int(draw_h * base_ratio))
        surf = pygame.transform.smoothscale(base, (draw_w, draw_h))
        
        angle = {
            Direction.RIGHT: 0,
            Direction.LEFT: 180,
            Direction.UP: 90,
            Direction.DOWN: -90,
        }[state.mario_facing]
        surf = pygame.transform.rotate(surf, angle)

        bg_size = max(surf.get_width(), surf.get_height()) + 14
        
        bg = pygame.Surface((bg_size, bg_size), pygame.SRCALPHA)
        pygame.draw.circle(bg, (20, 24, 30, 140), bg.get_rect().center, bg_size // 2)
        target_center = (
            cell.left + max(18, cell.width // 6),
            cell.bottom - max(18, cell.height // 6),
        )
        self.screen.blit(bg, bg.get_rect(center=target_center))
        self.screen.blit(surf, surf.get_rect(center=target_center))

    def _draw_rescued_princess_with_mario(self, state: WorldState) -> None:
        """
        Após o resgate, desenha a princesa ao lado do Mario.
        """
        cell = self.cell_rect(state.size, state.mario.row, state.mario.col)
        anchor_x, anchor_y = self._entity_anchor(state.size, cell)
        surf = self.assets.load_animation(
            "princesa.gif",
            size=(max(24, int(cell.width * 0.28)), max(34, int(cell.height * 0.32))),
            frame_time=0.10,
        ).frame_at(time.time())

        horizontal = int(cell.width * 0.16)
        if state.mario_facing == Direction.LEFT:
            x = anchor_x + horizontal
        else:
            x = anchor_x - horizontal
        y = anchor_y - int(cell.height * 0.02)
        rect = surf.get_rect(midbottom=(x, y))
        self.screen.blit(surf, rect)

    def _draw_effects(self, state: WorldState) -> None:
        """
        Efeito visual da fireball.
        """
        now = time.time()
        alive_effects: list[FireballEffect] = []
        for effect in self.effects:
            if not effect.is_alive(now):
                continue
            alive_effects.append(effect)
            progress = min(0.999, (now - effect.created_at) / effect.duration)
            if not effect.path:
                continue
            idx = min(len(effect.path) - 1, int(progress * len(effect.path)))
            row, col = effect.path[idx]
            cell = self.cell_rect(state.size, row, col)
            surf = self.assets.load_animation(
                "mario_fireBall.gif",
                size=(max(28, int(cell.width * 0.26)), max(28, int(cell.height * 0.26))),
                frame_time=0.05,
            ).frame_at(now)
            rect = surf.get_rect(center=(cell.centerx, cell.top + int(cell.height * 0.44)))
            glow = pygame.Surface((rect.width + 10, rect.height + 10), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 170, 60, 90), glow.get_rect().center, glow.get_width() // 2)
            self.screen.blit(glow, glow.get_rect(center=rect.center))
            self.screen.blit(surf, rect)
        self.effects = alive_effects

    def _draw_hud(self, state: WorldState, percept: Percept, agent_name: str) -> None:
        """
        Painel lateral com informações da partida.
        """
        panel = self.hud_rect()
        overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        overlay.fill(self.render_cfg.panel_color)
        self.screen.blit(overlay, panel.topleft)
        pygame.draw.rect(self.screen, (255, 255, 255), panel, width=2, border_radius=18)

        x = panel.x + 18
        y = panel.y + 18
        draw_text(self.screen, self.font_title, "Mario Wumpus", self.render_cfg.text_color, x, y)
        y += 48
        draw_text(self.screen, self.font_ui, f"Agente: {agent_name}", self.render_cfg.text_color, x, y)
        y += 36
        draw_text(self.screen, self.font_ui, f"Mapa: {state.size} x {state.size}", self.render_cfg.text_color, x, y)
        y += 36
        draw_text(self.screen, self.font_ui, f"Passos: {state.step_count}", self.render_cfg.text_color, x, y)
        y += 36
        draw_text(self.screen, self.font_ui, f"Score: {state.score:.1f}", self.render_cfg.text_color, x, y)

        y += 52
        draw_text(self.screen, self.font_ui, "Percepções", self.render_cfg.accent_color, x, y)
        y += 36
        for label, value in [
            ("Brisa", percept.breeze),
            ("Fedor", percept.stink),
            ("Brilho", percept.glitter),
            ("Colisão", percept.bump),
            ("Grito", percept.scream),
            ("Fireball", percept.has_fireball),
        ]:
            color = (100, 220, 120) if value else (210, 210, 210)
            draw_text(self.screen, self.font_ui, f"{label}: {'SIM' if value else 'não'}", color, x, y)
            y += 32

        y += 24
        draw_text(self.screen, self.font_ui, "Controles", self.render_cfg.accent_color, x, y)
        y += 34
        controls = [
            "WASD: mover",
            "Setas: mirar",
            "F: espada / ataque",
            "SPACE: resgatar",
            "TAB: revelar mapa",
            "R: reiniciar",
            "ESC: menu",
        ]
        for line in controls:
            draw_text(self.screen, self.font_small, line, self.render_cfg.text_color, x, y)
            y += 24

        y += 18
        if state.terminal:
            if state.success:
                msg = "Vitória: princesa resgatada"
                color = (110, 220, 120)
            else:
                msg = "Fim de jogo"
                color = self.render_cfg.danger_color
            draw_text(self.screen, self.font_ui, msg, color, x, y)
        else:
            status = "Bowser vivo" if state.bowser_alive else "Bowser derrotado"
            draw_text(self.screen, self.font_ui, status, self.render_cfg.text_color, x, y)



class MenuRenderer:
    """
    Tela inicial
    """

    def __init__(self, screen: pygame.Surface, assets: AssetManager, render_cfg: RenderConfig):
        self.screen = screen
        self.assets = assets
        self.render_cfg = render_cfg
        self.font_title = pygame.font.SysFont("arial", 38, bold=True)
        self.font_ui = pygame.font.SysFont("arial", 28)
        self.font_small = pygame.font.SysFont("arial", 20)

    def draw(
        self,
        size: int,
        hovered: str | None,
        buttons: dict[str, Button],
    ) -> None:
        """
        Renderiza o menu principal.
        """
        bg = self.assets.load_surface("fundo.png", size=self.screen.get_size(), alpha=True)
        self.screen.blit(bg, (0, 0))

        width, height = self.screen.get_size()
        panel = pygame.Rect(width // 2 - 250, int(height * 0.44), 500, 330)
        overlay = pygame.Surface(panel.size, pygame.SRCALPHA)
        overlay.fill((15, 20, 30, 170))
        self.screen.blit(overlay, panel.topleft)
        pygame.draw.rect(self.screen, (255, 255, 255), panel, width=2, border_radius=18)

        draw_text(
            self.screen,
            self.font_title,
            "Menu",
            (255, 255, 255),
            panel.centerx,
            panel.y + 34,
            center=True,
        )
        draw_text(
            self.screen,
            self.font_ui,
            f"Tamanho do mapa: {size} x {size}",
            (245, 245, 245),
            panel.centerx,
            panel.y + 85,
            center=True,
        )
        

        for name, button in buttons.items():
            button.draw(self.screen, self.font_ui, hovered == name)

        pygame.display.flip()
