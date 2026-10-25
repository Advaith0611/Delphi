import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from agentspan.agents import Agent, EventType, shutdown, stream, tool


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL = f"openai/{OPENROUTER_MODEL}"

logger = logging.getLogger("planner_agent")

def configure_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_credentials() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")
    os.environ["OPENAI_API_KEY"] = key


@tool
def read_project_file(filename: str) -> str:
    """Read one small, approved project file for planning; never modify files."""
    allowed_files = {
        "reason.py",
        "weather.py",
        "planner.py",
        "example.json",
        "pyproject.toml",
        "README.md",
    }
    if filename not in allowed_files:
        return f"Read denied: {filename!r} is not an approved project file."

    path = Path(__file__).with_name(filename)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Read failed for {filename!r}: {exc}"


agent = Agent(
    name="project_planner",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
    instructions=(
        "You are the Planning Agent for Pythios. Create practical, ordered plans for "
        "software and documentation work. Inspect the files named in the task before "
        "making recommendations. Separate confirmed facts from assumptions, identify "
        "dependencies and risks, and keep each step concrete enough for another agent "
        "to implement. Do not invent files, APIs, or test results. Return a concise "
        "Markdown plan with: Goal, Current state, Proposed changes, Verification, and "
        "Open questions. Use read_project_file when local file contents are needed. "
        "This agent plans only; it must not modify files or run commands."
    ),
    tools=[read_project_file],
    max_tokens=2048,
)


PLANNER_TASK = """
Review this Agentspan project and prepare an implementation plan for the next agent.

Inspect 'example.json' and infer what shape or drawing the file likely describes it is context for a whiteboard shopwing the postipon and spape of some objects infer the user's goal and the current state of the project. Identify any missing information or assumptions that need to be clarified. Create a step-by-step plan for implementing the next agent, including any necessary changes to existing files, new files to be created, and how to verify the implementation. DO NOT write or create any files or run any commands. Return the plan in Markdown format with the following sections: Goal, Current state, Proposed changes, Verification, and Open questions.
""".strip()


def run_planner(task: str = PLANNER_TASK) -> str:
    load_credentials()
    final_output = None

    for event in stream(agent, task):
        if event.type == EventType.DONE:
            final_output = event.output
            break
        if event.type == EventType.ERROR:
            raise RuntimeError(f"Planner error: {event.content}")

    if final_output is None:
        raise RuntimeError("Planner did not complete")
    return final_output


def main() -> None:
    try:
        print(run_planner())
    finally:
        shutdown()


if __name__ == "__main__":
    configure_logging()
    main()
