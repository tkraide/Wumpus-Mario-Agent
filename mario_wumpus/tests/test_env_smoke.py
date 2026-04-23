from mario_wumpus.config import WorldConfig
from mario_wumpus.core.actions import Action
from mario_wumpus.core.env import WumpusEnv


def test_env_reset_and_step():
    env = WumpusEnv(WorldConfig(size=4, random_seed=1))
    percept = env.reset()
    assert percept.position.as_tuple() == (3, 0)
    transition = env.step(Action.WAIT)
    assert isinstance(transition.reward, float)
