"""Public, sandboxed delivery for generated Pythios applications."""

from __future__ import annotations

import logging
import mimetypes
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request as UrlRequest, urlopen
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.services.project_builder import PUBLISHED_ROOT
from app.services.published_apps import PublishedAppStore, is_valid_project_id


logger = logging.getLogger(__name__)
router = APIRouter()
published_apps = PublishedAppStore(PUBLISHED_ROOT)


class GitHubPublishedApps:
    """Read durable published versions from the optional GitHub archive.

    Render's local filesystem is only a cache when no persistent disk is
    attached. The archive manifest is updated after a complete version upload,
    so an interrupted generation continues to expose the previous version.
    """

    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_TOKEN", "").strip()
        self.repository = os.getenv("GITHUB_REPOSITORY", "").strip().strip("/")
        self.branch = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
        self.archive_path = os.getenv("GITHUB_ARCHIVE_PATH", "generated-projects").strip("/")

    @property
    def enabled(self) -> bool:
        return self.repository.count("/") == 1 and bool(self.archive_path)

    def get_file(self, project_id: str, asset_path: str = "index.html") -> bytes | None:
        if not self.enabled or not is_valid_project_id(project_id):
            return None
        normalized = self._asset_path(asset_path)
        if normalized is None:
            return None
        version = self._version(project_id)
        if version:
            return self._get(f"{self.archive_path}/{project_id}/.versions/{version}/{normalized}")
        # Compatibility with archives uploaded before versioned publishing.
        return self._get(f"{self.archive_path}/{project_id}/{normalized}")

    @staticmethod
    def _asset_path(asset_path: str) -> str | None:
        if not asset_path or asset_path.endswith("/"):
            asset_path = f"{asset_path}index.html"
        pieces = asset_path.replace("\\", "/").split("/")
        if any(not piece or piece in {".", ".."} for piece in pieces):
            return None
        return "/".join(pieces)

    def _version(self, project_id: str) -> str | None:
        payload = self._get(f"{self.archive_path}/{project_id}/.published.json")
        if payload is None:
            return None
        try:
            version = json.loads(payload.decode("utf-8")).get("version")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return version if isinstance(version, str) and len(version) == 32 and all(char in "0123456789abcdef" for char in version) else None

    def _get(self, path: str) -> bytes | None:
        url = f"https://api.github.com/repos/{self.repository}/contents/{quote(path, safe='/')}?ref={quote(self.branch, safe='')}"
        headers = {
            "Accept": "application/vnd.github.raw+json",
            "User-Agent": "pythios-published-apps",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(UrlRequest(url, headers=headers), timeout=15) as response:
                return response.read()
        except HTTPError as error:
            if error.code != 404:
                logger.warning("GitHub archive request failed with HTTP %s", error.code)
            return None
        except URLError:
            logger.warning("GitHub archive is unavailable")
            return None


github_published_apps = GitHubPublishedApps()


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Published app not found")


def _shell(project_id: str) -> HTMLResponse:
    if not is_valid_project_id(project_id) or not _exists(project_id):
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
    name = file_path.name if file_path is not None else asset_path.rsplit("/", 1)[-1]
    media_type, _ = mimetypes.guess_type(name)
    # The generated document is safe only in the sandboxed iframe. Modern
    # browsers set this Fetch Metadata header for iframe navigation; rejecting
    # a top-level navigation prevents the internal document URL from becoming
    # an accidental unsandboxed public execution route.
    if media_type == "text/html" and request.headers.get("sec-fetch-dest") != "iframe":
        raise _not_found()
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store" if name == "index.html" else "public, max-age=300",
        "Referrer-Policy": "no-referrer",
    }
    if file_path is not None:
        return FileResponse(file_path, media_type=media_type or "application/octet-stream", headers=headers)
    content = github_published_apps.get_file(project_id, asset_path)
    if content is None:
        raise _not_found()
    return Response(content=content, media_type=media_type or "application/octet-stream", headers=headers)


def _exists(project_id: str) -> bool:
    return published_apps.exists(project_id) or github_published_apps.get_file(project_id) is not None


@router.get("/{project_id}", include_in_schema=False)
async def published_app(project_id: str):
    return _shell(project_id)


@router.get("/{project_id}/", include_in_schema=False)
async def published_app_slash(project_id: str):
    return _shell(project_id)
