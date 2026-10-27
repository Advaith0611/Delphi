from typing import Literal

from pydantic import BaseModel, Field

from app.models.canvas_protocol import CanvasActionBatch, CanvasState, CanvasVisualContext


class SpatialShape(BaseModel):
    id: str
    type: str
    x: float = 0
    y: float = 0
    w: float = 120
    h: float = 72
    text: str | None = None
    geo: str | None = None
    color: str | None = None


class GenerateRequest(BaseModel):
    shapes: list[SpatialShape] = Field(default_factory=list)
    canvasState: CanvasState | None = None
    visualContext: CanvasVisualContext | None = None
    prompt: str | None = None
    selectedOnly: bool = False
    projectId: str | None = Field(default=None, pattern=r"^[a-z0-9]{6}$")


class ProjectBuildInfo(BaseModel):
    projectId: str
    url: str | None = None
    status: Literal["created", "updated", "failed"]
    activity: list[str] = Field(default_factory=list)
    error: str | None = None


class GeneratedComponent(BaseModel):
    id: str
    type: Literal[
        "metric",
        "chart",
        "table",
        "button",
        "input",
        "list",
        "kanban",
        "timeline",
        "workflow",
        "note",
    ]
    title: str
    label: str | None = None
    value: str | None = None
    detail: str | None = None
    items: list[str] | None = None
    columns: list[str] | None = None
    rows: list[dict[str, str | int | float]] | None = None
    accent: str | None = None


class GeneratedUI(BaseModel):
    id: str
    app_type: str
    title: str
    summary: str
    theme: Literal["light", "dark"] = "dark"
    layout: Literal["dashboard", "app", "workflow", "wireframe"] = "dashboard"
    generated_at: str
    source: Literal["backend", "local"] = "backend"
    components: list[GeneratedComponent]


class GenerateResponse(BaseModel):
    actionBatch: CanvasActionBatch = Field(default_factory=CanvasActionBatch)
    generatedUI: GeneratedUI | None = None
    source: Literal["ai-core"] = "ai-core"
    project: ProjectBuildInfo | None = None


class HealthResponse(BaseModel):
    status: str
    ai: str
