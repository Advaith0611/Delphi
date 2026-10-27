"""Single-workspace coding-agent runner for generated Pythios projects.

The backend, not the model, owns IDs and paths.  A supplied project id must
already exist; an omitted id creates one random project.  This prevents an
agent from selecting other users' project directories or silently creating a
second project in an active browser session.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
import shutil
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
# Local development keeps generated projects in the repository. Production can
# point this at a mounted persistent disk (for example, Render's /var/data) so
# published projects survive deploys and service restarts.
TEMP_ROOT = Path(os.getenv("PYTHIOS_DATA_DIR", REPO_ROOT / "ai-core" / "tmp")).resolve()
PROJECTS_ROOT = TEMP_ROOT / "projects"
PUBLISHED_ROOT = TEMP_ROOT / "published"
PROJECT_ALPHABET = string.ascii_lowercase + string.digits


@dataclass
class BuildResult:
    project_id: str
    status: str
    url: str | None = None
    activity: list[str] = field(default_factory=list)
    error: str | None = None

    def as_response(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "status": self.status,
            "url": self.url,
            "activity": self.activity[-80:],
            "error": self.error,
        }


class ProjectBuilder:
    def __init__(self) -> None:
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        PUBLISHED_ROOT.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        *,
        project_id: str | None,
        brief: str,
        user_prompt: str | None,
        screenshot_data_url: str | None,
    ) -> BuildResult:
        try:
            resolved_id, created = self._resolve_project(project_id)
        except ValueError as error:
            return BuildResult(project_id=project_id or "unknown", status="failed", error=str(error))

        workspace = PROJECTS_ROOT / resolved_id
        metadata = self._load_metadata(resolved_id)
        activity = [
            f"Project {resolved_id}: {'created' if created else 'loaded existing workspace'}.",
            "Saved the current whiteboard screenshot and Gemini project brief.",
        ]

        screenshot_path = self._save_screenshot(workspace, screenshot_data_url)
        self._write_agent_brief(workspace, brief, user_prompt, screenshot_path)

        try:
            agent_result = asyncio.run(
                self._run_agent(
                    workspace=workspace,
                    project_id=resolved_id,
                    brief=brief,
                    user_prompt=user_prompt,
                    screenshot_path=screenshot_path,
                    previous_session_id=metadata.get("agentSessionId"),
                )
            )
            activity.extend(agent_result["activity"])
            agent_session_id = agent_result.get("session_id")
        except Exception as error:  # Keep canvas generation useful when a harness is misconfigured.
            return BuildResult(
                project_id=resolved_id,
                status="failed",
                activity=activity,
                error=f"Coding agent did not run: {error}",
            )

        published = self._publish_workspace(resolved_id, workspace)
        metadata.update(
            {
                "projectId": resolved_id,
                "agentSessionId": agent_session_id or metadata.get("agentSessionId"),
                "lastBrief": brief,
                "published": bool(published),
            }
        )
        self._save_metadata(resolved_id, metadata)

        if not published:
            return BuildResult(
                project_id=resolved_id,
                status="failed",
                activity=activity,
                error="The agent finished, but no publishable artifact was found. It must create index.html or a dist/ or build/ directory.",
            )

        public_base = os.getenv("PYTHIOS_PUBLIC_APP_URL", "https://app.pythios.xyz").rstrip("/")
        return BuildResult(
            project_id=resolved_id,
            status="created" if created else "updated",
            url=f"{public_base}/{resolved_id}/",
            activity=activity,
        )

    def _resolve_project(self, requested_id: str | None) -> tuple[str, bool]:
        if requested_id:
            if not self._is_valid_project_id(requested_id):
                raise ValueError("Project IDs must be six lowercase letters or numbers.")
            if not (PROJECTS_ROOT / requested_id).is_dir():
                raise ValueError(f"Project {requested_id} does not exist. Clear the project ID to create a new project.")
            return requested_id, False

        while True:
            candidate = "".join(secrets.choice(PROJECT_ALPHABET) for _ in range(6))
            if not (PROJECTS_ROOT / candidate).exists() and not (PUBLISHED_ROOT / candidate).exists():
                (PROJECTS_ROOT / candidate).mkdir(parents=True, exist_ok=False)
                return candidate, True

    @staticmethod
    def _is_valid_project_id(value: str) -> bool:
        return len(value) == 6 and all(character in PROJECT_ALPHABET for character in value)

    def _metadata_path(self, project_id: str) -> Path:
        return PROJECTS_ROOT / f"{project_id}.json"

    def _load_metadata(self, project_id: str) -> dict[str, Any]:
        path = self._metadata_path(project_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_metadata(self, project_id: str, metadata: dict[str, Any]) -> None:
        self._metadata_path(project_id).write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    @staticmethod
    def _save_screenshot(workspace: Path, data_url: str | None) -> Path | None:
        if not data_url or "," not in data_url:
            return None
        try:
            image_data = base64.b64decode(data_url.split(",", 1)[1], validate=True)
        except (ValueError, base64.binascii.Error):
            return None
        input_dir = workspace / ".pythios"
        input_dir.mkdir(exist_ok=True)
        screenshot = input_dir / "whiteboard.png"
        screenshot.write_bytes(image_data)
        return screenshot

    @staticmethod
    def _write_agent_brief(workspace: Path, brief: str, user_prompt: str | None, screenshot_path: Path | None) -> None:
        internal = workspace / ".pythios"
        internal.mkdir(exist_ok=True)
        text = "# Pythios project brief\n\n" + brief.strip() + "\n"
        if user_prompt:
            text += f"\n## Latest user request\n\n{user_prompt.strip()}\n"
        if screenshot_path:
            text += "\n## Whiteboard image\n\n`.pythios/whiteboard.png` is the current whiteboard screenshot.\n"
        (internal / "brief.md").write_text(text, encoding="utf-8")

    async def _run_agent(
        self,
        *,
        workspace: Path,
        project_id: str,
        brief: str,
        user_prompt: str | None,
        screenshot_path: Path | None,
        previous_session_id: str | None,
    ) -> dict[str, Any]:
        try:
            from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, ToolUseBlock, query
        except ImportError as error:
            raise RuntimeError("claude-agent-sdk is not installed. Install backend requirements first.") from error

        model = os.getenv("PYTHIOS_CODING_MODEL", "anthropic/claude-opus-5.5:batch")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api")
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing from backend/.env")

        # The agent receives a private working directory. Claude Code's own
        # sandbox is also enabled; production should run this backend in a
        # container that mounts only this workspace.
        settings = json.dumps(
            {
                "permissions": {
                    "allow": [
                        {"tool": tool, "ruleContent": f"{workspace}/**"}
                        for tool in ("Read", "Write", "Edit", "Glob", "Grep", "Bash")
                    ]
                }
            }
        )
        options = ClaudeAgentOptions(
            cwd=workspace,
            model=model,
            resume=previous_session_id,
            max_turns=int(os.getenv("PYTHIOS_AGENT_MAX_TURNS", "36")),
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
            disallowed_tools=["WebFetch", "WebSearch"],
            permission_mode="dontAsk",
            setting_sources=[],
            settings=settings,
            sandbox={
                "enabled": True,
                "autoAllowBashIfSandboxed": True,
                "allowUnsandboxedCommands": False,
            },
            env={
                "ANTHROPIC_BASE_URL": base_url,
                "ANTHROPIC_AUTH_TOKEN": api_key,
                "ANTHROPIC_API_KEY": api_key,
                "API_TIMEOUT_MS": "300000",
                "CLAUDE_CODE_MAX_RETRIES": "2",
            },
        )

        screenshot_note = (
            "Inspect `.pythios/whiteboard.png` with the Read tool if visual detail is useful."
            if screenshot_path
            else "No screenshot was available for this request."
        )
        task = f"""
