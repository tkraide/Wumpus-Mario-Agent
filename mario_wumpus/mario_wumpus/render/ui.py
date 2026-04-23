from __future__ import annotations

from dataclasses import dataclass
import pygame


@dataclass(slots=True)
class Button:
    rect: pygame.Rect
    text: str
    fill: tuple[int, int, int]
    hover_fill: tuple[int, int, int]
    text_color: tuple[int, int, int] = (245, 245, 245)
    radius: int = 14

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, hovered: bool) -> None:
        color = self.hover_fill if hovered else self.fill
        pygame.draw.rect(surface, color, self.rect, border_radius=self.radius)
        label = font.render(self.text, True, self.text_color)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    x: int,
    y: int,
    center: bool = False,
) -> pygame.Rect:
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(rendered, rect)
    return rect
