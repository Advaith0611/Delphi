import json
import logging
import os
from pathlib import Path
from urllib import parse, request
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv

from agentspan.agents import Agent, EventType, shutdown, stream, tool


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL = f"openai/{OPENROUTER_MODEL}"

logger = logging.getLogger("reasoning_agent")

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
def simple_search(query: str) -> str:
    """Search DuckDuckGo and return its result page for the model to interpret."""
    logger.info("tool simple_search(query=%r)", query)

    query = query.strip()
    if not query:
        return "Search failed: query must not be empty."

    search_url = "https://html.duckduckgo.com/html/?" + parse.urlencode({"q": query})
    search_request = request.Request(
        search_url,
        headers={"User-Agent": "Pythios-Reasoning-Agent/1.0"},
    )

    try:
        with request.urlopen(search_request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return "Search failed: DuckDuckGo could not be reached."

    # Let the reasoning model interpret the page instead of duplicating HTML
    # parsing logic here.
    return html


agent = Agent(
    name="reasoning_agent",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
    instructions=("You are the Reasoning Agent for Pythios. You handle calculations, "
"step-by-step explanations, comparisons, and analytical sub-tasks. "
""
"Default to the simplest correct answer. If the sub-task is a single calculation "
"or a short factual explanation, your entire output should be that calculation or "
"explanation — do not generate surrounding scaffolding, summary documents, or "
"supplementary files. Most of your calls will and should result in no file output "
"at all, just a direct answer that the Output Format Decider can route as an "
"inline response. "
""
"Use the canvas only as far as it's relevant: if numbers or relationships are "
"present on the canvas, use them as given rather than re-deriving them from "
"scratch. If the canvas shows a multi-step process (e.g. a decision tree or a "
"numbered sequence), walk through it in the same order it's laid out spatially. "
""
"For genuinely multi-step analysis (comparing several options laid out on the "
"canvas, synthesizing tradeoffs across multiple nodes), structure your reasoning "
"explicitly step by step, but still keep the final output proportional to what "
"was asked — a multi-step reasoning process does not require a multi-file output. "
""
"Return {answer, reasoning_steps: [...] (omit if trivial), "
"output_size_estimate: trivial|small|substantial} — the size estimate helps the "
"Output Format Decider avoid over-producing."),
    tools=[simple_search],
    max_tokens=2048,
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
        print(run_agent("If I have a triangle with base 8cm and the height of 6cm and we know it is isocelese determine what are the 3 angles of the triangle and test by proving they add to 180 degrees"))
    finally:
        shutdown()


if __name__ == "__main__":
    configure_logging()
    main()
