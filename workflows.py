"""Auto-Flow AI - task menu.

Each entry in WORKFLOWS is one task the user can pick.
All of them use the same engine: run_workflow() from agent_core.py.
"""
import asyncio
from typing import List, Optional

from pydantic import BaseModel

from agent_core import run_workflow

SAFETY = " Do not log in, buy anything, or submit any form."


# ---------------------------------------------------------------- result shapes
class Product(BaseModel):
    name: str
    price: str
    rating: Optional[str] = None
    url: Optional[str] = None


class ProductList(BaseModel):
    products: List[Product]


class Job(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    url: Optional[str] = None


class JobList(BaseModel):
    jobs: List[Job]


class PageSummary(BaseModel):
    title: str
    summary: str


# ---------------------------------------------------------------- the menu
WORKFLOWS = {
    "1": {
        "label": "Compare product prices",
        "inputs": [("site", "Website URL (e.g. https://www.amazon.in)"),
                   ("query", "What product? (e.g. wireless earbuds)")],
        "goal": "Go to {site}, search for '{query}', and return the 3 cheapest "
                "results with name, price, rating and link." + SAFETY,
        "output": ProductList,
        "needs_approval": False,
    },
    "2": {
        "label": "Find jobs / internships",
        "inputs": [("site", "Job site URL"),
                   ("query", "Job title (e.g. AI intern)")],
        "goal": "Go to {site}, search for '{query}', and return the first 5 "
                "listings with title, company, location and link." + SAFETY,
        "output": JobList,
        "needs_approval": True,   # demo of the human-approval gate
    },
    "3": {
        "label": "Summarize a web page",
        "inputs": [("url", "Page URL (try https://example.com first)")],
        "goal": "Go to {url} and return the page title and a 2-sentence "
                "summary of the page." + SAFETY,
        "output": PageSummary,
        "needs_approval": False,
    },
}


# ---------------------------------------------------------------- runner
async def run_task(choice: str, **inputs) -> dict:
    wf = WORKFLOWS[choice]
    goal = wf["goal"].format(**inputs)

    if wf["needs_approval"]:
        print(f"\nThe agent is about to do this:\n  {goal}")
        if input("Approve? (y/n): ").strip().lower() != "y":
            return {"success": False, "result": None, "error": "cancelled by user"}

    return await run_workflow(goal, wf["output"])


async def main():
    print("\n=== Auto-Flow AI ===")
    for key, wf in WORKFLOWS.items():
        print(f"  {key}. {wf['label']}")
    choice = input("\nPick a task number: ").strip()
    if choice not in WORKFLOWS:
        print("Invalid choice.")
        return

    inputs = {}
    for key, prompt in WORKFLOWS[choice]["inputs"]:
        inputs[key] = input(f"{prompt}: ").strip()

    out = await run_task(choice, **inputs)
    print("\n---------------- RESULT ----------------")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())
