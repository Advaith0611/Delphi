"""Public, sandboxed delivery for generated Pythios applications."""

from __future__ import annotations

import logging
import mimetypes
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
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

    def list_project_ids(self) -> list[str]:
        """List durable archive folders so the directory survives a restart."""
        if not self.enabled:
            return []
        url = f"https://api.github.com/repos/{self.repository}/contents/{quote(self.archive_path, safe='/')}?ref={quote(self.branch, safe='')}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "pythios-published-apps"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(UrlRequest(url, headers=headers), timeout=15) as response:
                entries = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("GitHub archive directory is unavailable")
            return []
        if not isinstance(entries, list):
            return []
        return sorted(
            entry["name"] for entry in entries
            if isinstance(entry, dict) and entry.get("type") == "dir"
            and isinstance(entry.get("name"), str) and is_valid_project_id(entry["name"])
        )

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


def _embed_origins() -> str:
    """Origins permitted to put a published-app shell in an iframe."""
    configured = os.getenv(
        "PYTHIOS_EMBED_ORIGINS",
        "https://pythios.xyz,https://www.pythios.xyz,https://delphi.pythios.xyz,https://app.pythios.xyz",
    )
    origins: list[str] = []
    for candidate in configured.split(","):
        value = candidate.strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme == "https" and parsed.netloc and not parsed.path and not parsed.params and not parsed.query and not parsed.fragment:
            origins.append(value)
    return " ".join(origins) or "'none'"


def _directory(query: str = "") -> HTMLResponse:
    project_ids = sorted(set(published_apps.list_project_ids()) | set(github_published_apps.list_project_ids()))
    search = query.strip().lower()
    if search:
        project_ids = [project_id for project_id in project_ids if search in project_id]
    project_cards = "".join(
        f'''<li class="project-card"><div class="preview"><iframe title="Preview of {escape(project_id)}" src="/{escape(project_id)}" loading="lazy" tabindex="-1"></iframe></div><div class="card-footer"><strong>{escape(project_id)}</strong><a href="/{escape(project_id)}">Open project <span aria-hidden="true">→</span></a></div></li>'''
        for project_id in project_ids
    ) or ('<li class="empty">No projects match that ID.</li>' if search else '<li class="empty">No published projects yet.</li>')
    search_value = escape(query, quote=True)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pythios projects</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600&display=swap');*{{box-sizing:border-box}}body{{margin:0;background:#f3efe6;color:#181818;font:400 16px Inter,system-ui,sans-serif}}main{{width:min(1120px,calc(100% - 40px));margin:64px auto 80px}}h1{{margin:0;font:400 clamp(2.8rem,6vw,4.8rem)/.95 'Instrument Serif',Georgia,serif;letter-spacing:-.035em}}h1 em{{font-style:italic;color:#bfa15f}}p{{color:#6e6858;max-width:620px;line-height:1.55;margin:12px 0 0}}form{{margin:30px 0}}input{{width:min(440px,100%);padding:13px 15px;border:1.5px solid rgba(0,0,0,.12);border-radius:9px;background:#fffdf5;color:#181818;font:400 14px Inter,system-ui,sans-serif;outline:none}}input:focus{{border-color:#bfa15f;box-shadow:0 0 0 3px rgba(191,161,95,.18)}}ul{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;padding:0;list-style:none;margin:0}}.project-card{{overflow:hidden;border-radius:16px;background:#fffdf5;box-shadow:0 10px 30px rgba(0,0,0,.06),0 0 0 1px rgba(0,0,0,.05)}}.preview{{height:210px;background:#fff;overflow:hidden;pointer-events:none;border-bottom:1px solid rgba(0,0,0,.08)}}iframe{{display:block;width:100%;height:100%;border:0;background:#fff}}.card-footer{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 17px}}.card-footer strong{{font:500 13px Inter,system-ui,sans-serif;letter-spacing:.02em;color:#6e6858}}.card-footer a{{color:#181818;text-decoration:none;font-size:14px;font-weight:500}}.card-footer a span{{color:#bfa15f;font-size:18px;vertical-align:-1px}}.card-footer a:hover{{color:#7a6e3a}}.empty{{color:#6e6858}}</style>
</head><body><main><h1>Published <em>projects</em></h1><p>Preview a project, or search by its project ID.</p><form action="/" method="get"><label for="project-search" style="position:absolute;left:-9999px">Search project ID</label><input id="project-search" name="q" type="search" value="{search_value}" placeholder="Search project ID" autocomplete="off" spellcheck="false"></form><ul>{project_cards}</ul></main></body></html>"""
    return HTMLResponse(document, headers={
        "Content-Security-Policy": "default-src 'none'; frame-src 'self'; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; base-uri 'none'; form-action 'self'; frame-ancestors " + _embed_origins(),
        "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
    })


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
            "Content-Security-Policy": "default-src 'none'; frame-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors " + _embed_origins(),
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


@router.get("/", include_in_schema=False)
async def published_app_directory(q: str = ""):
    return _directory(q)


@router.get("/{project_id}", include_in_schema=False)
async def published_app(project_id: str):
    return _shell(project_id)


@router.get("/{project_id}/", include_in_schema=False)
async def published_app_slash(project_id: str):
    return _shell(project_id)
