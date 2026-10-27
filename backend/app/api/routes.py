from fastapi import APIRouter

from app.models.canvas_protocol import CanvasActionBatch, CanvasProtocolResponse
from app.models.schemas import GenerateRequest, GenerateResponse, HealthResponse
from app.pipelines.ai_core_runner import run_ai_core

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", ai="local-ready")


@router.post("/generate", response_model=GenerateResponse, response_model_exclude_none=True)
async def generate(request: GenerateRequest):
    return await run_ai_core(request)


@router.get("/canvas/protocol", response_model=CanvasProtocolResponse)
async def canvas_protocol():
    return CanvasProtocolResponse()


@router.post("/canvas/actions/validate", response_model=CanvasActionBatch, response_model_exclude_none=True)
async def validate_canvas_actions(request: CanvasActionBatch):
    return request
