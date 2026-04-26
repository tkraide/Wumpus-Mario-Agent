from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mario_wumpus.agents.greedy import GreedyAgent
from mario_wumpus.agents.random_agent import RandomAgent
from mario_wumpus.agents.simple_reactive_agent import SimpleReactiveAgent
from mario_wumpus.agents.state_reactive_agent import StateReactiveAgent
from mario_wumpus.config import WorldConfig
from mario_wumpus.core.env import WumpusEnv

AGENT_SELECT = 3  # 0: GreedyAgent, 1: RandomAgent, 2: SimpleReactiveAgent, 3: StateReactiveAgent

def main() -> None:
    env = WumpusEnv(WorldConfig(size=6, random_seed=7))
    match AGENT_SELECT:
        case 0:
            agent = GreedyAgent(seed=7)
        case 1:
            agent = RandomAgent(seed=7)
        case 2:
            agent = SimpleReactiveAgent(seed=7)
        case 3:
            agent = StateReactiveAgent(seed=7)

    percept = env.reset()
    agent.reset()

    print("Estado inicial:", percept.as_dict())

    while True:
        action = agent.act(percept, env.legal_actions)
        transition = env.step(action)
        percept = transition.percept
        print(
            {
                "action": action.name,
                "reward": transition.reward,
                "done": transition.done,
                "percept": percept.as_dict(),
                "info": {
                    "success": transition.info["success"],
                    "score": round(transition.info["score"], 2),
                    "bowser_alive": transition.info["bowser_alive"],
                },
            }
        )
        if transition.done:
            break


if __name__ == "__main__":
    main()
