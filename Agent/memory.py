import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from agentspan.agents import Agent, EventType, shutdown, stream, tool


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL = f"openai/{OPENROUTER_MODEL}"

logger = logging.getLogger("working_memory_agent")

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
def write_memory_entry(
    sub_task_id: str,
    source_agent: str,
    output_type: str,
    output_summary: str,
) -> str:
    """Write a new memory entry to the session state."""
    with open("session_memory.txt", "a") as f:
        f.write(
            f"{sub_task_id}\t{source_agent}\t{output_type}\t{output_summary}\n"
        )
        
    logger.info(
        "Memory entry written: %s, %s, %s, %s",
        sub_task_id,
        source_agent,
        output_type,
        output_summary,
    )
    return "Memory entry written successfully."


working_memory_agent = Agent(
    name="working_memory",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
    instructions=(
"You are the Working Memory component of Pythios's Orchestrator. "
"You do not answer the user directly and you do not make planning decisions. "
"Your only job is to maintain a compact, accurate running record of the current "
"session's state. "
""
"On each call you will receive either (a) a new specialist agent output to "
"incorporate, or (b) a query asking what has been produced so far. "
""
"For incorporation calls: append a compressed entry to the state object "
"containing {sub_task_id, source_agent, output_type, output_summary (max 2 sentences), "
"canvas_regions_touched}. Do not store full output content if it exceeds roughly "
"200 tokens — store a faithful summary and a pointer instead, since this object "
"will be re-read many times per session and must stay small. "
""
"For query calls: return only the fields relevant to the query, never the entire "
"state object, to keep the calling agent's context minimal. "
""
"Never alter or reinterpret a prior entry's content — if new information "
"contradicts an old entry, add a new entry noting the contradiction rather than "
"silently overwriting history."),
    tools=[write_memory_entry],
    max_tokens=2048,
)


MEMORY_TASK = """

Maintain the current Pythios session memory.

If this request contains a specialist agent result, record a compact summary with
its sub-task ID, source_agent, output type, summary, and canvas regions touched.
Keep the summary to at most two sentences and do not store full output. If this
request is a memory query, return only the fields needed to answer that query.
Preserve earlier entries and record contradictions as new entries.
write an intial start process entry into working memory

""".strip()


def run_memory_agent(memory_request: str = MEMORY_TASK) -> str:
    load_credentials()
    final_output = None

    for event in stream(working_memory_agent, memory_request):
        if event.type == EventType.DONE:
            final_output = event.output
            break
        if event.type == EventType.ERROR:
            raise RuntimeError(f"Working memory error: {event.content}")

    if final_output is None:
        raise RuntimeError("Working memory agent did not complete")
    return final_output


def main() -> None:
    try:
        print(run_memory_agent())
    finally:
        shutdown()


if __name__ == "__main__":
    configure_logging()
    main()
