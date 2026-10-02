"""Auto-Flow AI - core agent (rebuilt).

Takes a natural-language goal, drives a browser with browser-use,
and always returns a dict: {"success": bool, "result": ..., "error": ...}.
"""
import os
import asyncio
from typing import Optional, Type

from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, ChatGoogle

load_dotenv()

# ---------------------------------------------------------------- config
MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
RUN_RETRIES = int(os.getenv("RUN_RETRIES", "2"))        # whole-run retries
RETRY_WAIT = int(os.getenv("RETRY_WAIT_SECONDS", "20"))  # wait between them


# ---------------------------------------------------------------- models
def build_llms():
    """Primary = Google. Fallback = Groq, or a 2nd Google project, or none."""
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if key:
        os.environ["GOOGLE_API_KEY"] = key

    primary = ChatGoogle(model=os.getenv("PRIMARY_MODEL", "gemini-3.8-flash"))
    fallback = None

    if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_MODEL"):
        from browser_use import ChatGroq
        fallback = ChatGroq(model=os.getenv("GROQ_MODEL"))
    elif os.getenv("GOOGLE_API_KEY_2"):
        fallback = ChatGoogle(
            model=os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite"),
            api_key=os.getenv("GOOGLE_API_KEY_2"),
        )
    return primary, fallback


# ---------------------------------------------------------------- output shapes
class PageAnswer(BaseModel):
    """Example structured result. Replace/extend for your real use cases."""
    answer: str
    source_url: Optional[str] = None


# ---------------------------------------------------------------- agent
def make_agent(goal: str, llm, fallback, output_model: Optional[Type[BaseModel]]):
    kwargs = dict(
        task=goal,
        llm=llm,
        fallback_llm=fallback,
        use_vision=False,   # fewer tokens; turn on for visual tasks
        use_judge=False,    # skips the extra grading call
        max_failures=5,
        retry_delay=15,
    )
    if output_model is not None:
        kwargs["output_model_schema"] = output_model

    # Parameter names shift between browser-use versions: drop any the
    # installed version rejects instead of crashing.
    for _ in range(4):
        try:
            return Agent(**kwargs)
        except TypeError as e:
            bad = next((k for k in list(kwargs) if f"'{k}'" in str(e)), None)
            if bad is None or bad in ("task", "llm"):
                raise
            print(f"[warn] this browser-use version doesn't accept '{bad}', skipping it")
            kwargs.pop(bad)
    raise RuntimeError("Could not construct Agent")


async def run_workflow(goal: str, output_model: Optional[Type[BaseModel]] = None) -> dict:
    primary, fallback = build_llms()
    last_error = "unknown error"

    for attempt in range(1, RUN_RETRIES + 2):
        try:
            print(f"🚀 Attempt {attempt}: {goal!r}")
            agent = make_agent(goal, primary, fallback, output_model)
            history = await agent.run(max_steps=MAX_STEPS)

            result = None
            if output_model is not None:
                result = getattr(history, "structured_output", None)
                if result is not None:
                    result = result.model_dump()
            if result is None:
                result = history.final_result()

            if result:
                return {"success": True, "result": result, "error": None}
            last_error = "agent finished without a result"
        except Exception as e:  # network, quota, browser crash...
            last_error = f"{type(e).__name__}: {e}"
            print(f"[error] {last_error}")

        if attempt <= RUN_RETRIES:
            print(f"⏳ Waiting {RETRY_WAIT}s before retrying...")
            await asyncio.sleep(RETRY_WAIT)

    return {"success": False, "result": None, "error": last_error}


# ---------------------------------------------------------------- demo
async def main():
    out = await run_workflow(
        "Go to https://example.com and extract the main heading.",
        output_model=PageAnswer,
    )
    print("\n---------------- OUTPUT ----------------")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())