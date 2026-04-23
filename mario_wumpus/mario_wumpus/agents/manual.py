from __future__ import annotations

import pygame

from ..core.actions import Action

def key_to_move_action(key: int) -> Action | None:
    """
    Traduz teclas WASD para movimento.
    """
    if key == pygame.K_w:
        return Action.MOVE_UP
    if key == pygame.K_d:
        return Action.MOVE_RIGHT
    if key == pygame.K_s:
        return Action.MOVE_DOWN
    if key == pygame.K_a:
        return Action.MOVE_LEFT
    return None


def key_to_aim_action(key: int) -> Action | None:
    """
    Traduz as setas do teclado para ações de mira.
    """
    if key == pygame.K_UP:
        return Action.AIM_UP
    if key == pygame.K_RIGHT:
        return Action.AIM_RIGHT
    if key == pygame.K_DOWN:
        return Action.AIM_DOWN
    if key == pygame.K_LEFT:
        return Action.AIM_LEFT
    return None
