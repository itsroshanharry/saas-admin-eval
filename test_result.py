"""Quick test to see what's in the result object."""
import asyncio
from hud.agents import create_agent
from tasks import BUSINESS_TASKS
import hud

async def test():
    agent = create_agent(model="claude-sonnet-4-5")
    task = BUSINESS_TASKS[0]
    
    async with hud.eval(task) as ctx:
        result = await agent.run(ctx, max_steps=15)
    
    print("Result type:", type(result))
    print("Result attributes:", dir(result))
    print("\nChecking common attributes:")
    for attr in ['reward', 'score', 'done', 'content', 'trace', 'steps']:
        if hasattr(result, attr):
            val = getattr(result, attr)
            print(f"  {attr}: {val} (type: {type(val).__name__})")

if __name__ == "__main__":
    asyncio.run(test())
