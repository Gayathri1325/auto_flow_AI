# main.py - Auto-Flow AI Engine (API)
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_core import run_workflow
from workflows import WORKFLOWS, SAFETY

app = FastAPI(title="Auto-Flow AI Engine", version="2.0")

# In-memory task store (resets when the server restarts)
TASKS: Dict[str, dict] = {}


class TaskRequest(BaseModel):
    workflow: str            # e.g. "3"
    inputs: Dict[str, str]   # e.g. {"url": "https://example.com"}


class FreeformRequest(BaseModel):
    goal: str


def _public(task: dict) -> dict:
    keys = ("task_id", "workflow", "goal", "status", "result", "error")
    return {k: task.get(k) for k in keys}


async def _run(task: dict) -> dict:
    task["status"] = "running"
    out = await run_workflow(task["goal"], task.get("output_model"))
    task["status"] = "completed" if out["success"] else "failed"
    task["result"] = out["result"]
    task["error"] = out["error"]
    return _public(task)


@app.get("/api/v1/workflows")
def list_workflows():
    """What tasks can the user pick, and what inputs does each need?"""
    return [
        {
            "id": key,
            "label": wf["label"],
            "inputs": [{"name": n, "prompt": p} for n, p in wf["inputs"]],
            "needs_approval": wf["needs_approval"],
        }
        for key, wf in WORKFLOWS.items()
    ]


@app.post("/api/v1/tasks")
async def create_task(req: TaskRequest):
    """Start a task. If it needs approval, it waits as 'pending_approval'."""
    wf = WORKFLOWS.get(req.workflow)
    if wf is None:
        raise HTTPException(404, f"Unknown workflow '{req.workflow}'")

    missing = [n for n, _ in wf["inputs"] if n not in req.inputs]
    if missing:
        raise HTTPException(400, f"Missing inputs: {missing}")

    task = {
        "task_id": uuid.uuid4().hex[:8],
        "workflow": req.workflow,
        "goal": wf["goal"].format(**req.inputs),
        "output_model": wf["output"],
        "status": "pending_approval" if wf["needs_approval"] else "queued",
        "result": None,
        "error": None,
    }
    TASKS[task["task_id"]] = task

    if wf["needs_approval"]:
        return _public(task)          # human must approve before anything runs
    return await _run(task)


@app.post("/api/v1/tasks/{task_id}/approve")
async def approve_task(task_id: str):
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if task["status"] != "pending_approval":
        raise HTTPException(409, f"Task is '{task['status']}', not waiting for approval")
    return await _run(task)


@app.post("/api/v1/tasks/{task_id}/reject")
def reject_task(task_id: str):
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if task["status"] != "pending_approval":
        raise HTTPException(409, f"Task is '{task['status']}', not waiting for approval")
    task["status"] = "rejected"
    task["error"] = "rejected by user"
    return _public(task)


@app.get("/api/v1/tasks/{task_id}")
def get_task(task_id: str):
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return _public(task)


@app.post("/api/v1/execute")
async def execute_freeform(req: FreeformRequest):
    """Your original endpoint: any goal in plain English (safety rules added)."""
    out = await run_workflow(req.goal + SAFETY)
    return {
        "status": "completed" if out["success"] else "failed",
        "result": out["result"],
        "error": out["error"],
    }


if __name__ == "__main__":
    import uvicorn
    # reload=False: auto-reload on Windows can break browser launching
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
