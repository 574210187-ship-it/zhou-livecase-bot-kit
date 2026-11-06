from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release"))
from build_release import build


class ReleaseBuildTests(unittest.TestCase):
    def test_build_writes_manifest_and_excludes_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "safe.py").write_text("print('safe')\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git/config").write_text("not for release\n", encoding="utf-8")
            output = Path(directory) / "release.zip"
            result = build(root, output)
            self.assertEqual(len(result["files"]), 1)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("safe.py", archive.namelist())
                self.assertNotIn(".git/config", archive.namelist())
                manifest = json.loads(archive.read("RELEASE_MANIFEST.json"))
            self.assertEqual(manifest["files"][0]["path"], "safe.py")

    def test_identical_source_builds_identical_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "safe.py").write_text("print('safe')\n", encoding="utf-8")
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            first_result = build(root, first)
            second_result = build(root, second)
            self.assertEqual(first_result["zip_sha256"], second_result["zip_sha256"])
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_nested_rule_dist_is_included_but_top_level_dist_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            (root / "dist").mkdir(parents=True)
            (root / "dist/old.zip").write_bytes(b"old")
            (root / "rules/public/dist").mkdir(parents=True)
            with zipfile.ZipFile(root / "rules/public/dist/rules.zip", "w") as handle:
                handle.writestr("rules.md", "safe rules")
            output = Path(directory) / "release.zip"
            build(root, output)
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn("dist/old.zip", archive.namelist())
                self.assertIn("rules/public/dist/rules.zip", archive.namelist())