You are the sole implementation agent for Pythios project {project_id}.
You are editing an existing project workspace. Never create, select, delete, or modify another project.
Only create or change files under your current working directory.

Read `.pythios/brief.md` first. {screenshot_note}

Gemini's current project interpretation:
{brief}

Latest user instruction:
{user_prompt or 'Build or improve the artifact described by the whiteboard.'}

Build the requested artifact. It may be a website, interactive simulation, presentation, dashboard, or other browser-viewable artifact.
Keep it self-contained where practical. Inspect existing files before changing them and preserve useful prior work.
For publishability, leave either an `index.html` at the workspace root or a completed `dist/` or `build/` directory. Run the relevant build or validation command when available and fix obvious failures.
Do not expose API keys, read files outside this workspace, or claim success without checking the output.
""".strip()

        activity: list[str] = [f"Coding agent started with {model}."]
        session_id: str | None = None
        async for message in query(prompt=task, options=options):
            if isinstance(message, AssistantMessage):
                for block in getattr(message, "content", []):
                    if isinstance(block, ToolUseBlock):
                        name = getattr(block, "name", "tool")
                        activity.append(f"Agent is using {name}.")
            if isinstance(message, ResultMessage):
                session_id = getattr(message, "session_id", None)
                result_text = getattr(message, "result", "")
                if result_text:
                    activity.append("Agent completed its implementation pass.")

        return {"activity": _deduplicate(activity), "session_id": session_id}

    @staticmethod
    def _publish_workspace(project_id: str, workspace: Path) -> bool:
        source = next(
            (
                candidate
                for candidate in (workspace / "dist", workspace / "build", workspace)
                if (candidate / "index.html").is_file()
            ),
            None,
        )
        if source is None:
            return False

        destination = PUBLISHED_ROOT / project_id
        staging = PUBLISHED_ROOT / f".{project_id}.staging"
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(
            source,
            staging,
            ignore=shutil.ignore_patterns(".pythios", ".git", "node_modules", "__pycache__", ".env", ".env.*"),
        )
        if destination.exists():
            shutil.rmtree(destination)
        staging.rename(destination)
        return True


def _deduplicate(entries: list[str]) -> list[str]:
    unique: list[str] = []
    for entry in entries:
        if not unique or unique[-1] != entry:
            unique.append(entry)
    return unique
