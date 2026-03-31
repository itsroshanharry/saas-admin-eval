"""
run.py — Run the eval locally or at scale.

THREE MODES:

  1. Local dev (single task, instant feedback)
     python run.py --mode dev --category business --task 0

  2. Full eval (all 30 tasks, one model)
     python run.py --mode full --model claude

  3. Multi-model comparison (builds your leaderboard)
     python run.py --mode compare

Usage:
  pip install hud-python anthropic
  export HUD_API_KEY=your_key
  export ANTHROPIC_API_KEY=your_key
  python run.py --mode dev
"""

import asyncio
import argparse
from hud.agents import create_agent
from tasks import BUSINESS_TASKS, AGENTIC_TASKS, REDTEAM_TASKS, ALL_TASKS
import hud


# ── Mode 1: Local dev — run one task, print everything ────────────────────────

async def run_dev(category: str, task_idx: int):
    """
    Run a single task locally. Use this while building scenarios.
    Shows the full agent loop: prompt → tool calls → reward.
    """
    tasksets = {
        "business": BUSINESS_TASKS,
        "agentic":  AGENTIC_TASKS,
        "redteam":  REDTEAM_TASKS,
    }
    tasks = tasksets.get(category, BUSINESS_TASKS)
    task = tasks[task_idx]

    print(f"\n{'='*60}")
    print(f"Category : {category}")
    print(f"Task idx : {task_idx}")
    print(f"{'='*60}\n")

    agent = create_agent(
        model="claude-sonnet-4-5",
        verbose=True,   # prints every tool call the agent makes
    )

    async with hud.eval(task) as ctx:
        print(f"Prompt: {ctx.prompt}\n")
        result = await agent.run(ctx, max_steps=15)
    
    # Reward is set when context exits, so read it from ctx AFTER the block
    reward = ctx.reward if hasattr(ctx, 'reward') and ctx.reward is not None else 0.0

    print(f"\n{'='*60}")
    print(f"Reward   : {reward}")
    print(f"Done     : {result.done}")
    print(f"Steps    : {len(result.steps) if hasattr(result, 'steps') else 'N/A'}")
    print(f"{'='*60}\n")

    return result


# ── Mode 2: Full eval — all 30 tasks, uploads traces to HUD platform ──────────

async def run_full(model: str = "claude"):
    """
    Run all 30 tasks. Traces upload to hud.ai automatically.
    Results appear on your taskset's leaderboard tab in real time.
    """
    print(f"\nRunning full eval with model: {model}")
    print(f"Tasks: {len(ALL_TASKS)} | Categories: business(10) + agentic(10) + redteam(10)\n")

    # hud eval CLI does this more efficiently (parallel) but this works locally too
    results = {"business": [], "agentic": [], "redteam": []}
    categories = [
        ("business", BUSINESS_TASKS),
        ("agentic",  AGENTIC_TASKS),
        ("redteam",  REDTEAM_TASKS),
    ]

    agent = create_agent(model="claude-sonnet-4-5")

    for cat_name, tasks in categories:
        print(f"\n── {cat_name.upper()} ({len(tasks)} tasks) ──")
        for i, task in enumerate(tasks):
            async with hud.eval(task) as ctx:
                result = await agent.run(ctx, max_steps=15)
            
            # Reward is set when context exits, read from ctx
            reward = ctx.reward if hasattr(ctx, 'reward') and ctx.reward is not None else 0.0
            
            results[cat_name].append(reward)
            bar = "█" * int(reward * 10) + "░" * (10 - int(reward * 10))
            print(f"  Task {i+1:02d} [{bar}] {reward:.2f}")

    # ── Summary ──
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for cat, scores in results.items():
        avg = sum(scores) / len(scores)
        full_pass = sum(1 for s in scores if s == 1.0)
        print(f"{cat:10s}  avg={avg:.2f}  full_pass={full_pass}/{len(scores)}")

    all_scores = [s for scores in results.values() for s in scores]
    overall = sum(all_scores) / len(all_scores)
    print(f"\nOverall avg reward: {overall:.2f}")
    print(f"Target range:       0.20 – 0.35  (for useful training signal)")
    if overall < 0.20:
        print("→ Tasks may be too hard. Consider adding more partial credit.")
    elif overall > 0.40:
        print("→ Tasks may be too easy. Consider harder variants or stricter graders.")
    else:
        print("→ Good difficulty range. Traces are ready for training.")
    print(f"{'='*60}\n")


# ── Mode 3: Multi-model comparison — builds your leaderboard ──────────────────

async def run_compare():
    """
    Run the red-team category across Claude and GPT-4o.
    Results show up in your HUD leaderboard for model comparison.
    This is the most compelling thing to show in your portfolio.
    """
    print("\nMulti-model comparison on red-team tasks")
    print("This builds your public leaderboard on hud.ai\n")
    print("Run from CLI for parallel execution:")
    print("  hud eval tasks.REDTEAM_TASKS claude --full --group-size 3")
    print("  hud eval tasks.REDTEAM_TASKS gpt-4o --full --group-size 3")
    print("\nOr run sequentially here (slower):")

    models = [
        ("Claude Sonnet", create_agent(model="claude-sonnet-4-5")),
        ("GPT-4o",        create_agent(model="gpt-4o")),
    ]

    for model_name, agent in models:
        print(f"\n── {model_name} ──")
        scores = []
        for i, task in enumerate(REDTEAM_TASKS):
            async with hud.eval(task) as ctx:
                result = await agent.run(ctx, max_steps=10)
            
            # Reward is set when context exits, read from ctx
            reward = ctx.reward if hasattr(ctx, 'reward') and ctx.reward is not None else 0.0
            
            scores.append(reward)
            status = "✓ RESISTED" if reward == 1.0 else "✗ COMPROMISED"
            print(f"  Red-team {i+1:02d}: {status} ({reward:.2f})")
        avg = sum(scores) / len(scores)
        print(f"  Resistance rate: {avg:.0%}")


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run saas-admin-eval")
    parser.add_argument("--mode", choices=["dev", "full", "compare"], default="dev")
    parser.add_argument("--category", choices=["business", "agentic", "redteam"], default="business")
    parser.add_argument("--task", type=int, default=0, help="Task index for dev mode")
    parser.add_argument("--model", default="claude", help="Model for full mode")
    args = parser.parse_args()

    if args.mode == "dev":
        asyncio.run(run_dev(args.category, args.task))
    elif args.mode == "full":
        asyncio.run(run_full(args.model))
    elif args.mode == "compare":
        asyncio.run(run_compare())
