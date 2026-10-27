from __future__ import annotations

import anyio
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from app.models.canvas_protocol import CanvasActionBatch
from app.models.schemas import GenerateRequest, GenerateResponse, GeneratedUI, ProjectBuildInfo


REPO_ROOT = Path(__file__).resolve().parents[3]
AI_CORE_DIR = REPO_ROOT / "ai-core"
AI_CORE_MAIN = AI_CORE_DIR / "main.py"


async def run_ai_core(request: GenerateRequest) -> GenerateResponse:
    """Run the synchronous user-owned AI Core outside FastAPI's event loop."""
    return await anyio.to_thread.run_sync(_run_ai_core_sync, request)


def _run_ai_core_sync(request: GenerateRequest) -> GenerateResponse:
    module = _load_ai_core_main()
    payload = request.model_dump(mode="json")
    raw_result = _call_run(module, payload)
    action_batch, generated_ui = _normalize_ai_core_result(raw_result)
    project = _project_info(raw_result)

    return GenerateResponse(actionBatch=action_batch, generatedUI=generated_ui, project=project)


def _load_ai_core_main() -> ModuleType:
    if not AI_CORE_MAIN.exists():
        raise FileNotFoundError(f"AI Core entry point not found: {AI_CORE_MAIN}")

    ai_core_path = str(AI_CORE_DIR)
    if ai_core_path not in sys.path:
        sys.path.insert(0, ai_core_path)

    module_name = f"pythios_ai_core_main_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, AI_CORE_MAIN)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load AI Core entry point: {AI_CORE_MAIN}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _call_run(module: ModuleType, payload: dict):
    run = getattr(module, "run", None)
    if run is None:
        return None
    if not callable(run):
        raise TypeError("ai-core/main.py must expose a callable run entry point")

    canvas_state = payload.get("canvasState")
    visual_context = payload.get("visualContext")
    prompt = payload.get("prompt")
    call_values = {
        "canvas_state": canvas_state,
        "visual_context": visual_context,
        "prompt": prompt,
        "request": payload,
    }

    signature = inspect.signature(run)
    parameters = signature.parameters

    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return run(**call_values)

    keyword_args = {
        name: value
        for name, value in call_values.items()
        if name in parameters
    }
    if keyword_args:
        return run(**keyword_args)

    positional = [
        parameter
        for parameter in parameters.values()
        if parameter.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
    ]
    if len(positional) == 0:
        return run()
    if len(positional) == 1:
        return run(canvas_state)
    if len(positional) == 2:
        return run(canvas_state, visual_context)
    if len(positional) == 3:
        return run(canvas_state, visual_context, prompt)

    return run(canvas_state, visual_context, prompt, payload)


def _normalize_ai_core_result(raw_result) -> tuple[CanvasActionBatch, GeneratedUI | None]:
    if raw_result is None:
        return CanvasActionBatch(), None

    if isinstance(raw_result, list):
        return CanvasActionBatch(actions=raw_result), None

    if isinstance(raw_result, CanvasActionBatch):
        return raw_result, None

    if isinstance(raw_result, GeneratedUI):
        return CanvasActionBatch(), raw_result

    if not isinstance(raw_result, dict):
        raise TypeError("AI Core run() must return an action batch dict, action list, GenerateResponse-like dict, or None")

    if "actionBatch" in raw_result or "generatedUI" in raw_result:
        action_batch = CanvasActionBatch.model_validate(raw_result.get("actionBatch") or {})
        generated_ui_payload = raw_result.get("generatedUI")
        generated_ui = GeneratedUI.model_validate(generated_ui_payload) if generated_ui_payload else None
        return action_batch, generated_ui

    if "actions" in raw_result:
        return CanvasActionBatch.model_validate(raw_result), None

    return CanvasActionBatch(), None


def _project_info(raw_result) -> ProjectBuildInfo | None:
    if not isinstance(raw_result, dict) or not raw_result.get("project"):
        return None
    return ProjectBuildInfo.model_validate(raw_result["project"])
