"""Public, sandboxed delivery for generated Pythios applications."""

from __future__ import annotations

import logging
import mimetypes
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from app.services.project_builder import PUBLISHED_ROOT
from app.services.published_apps import PublishedAppStore, is_valid_project_id


logger = logging.getLogger(__name__)
router = APIRouter()
published_apps = PublishedAppStore(PUBLISHED_ROOT)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Published app not found")


def _shell(project_id: str) -> HTMLResponse:
    if not is_valid_project_id(project_id) or not published_apps.exists(project_id):
        raise _not_found()
    source = f"/__published/{project_id}/index.html"
    document = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Pythios app {escape(project_id)}</title>
<style>html,body,iframe{{width:100%;height:100%;margin:0;border:0;overflow:hidden;background:#fff}}iframe{{display:block}}</style>
</head><body><iframe title=\"Pythios app {escape(project_id)}\" src=\"{source}\" sandbox=\"allow-scripts allow-forms allow-modals\" referrerpolicy=\"no-referrer\"></iframe></body></html>"""
    return HTMLResponse(
        document,
        headers={
            "Content-Security-Policy": "default-src 'none'; frame-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/__published/{project_id}/{asset_path:path}", include_in_schema=False)
async def published_asset(project_id: str, asset_path: str, request: Request):
    file_path = published_apps.resolve_file(project_id, asset_path)
    if file_path is None:
        raise _not_found()
    media_type, _ = mimetypes.guess_type(file_path.name)
    # The generated document is safe only in the sandboxed iframe. Modern
    # browsers set this Fetch Metadata header for iframe navigation; rejecting
    # a top-level navigation prevents the internal document URL from becoming
    # an accidental unsandboxed public execution route.
    if media_type == "text/html" and request.headers.get("sec-fetch-dest") != "iframe":
        raise _not_found()
    return FileResponse(
        file_path,
        media_type=media_type or "application/octet-stream",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store" if file_path.name == "index.html" else "public, max-age=300",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/{project_id}", include_in_schema=False)
async def published_app(project_id: str):
    return _shell(project_id)


@router.get("/{project_id}/", include_in_schema=False)
async def published_app_slash(project_id: str):
    return _shell(project_id)
