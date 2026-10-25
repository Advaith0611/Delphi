"""Pythios coding agent.

This agent works in a temporary project directory selected with
``PYTHIOS_PROJECT_ROOT`` (or the current working directory).  It deliberately
uses local file and shell tools rather than a general coding harness so the
generated project can be created, built, and published by the surrounding app.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from agentspan.agents import Agent, EventType, Strategy, shutdown, stream, tool


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL", "cohere/north-mini-code:free"
)
MODEL = f"openai/{OPENROUTER_MODEL}"

logger = logging.getLogger("coder_agent")

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
}


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
    # Agentspan's OpenAI-compatible provider reads OPENAI_API_KEY.
    os.environ["OPENAI_API_KEY"] = key


def project_root() -> Path:
    """Return the active generated project directory."""
    configured = os.environ.get("PYTHIOS_PROJECT_ROOT")
    root = (
        Path(configured).expanduser()
        if configured
        else Path(__file__).with_name("coder_projects") / "pythios_project"
    )
    # macOS uses /tmp for temporary files. Treat /temp as its common typo,
    # while preserving a project suffix such as /temp/project-123.
    if root == Path("/temp") or Path("/temp") in root.parents:
        root = Path("/tmp") / root.relative_to("/temp")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_project_path(filename: str) -> Path:
    """Resolve a relative project path without allowing it to escape the project."""
    if not filename or Path(filename).is_absolute():
        raise ValueError("filename must be a non-empty relative path")
    root = project_root()
    path = (root / filename).resolve()
    if path != root and root not in path.parents:
        raise ValueError("path must remain inside the active project directory")
    return path


def _relative(path: Path) -> str:
    return str(path.relative_to(project_root()))


def _included(path: Path) -> bool:
    return not any(part in IGNORED_DIRECTORIES for part in path.parts)


def _trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} characters]"


@tool
def list_project_files(prefix: str = "", max_files: int = 300) -> str:
    """List files in the generated project, optionally below a relative prefix."""
    try:
        base = safe_project_path(prefix) if prefix else project_root()
        if not base.is_dir():
            return json.dumps({"error": f"Not a directory: {prefix}"})
        files = [
            _relative(path)
            for path in base.rglob("*")
            if path.is_file() and _included(path)
        ]
        files.sort()
        return json.dumps({
            "root": str(project_root()),
            "files": files[:max(1, min(max_files, 1000))],
            "truncated": len(files) > max_files,
        })
    except (OSError, ValueError) as exc:
        return json.dumps({"error": str(exc)})


@tool
def read_project_file(filename: str, max_chars: int = 30000) -> str:
    """Read one project file, capped to keep the model context manageable."""
    try:
        path = safe_project_path(filename)
        if not path.is_file():
            return f"Read failed: {filename!r} is not a file."
        content = path.read_text(encoding="utf-8", errors="replace")
        return _trim(content, max(1000, min(max_chars, 100000)))
    except (OSError, ValueError) as exc:
        return f"Read failed for {filename!r}: {exc}"


@tool
def search_project(query: str, glob: str = "", max_matches: int = 100) -> str:
    """Search project text with ripgrep and return matching paths and lines."""
    query = query.strip()
    if not query:
        return "Search failed: query must not be empty."
    command = ["rg", "-n", "--hidden", "--glob", "!.git", "--glob", "!node_modules"]
    if glob:
        command.extend(["--glob", glob])
    command.extend([query, str(project_root())])
    try:
        result = subprocess.run(
            command,
            cwd=project_root(),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode not in (0, 1):
            return f"Search failed: {_trim(result.stderr, 4000)}"
        lines = result.stdout.splitlines()
        return "\n".join(lines[:max(1, min(max_matches, 500))]) or "No matches found."
    except FileNotFoundError:
        return "Search unavailable: rg is not installed. Use list_project_files and read_project_file."
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Search failed: {exc}"


@tool
def write_project_file(filename: str, content: str) -> str:
    """Create or replace a generated project file."""
    try:
        path = safe_project_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return json.dumps({"written": True, "path": _relative(path), "bytes": path.stat().st_size})
    except (OSError, ValueError) as exc:
        return json.dumps({"written": False, "path": filename, "error": str(exc)})


@tool
def delete_project_file(filename: str) -> str:
    """Delete one generated project file when it is no longer needed."""
    try:
        path = safe_project_path(filename)
        if not path.is_file():
            return json.dumps({"deleted": False, "error": "file does not exist"})
        path.unlink()
        return json.dumps({"deleted": True, "path": filename})
    except (OSError, ValueError) as exc:
        return json.dumps({"deleted": False, "error": str(exc)})


@tool
def run_project_command(command: str, timeout_seconds: int = 120) -> str:
    """Run a build, test, install, or inspection command in the project directory."""
    command = command.strip()
    if not command:
        return "Command failed: command must not be empty."
    timeout = max(1, min(timeout_seconds, 600))
    logger.info("running project command: %s", command)
    try:
        completed = subprocess.run(
            command,
            cwd=project_root(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        return json.dumps({
            "command": command,
            "returncode": completed.returncode,
            "output": _trim(output, 20000),
        })
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return json.dumps({
            "command": command,
            "returncode": None,
            "timed_out": True,
            "output": _trim(output, 12000),
        })
    except OSError as exc:
        return json.dumps({"command": command, "returncode": None, "error": str(exc)})


@tool
def inspect_project_context(max_files: int = 80, max_chars_per_file: int = 6000) -> str:
    """Return a compact context snapshot of likely source/config files."""
    candidates = []
    for path in project_root().rglob("*"):
        if not path.is_file() or not _included(path):
            continue
        if path.suffix.lower() in {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json",
            ".toml", ".yaml", ".yml", ".md", ".txt",
        }:
            candidates.append(path)
    candidates.sort(key=lambda item: (item.name not in {"package.json", "pyproject.toml", "README.md"}, str(item)))
    snapshot: list[dict[str, str]] = []
    for path in candidates[:max(1, min(max_files, 200))]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            snapshot.append({"path": _relative(path), "content": _trim(text, max(500, min(max_chars_per_file, 20000)))})
        except OSError:
            continue
    return json.dumps({"root": str(project_root()), "files": snapshot}, ensure_ascii=False)


@tool
def record_plan(goal: str, steps: list[str], files: list[str] | None = None) -> str:
    """Record the current implementation plan in the tool result without creating a file."""
    normalized = [step.strip() for step in steps if step and step.strip()]
    if not goal.strip() or not normalized:
        return "Plan rejected: provide a goal and at least one concrete step."
    return json.dumps({"planned": True, "goal": goal.strip(), "steps": normalized, "files": files or []})


# The explorer has no write or shell tools. It can be handed the same task and
# return repository facts before the main coder starts making changes.
explorer_agent = Agent(
    name="codebase_explorer",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
    instructions=(
        "You are the read-only Codebase Explorer for Pythios. Inspect the active "
        "temporary project using only list_project_files, read_project_file, "
        "search_project, and inspect_project_context. Never write files, delete "
        "files, or run commands. Report the relevant existing architecture, entry "
        "points, dependencies, conventions, and likely files for the requested "
        "change. Separate observed facts from assumptions and keep the report "
        "compact enough for the main Code Agent to use."
    ),
    tools=[list_project_files, read_project_file, search_project, inspect_project_context],
    max_turns=12,
    max_tokens=4096,
    include_contents="none",
)


CODER_INSTRUCTIONS = (
    "You are the Code Agent for Pythios. You receive a sub-task description, the "
    "relevant canvas region (which may be a system diagram, a flow sketch, or "
    "annotated boxes representing an architecture), and the complexity estimate "
    "assigned by the Task Planner. "
    "\n\n"
    "Treat the canvas as the actual specification, not as inspiration. Node "
    "groupings indicate module boundaries. Arrows indicate data flow or call "
    "direction — implement them as such, do not infer a different architecture "
    "than what is drawn. Annotations and labels on the canvas take precedence "
    "over your own assumptions about naming or structure. "
    "\n\n"
    "First use the read-only Codebase Explorer for repository context on any "
    "non-trivial task. Then use record_plan with a concise implementation plan. "
    "Explore the existing project before editing it; use inspect_project_context, "
    "list_project_files, read_project_file, and search_project deliberately rather "
    "than loading the whole repository into context. Re-read files after important "
    "edits and run the smallest relevant build or test command before finishing. "
    "\n\n"
    "Produce only the code actually required by the sub-task. Do not scaffold "
    "additional files, READMEs, or boilerplate the user did not ask for and the "
    "canvas does not imply. You are creating a temporary generated project, not "
    "editing a user's existing codebase, so write directly to the active project "
    "directory and keep the result runnable. "
    "\n\n"
    "For low/medium complexity sub-tasks, prioritize directness and correctness "
    "over exhaustive edge-case handling. For high complexity sub-tasks (multi-file "
    "systems, multi-agent frameworks, anything spanning more than one canvas "
    "cluster), be thorough: define module boundaries explicitly, note assumptions, "
    "and flag any part of the canvas that was ambiguous rather than silently "
    "resolving it. "
    "\n\n"
    "Use context controls: prefer bounded reads, targeted searches, and compact "
    "summaries; do not repeat unchanged file contents in your final response. "
    "Shell execution is available for project creation, dependency installation, "
    "builds, tests, and static-site inspection. Report command failures accurately "
    "and repair them when they are within the task. "
    "\n\n"
    "Return {files: [{path, content}], assumptions_made: [...], "
    "canvas_elements_used: [...]}. The files array must describe the final files "
    "created or changed, with their complete content when practical. Also mention "
    "verification results briefly, but do not return unrelated logs."
)


coder_agent = Agent(
    name="pythios_code_agent",
    model=MODEL,
    base_url=OPENROUTER_BASE_URL,
    instructions=CODER_INSTRUCTIONS,
    tools=[
        list_project_files,
        read_project_file,
        search_project,
        write_project_file,
        delete_project_file,
        run_project_command,
        inspect_project_context,
        record_plan,
    ],
    agents=[explorer_agent],
    strategy=Strategy.HANDOFF,
    max_turns=40,
    max_tokens=8192,
    include_contents="default",
    metadata={"product": "pythios", "temporary_projects": True},
)


def on_event(event: Any) -> None:
    if event.type == EventType.TOOL_CALL:
        logger.info("tool call: %s %s", event.tool_name, event.args or {})
    elif event.type == EventType.TOOL_RESULT:
        logger.info("tool result: %s", event.tool_name)
    elif event.type == EventType.ERROR:
        logger.error("error: %s", event.content)
    elif event.type == EventType.DONE:
        logger.info("done: %s", event.execution_id)


def run_coder_agent(coder_prompt: str) -> Any:
    """Run the coder against the active temporary project directory."""
    load_credentials()
    final_output = None
    for event in stream(coder_agent, coder_prompt):
        on_event(event)
        if event.type == EventType.DONE:
            final_output = event.output
            break
        if event.type == EventType.ERROR:
            raise RuntimeError(f"Code agent error: {event.content}")
    if final_output is None:
        raise RuntimeError("Code agent did not complete")
    return final_output


DEFAULT_TASK = """
Implement the requested change in the active temporary project.

Canvas region:
- Top left near text tower of hanoi
Complexity: medium
Sub-task:
Create a simple runnable tower of hanoi game using html css and js only have 5 levels and a reset button and a move counter. The game should be playable in a web browser.
""".strip()


def main() -> None:
    try:
        logger.info("active project directory: %s", project_root())
        print(run_coder_agent(os.environ.get("PYTHIOS_CODER_TASK", DEFAULT_TASK)))
    finally:
        shutdown()


if __name__ == "__main__":
    configure_logging()
    main()
