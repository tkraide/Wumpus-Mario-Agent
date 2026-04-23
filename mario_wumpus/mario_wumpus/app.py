from __future__ import annotations

from pathlib import Path
import time

import pygame

from .agents.random_agent import RandomAgent
from .agents.manual import key_to_aim_action, key_to_move_action
from .config import RenderConfig, WorldConfig
from .core.actions import Action
from .core.env import WumpusEnv
from .render.assets import AssetManager
from .render.renderer import GameRenderer, MenuRenderer
from .render.ui import Button


ASSET_DIR = Path(__file__).resolve().parent / "assets"


def _make_buttons(width: int, height: int) -> dict[str, Button]:
    center_x = width // 2
    panel_y = int(height * 0.44)
    return {
        "dec": Button(
            pygame.Rect(center_x - 180, panel_y + 106, 178, 42),
            "-",
            (58, 83, 120),
            (78, 108, 152),
        ),
        "inc": Button(
            pygame.Rect(center_x + 4, panel_y + 106, 178, 42),
            "+",
            (58, 83, 120),
            (78, 108, 152),
        ),
        "manual": Button(
            pygame.Rect(center_x - 180, panel_y + 170, 360, 42),
            "Iniciar (manual)",
            (45, 120, 80),
            (58, 150, 100),
        ),
        "intelligent": Button(
            pygame.Rect(center_x - 180, panel_y + 222, 360, 42),
            "Executar agente inteligente",
            (84, 74, 126),
            (104, 92, 158),
        ),
        "quit": Button(
            pygame.Rect(center_x - 180, panel_y + 274, 360, 42),
            "Sair",
            (150, 70, 70),
            (180, 88, 88),
        ),
    }


def run_app() -> None:
    """
    Executa o aplicativo gráfico.
    """
    pygame.init()
    pygame.display.set_caption("Mario Wumpus")
    render_cfg = RenderConfig()
    screen = pygame.display.set_mode((render_cfg.window_width, render_cfg.window_height))
    clock = pygame.time.Clock()

    assets = AssetManager(ASSET_DIR)
    menu_renderer = MenuRenderer(screen, assets, render_cfg)
    game_renderer = GameRenderer(screen, assets, render_cfg)

    map_size = 4
    mode = "menu"
    hovered: str | None = None
    buttons = _make_buttons(*screen.get_size())

    env: WumpusEnv | None = None
    percept = None
    last_transition = None
    agent = None
    agent_name = "Manual"
    last_agent_step = 0.0
    agent_step_period = 0.24

    def start_game(selected_agent=None, selected_name: str = "Manual") -> None:
        nonlocal env, percept, last_transition, agent, agent_name, mode, game_renderer
        cfg = WorldConfig(size=map_size)
        env = WumpusEnv(cfg)
        percept = env.reset()
        last_transition = None
        agent = selected_agent
        if agent is not None:
            agent.reset()
        agent_name = selected_name
        game_renderer.show_full_world = False
        mode = "game"

    running = True
    while running:
        now = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif mode == "menu":
                if event.type == pygame.MOUSEMOTION:
                    hovered = None
                    for name, button in buttons.items():
                        if button.contains(event.pos):
                            hovered = name
                            break
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if buttons["dec"].contains(event.pos):
                        map_size = max(4, map_size - 1)
                    elif buttons["inc"].contains(event.pos):
                        map_size = min(10, map_size + 1)
                    elif buttons["manual"].contains(event.pos):
                        start_game(None, "Manual")
                    elif buttons["intelligent"].contains(event.pos):
                        start_game(RandomAgent(seed=map_size), "Agente inteligente")
                    elif buttons["quit"].contains(event.pos):
                        running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            elif mode == "game":
                assert env is not None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        mode = "menu"
                    elif event.key == pygame.K_TAB:
                        game_renderer.show_full_world = not game_renderer.show_full_world
                    elif event.key == pygame.K_r:
                        percept = env.reset()
                        if agent is not None:
                            agent.reset()
                        last_transition = None
                    elif agent is None:
                        move_action = key_to_move_action(event.key)
                        aim_action = key_to_aim_action(event.key)
                        action = move_action or aim_action
                        if action is None and event.key == pygame.K_SPACE:
                            action = Action.RESCUE
                        elif action is None and event.key == pygame.K_f:
                            action = Action.SHOOT
                        if action is not None:
                            last_transition = env.step(action)
                            game_renderer.handle_transition(last_transition)
                            percept = last_transition.percept

        if mode == "menu":
            menu_renderer.draw(map_size, hovered, buttons)

        elif mode == "game":
            assert env is not None and env.state is not None and percept is not None
            if agent is not None and not env.state.terminal:
                if now - last_agent_step >= agent_step_period:
                    action = agent.act(percept, env.legal_actions)
                    if action not in env.legal_actions:
                        action = Action.WAIT
                    last_transition = env.step(action)
                    game_renderer.handle_transition(last_transition)
                    percept = last_transition.percept
                    last_agent_step = now

            game_renderer.render(
                state=env.state,
                percept=percept,
                last_transition=last_transition,
                agent_name=agent_name,
                game_over_reveal=env.config.reveal_world_on_game_over,
            )

        clock.tick(render_cfg.fps)

    pygame.quit()
