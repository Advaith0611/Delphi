import json
import logging
import os
from pathlib import Path
from urllib import request
from urllib.error import URLError

from dotenv import load_dotenv

from agentspan.agents import Agent, EventType, shutdown, stream, tool


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL = f"openai/{OPENROUTER_MODEL}"

logger = logging.getLogger("weather_app")

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
def get_weather(city: str) -> str:
    """Return a simple weather summary for a city."""
    logger.info("tool get_weather(city=%r)", city)
    return f"72 F and sunny in {city}"


agent = Agent(
    name="weather_assistant",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
    instructions=(
        "If the user asks about weather or outdoor plans, you must call get_weather first "
        "and base your answer on that result. Keep the final answer concise and practical."
    ),
    tools=[get_weather],
    max_tokens=256,
)


def on_event(event) -> None:
    if event.type == EventType.TOOL_CALL:
        logger.info("tool call: %s %s", event.tool_name, event.args or {})
    elif event.type == EventType.TOOL_RESULT:
        logger.info("tool result: %s -> %s", event.tool_name, event.result)
    if event.type == EventType.DONE:
        logger.info("done: %s", event.execution_id)
    elif event.type == EventType.ERROR:
        logger.error("error: %s", event.content)


def run_agent(prompt: str) -> str:
    load_credentials()

    final_output = None
    for event in stream(agent, prompt):
        on_event(event)
        if event.type == EventType.DONE:
            final_output = event.output
            break
        elif event.type == EventType.ERROR:
            raise RuntimeError(f"Agent error: {event.content}")

    if final_output is None:
        raise RuntimeError("Agent did not complete")

    return final_output


def main() -> None:
    try:
        print(run_agent("What should I do today in NYC?"))
    finally:
        shutdown()


if __name__ == "__main__":
    configure_logging()
    main()
