from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from release.verify_release import scan


class ReleaseGuardTests(unittest.TestCase):
    def test_clean_source_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "clean.py").write_text("print('safe')\n", encoding="utf-8")
            self.assertTrue(scan(root)["ok"])

    def test_webhook_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.md").write_text("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=REDACTED", encoding="utf-8")
            result = scan(root)
            self.assertFalse(result["ok"])
            self.assertEqual(result["violations"][0]["path"], "bad.md")

    def test_host_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.py").write_text("ROOT='/Users/example/private'", encoding="utf-8")
            self.assertFalse(scan(root)["ok"])

    def test_realistic_feishu_table_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.json").write_text('{"table":"tblABCDEFGHIJKLMN"}', encoding="utf-8")
            self.assertFalse(scan(root)["ok"])

    def test_feishu_base_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.md").write_text("https://example.feishu.cn/base/PRIVATE", encoding="utf-8")
            self.assertFalse(scan(root)["ok"])

    def test_bearer_authorization_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = "Authorization" + ": Bearer private-value"
            (root / "bad.txt").write_text(header, encoding="utf-8")
            self.assertFalse(scan(root)["ok"])

    def test_nested_rule_zip_is_scanned(self) -> None:
        import zipfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "rules/public/dist"
            nested.mkdir(parents=True)
            archive = nested / "rules.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("bad.json", '{"table":"tblABCDEFGHIJKLMN"}')
            self.assertFalse(scan(root)["ok"])

