"""Atomic storage and safe lookup for public generated applications."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Iterator
from uuid import uuid4


PROJECT_ID_RE = re.compile(r"^[a-z0-9]{6}$")
VERSION_RE = re.compile(r"^[a-f0-9]{32}$")
IGNORED_BUILD_FILES = (".pythios", ".git", "node_modules", "__pycache__", ".env", ".env.*")


def is_valid_project_id(value: str) -> bool:
    return bool(PROJECT_ID_RE.fullmatch(value))


class PublishedAppStore:
    """Stores immutable app versions and atomically switches a project manifest.

    Reading always resolves a small manifest first. A failed build or copy never
    changes that manifest, so visitors continue to receive the last good app.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.versions_root = root / ".versions"
        self.locks_root = root / ".locks"
        self.root.mkdir(parents=True, exist_ok=True)
        self.versions_root.mkdir(exist_ok=True)
        self.locks_root.mkdir(exist_ok=True)

    def publish_workspace(self, project_id: str, workspace: Path, *, lock: bool = True) -> bool:
        if not is_valid_project_id(project_id):
            raise ValueError("Invalid project ID")

        source = next(
            (
                candidate
                for candidate in (workspace / "dist", workspace / "build", workspace)
                if (candidate / "index.html").is_file()
            ),
            None,
        )
        if source is None or not self._is_complete_html(source / "index.html"):
            return False

        with (self._project_lock(project_id) if lock else nullcontext()):
            version = uuid4().hex
            project_versions = self.versions_root / project_id
            project_versions.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=f".{project_id}-", dir=project_versions))
            version_dir = project_versions / version
            try:
                shutil.copytree(source, staging, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORED_BUILD_FILES))
                if not self._is_complete_html(staging / "index.html"):
                    return False
                os.replace(staging, version_dir)
                self._write_manifest(project_id, version)
            except Exception:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)
                if version_dir.exists():
                    shutil.rmtree(version_dir, ignore_errors=True)
                raise
        return True

    def project_lock(self, project_id: str) -> Iterator[None]:
        """Serialize complete project updates, including the agent workspace."""
        if not is_valid_project_id(project_id):
            raise ValueError("Invalid project ID")
        return self._project_lock(project_id)

    def resolve_file(self, project_id: str, asset_path: str = "index.html") -> Path | None:
        if not is_valid_project_id(project_id):
            return None
        if not asset_path or asset_path.endswith("/"):
            asset_path = f"{asset_path}index.html"
        candidate_path = Path(asset_path)
        if candidate_path.is_absolute() or ".." in candidate_path.parts:
            return None

        app_root = self._resolve_app_root(project_id)
        if app_root is None:
            return None
        candidate = (app_root / candidate_path).resolve()
        try:
            candidate.relative_to(app_root.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def exists(self, project_id: str) -> bool:
        return self.resolve_file(project_id) is not None

    def _resolve_app_root(self, project_id: str) -> Path | None:
        manifest = self.root / f"{project_id}.json"
        if manifest.is_file():
            try:
                version = json.loads(manifest.read_text(encoding="utf-8")).get("version", "")
            except (OSError, json.JSONDecodeError):
                return None
            if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
                return None
            root = self.versions_root / project_id / version
            return root if (root / "index.html").is_file() else None

        # Existing projects from before atomic publishing remain readable.
        legacy_root = self.root / project_id
        return legacy_root if (legacy_root / "index.html").is_file() else None

    def _write_manifest(self, project_id: str, version: str) -> None:
        destination = self.root / f"{project_id}.json"
        fd, temp_name = tempfile.mkstemp(prefix=f".{project_id}-", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": version}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, destination)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _is_complete_html(path: Path) -> bool:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            return False
        return len(content) >= 32 and "<html" in content.lower() and "</html>" in content.lower()

    @contextmanager
    def _project_lock(self, project_id: str) -> Iterator[None]:
        """Use a Render/Linux advisory lock when available for shared-disk writers."""
        lock_path = self.locks_root / f"{project_id}.lock"
        with lock_path.open("a+") as handle:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError:  # pragma: no cover - Windows local development
                pass
            try:
                yield
            finally:
                try:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except ImportError:  # pragma: no cover - Windows local development
                    pass
