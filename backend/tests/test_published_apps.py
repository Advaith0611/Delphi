from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import published_apps as published_api
from app.main import app
from app.services.published_apps import PublishedAppStore


def write_app(workspace: Path, body: str) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "index.html").write_text(
        f"<!doctype html><html><head><style>body{{color:red}}</style></head><body>{body}<script>window.appLoaded=true</script></body></html>",
        encoding="utf-8",
    )


class PublishedAppStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = PublishedAppStore(self.root / "published")
        self.first = self.root / "first"
        self.second = self.root / "second"
        write_app(self.first, "first version")
        write_app(self.second, "second version")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_projects_are_isolated_and_regeneration_keeps_url(self) -> None:
        self.assertTrue(self.store.publish_workspace("a1b2c3", self.first))
        self.assertTrue(self.store.publish_workspace("z9y8x7", self.second))
        self.assertIn("first version", self.store.resolve_file("a1b2c3").read_text())
        self.assertIn("second version", self.store.resolve_file("z9y8x7").read_text())

        write_app(self.first, "updated version")
        self.assertTrue(self.store.publish_workspace("a1b2c3", self.first))
        self.assertIn("updated version", self.store.resolve_file("a1b2c3").read_text())
        self.assertIn("second version", self.store.resolve_file("z9y8x7").read_text())

    def test_invalid_html_and_failed_manifest_preserve_previous_version(self) -> None:
        self.assertTrue(self.store.publish_workspace("a1b2c3", self.first))
        original = self.store.resolve_file("a1b2c3").read_text()
        (self.first / "index.html").write_text("incomplete", encoding="utf-8")
        self.assertFalse(self.store.publish_workspace("a1b2c3", self.first))
        self.assertEqual(original, self.store.resolve_file("a1b2c3").read_text())

        write_app(self.first, "would fail to save")
        with patch.object(self.store, "_write_manifest", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                self.store.publish_workspace("a1b2c3", self.first)
        self.assertEqual(original, self.store.resolve_file("a1b2c3").read_text())

    def test_path_traversal_and_bad_ids_cannot_resolve_files(self) -> None:
        self.assertTrue(self.store.publish_workspace("a1b2c3", self.first))
        self.assertIsNone(self.store.resolve_file("../../etc", "passwd"))
        self.assertIsNone(self.store.resolve_file("a1b2c3", "../../etc/passwd"))
        self.assertIsNone(self.store.resolve_file("bad", "index.html"))


class PublishedAppRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = PublishedAppStore(Path(self.temporary.name) / "published")
        workspace = Path(self.temporary.name) / "workspace"
        write_app(workspace, "served application")
        self.store.publish_workspace("a1b2c3", workspace)
        self.previous_store = published_api.published_apps
        published_api.published_apps = self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        published_api.published_apps = self.previous_store
        self.temporary.cleanup()

    def test_shell_is_sandboxed_and_document_is_served_as_html(self) -> None:
        shell = self.client.get("/a1b2c3")
        self.assertEqual(shell.status_code, 200)
        self.assertIn('sandbox="allow-scripts allow-forms allow-modals"', shell.text)
        self.assertNotIn("allow-same-origin", shell.text)
        self.assertIn("/__published/a1b2c3/index.html", shell.text)

        document = self.client.get("/__published/a1b2c3/index.html", headers={"Sec-Fetch-Dest": "iframe"})
        self.assertEqual(document.status_code, 200)
        self.assertIn("text/html", document.headers["content-type"])
        self.assertIn("<script>", document.text)
        self.assertIn("<style>", document.text)
        self.assertEqual(self.client.get("/__published/a1b2c3/index.html").status_code, 404)

    def test_missing_or_invalid_projects_return_404_without_leaking_paths(self) -> None:
        for path in ("/missing", "/abcdef", "/__published/a1b2c3/../../backend/.env"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("/Users/", response.text)

    def test_github_archive_restores_an_app_when_local_cache_is_empty(self) -> None:
        class Archive:
            @staticmethod
            def get_file(project_id: str, asset_path: str = "index.html") -> bytes | None:
                if project_id != "a1b2c3" or asset_path != "index.html":
                    return None
                return b"<!doctype html><html><body>restored from GitHub</body></html>"

        previous_archive = published_api.github_published_apps
        published_api.github_published_apps = Archive()
        try:
            # Replace the local store with an empty one to model a Render restart.
            published_api.published_apps = PublishedAppStore(Path(self.temporary.name) / "empty")
            shell = self.client.get("/a1b2c3")
            self.assertEqual(shell.status_code, 200)
            document = self.client.get("/__published/a1b2c3/index.html", headers={"Sec-Fetch-Dest": "iframe"})
            self.assertEqual(document.status_code, 200)
            self.assertIn("restored from GitHub", document.text)
        finally:
            published_api.github_published_apps = previous_archive


if __name__ == "__main__":
    unittest.main()
