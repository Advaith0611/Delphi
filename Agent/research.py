import json
import logging
import os
from pathlib import Path
from urllib import parse, request
from urllib.error import HTTPError, URLError
from tavily import TavilyClient
from dotenv import load_dotenv

from agentspan.agents import Agent, EventType, shutdown, stream, tool


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL = f"openai/{OPENROUTER_MODEL}"

logger = logging.getLogger("research_agent")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_credentials() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY") 
    if not key and not tavily_key:
        raise RuntimeError("Set OPENROUTER_API_KEY or OPENAI_API_KEY and Tavily key in .env")
    os.environ["OPENAI_API_KEY"] = key
    os.environ["TAVILY_API_KEY"] = tavily_key


@tool
def simple_search(query: str) -> str:
    """
    Search DuckDuckGo and return the raw HTML result page.

    Use this for a focused lookup when current or uncertain information is
    needed. The result is unstructured HTML rather than a verified answer, so
    inspect it carefully and cross-check important claims with reliable or
    primary sources. This tool does not perform deep research, extract a
    specific URL, or crawl an entire website.

    Args:
        query: A specific, non-empty search question or phrase.

    Returns:
        Raw DuckDuckGo HTML, or a failure message if the query is empty or the
        search service cannot be reached.
    """
    logger.info("tool research_search(query=%r)", query)

    query = query.strip()
    if not query:
        return "Search failed: query must not be empty."

    search_url = "https://html.duckduckgo.com/html/?" + parse.urlencode({"q": query})
    search_request = request.Request(
        search_url,
        headers={"User-Agent": "Pythios-Research-Agent/1.0"},
    )

    try:
        with request.urlopen(search_request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return "Search failed: DuckDuckGo could not be reached."

    # Let the research model interpret the page instead of duplicating HTML
    # parsing logic here.
    return html

@tool
def search(query:str):
    """
    Perform an advanced Tavily web search.

    Use this for focused web research that benefits from ranked, extracted
    search results. It is faster and narrower than deep_research and does not
    explore an entire website. Results can still be incomplete, so verify
    important claims and preserve source URLs in the final answer.

    Args:
        query: A clear web-search question or phrase.

    Returns:
        Tavily's search response containing matching results and metadata.
    """
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    response = client.search(
        query= query,
        search_depth="advanced"
    )
    return(response)

@tool
def extract(urls:list):
    """
    Extract readable content from one or more supplied URLs with Tavily.

    Use this after search when specific pages need to be read in detail. It
    does not discover new pages and should receive URLs that are relevant to
    the current research question.

    Args:
        urls: A list of page URLs to extract.

    Returns:
        Tavily's extracted page content and URL metadata.
    """
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    response = client.extract(
    urls=urls)
    return(response)

@tool
def crawl(
    url: str, 
    instructions: str):
    """
    Crawl a website starting from a base URL using Tavily.

    Use this for documentation sites or related pages where the answer is
    distributed across multiple pages. Keep the base URL focused and make the
    instructions describe exactly which pages or information to find. Crawling
    can return a large amount of content, so summarize or limit it before
    passing the result into another model step.

    Args:
        url: The starting website URL.
        instructions: A focused description of what pages or information to find.

    Returns:
        Tavily's crawl results and extracted page content.
    """
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    response = client.crawl(
    url = url,
    instructions = instructions,
    extract_depth="advanced"
    )
    return(response)
@tool
def deep_research():
    """
    Start a Tavily multi-step research task about the latest AI developments.

    Use this for broad questions requiring multiple searches, source analysis,
    and synthesis. This current implementation researches a fixed question;
    it does not accept a custom research query. It polls Tavily until the task
    completes and returns the generated report plus its sources. It is a last resort only for super complex tasks.

    Returns:
        A string containing the Tavily research report and source list.
    """
    tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    # Start a research task
    response = tavily_client.research("What are the latest developments in AI?")

    # Get the request ID
    request_id = response.get("request_id")

    # Poll for results
    while True:
        result = tavily_client.get_research_result(request_id)
        if result.get("status") == "completed":
            print(result.get("content"))  # The research report
            print(result.get("sources"))
            response = f"Content: {result.get('content')}, Sources: {result.get('sources')}"
            return(response)
            break
        elif result.get("status") == "failed":
            return("Research failed")
            break


research_agent = Agent(
    name="research_agent",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
instructions=("You are the Research Agent for Pythios. You investigate current or "
"uncertain topics, compare credible sources, and return practical findings. "
""
"Use research_search when outside information is needed. Prefer official documentation "
"and primary sources, and distinguish confirmed facts from assumptions. "
""
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
"Return {answer, sources: [...] (omit if no search was needed), "
"output_size_estimate: trivial|small|substantial} — the size estimate helps the "
"Output Format Decider avoid over-producing."
"only use deep reserch tool when absolutely nesscary only use it when you have exhausted all other tools and need to get the most up to date information on a topic."),
    tools=[simple_search, search, extract, crawl, deep_research],
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


def run_research_agent(research_prompt: str) -> str:
    load_credentials()

    final_output = None
    for event in stream(research_agent, research_prompt):
        on_event(event)
        if event.type == EventType.DONE:
            final_output = event.output
            break
        elif event.type == EventType.ERROR:
            raise RuntimeError(f"Research agent error: {event.content}")

    if final_output is None:
        raise RuntimeError("Research agent did not complete")

    return final_output


def main() -> None:
    try:
        print(run_research_agent("Research the current best practices for building a small interactive web application from a whiteboard design. Identify the recommended implementation approach, relevant libraries, official documentation, and important compatibility risks."))
    finally:
        shutdown()


if __name__ == "__main__":
    configure_logging()
    main()
