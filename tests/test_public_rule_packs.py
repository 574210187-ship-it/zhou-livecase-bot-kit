from __future__ import annotations

import hashlib
import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULE_ROOT = ROOT / "rules/public-v1.0"


class PublicRulePackTests(unittest.TestCase):
    def test_both_rule_packs_have_manifest_and_expected_prompt(self) -> None:
        registry = json.loads((RULE_ROOT / "dist/RULE_PACKS.json").read_text(encoding="utf-8"))
        self.assertEqual(len(registry["packs"]), 2)
        for item in registry["packs"]:
            path = RULE_ROOT / item["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
            with zipfile.ZipFile(path) as archive:
                self.assertIn("RULE_MANIFEST.json", archive.namelist())
                self.assertIn("README.md", archive.namelist())
                manifest = json.loads(archive.read("RULE_MANIFEST.json"))
                listed = {entry["path"] for entry in manifest["files"]}
                self.assertIn("contracts/transcript.json", listed)
                self.assertIn("contracts/deep.json", listed)

    def test_rule_archives_contain_no_private_target_ids_or_host_paths(self) -> None:
        forbidden = ("/" + "Users/", "my.feishu.cn/base/", "tbl", "reczz", "qyapi.weixin.qq.com")
        for path in (RULE_ROOT / "dist").glob("*.zip"):
            with zipfile.ZipFile(path) as archive:
                text = "\n".join(
                    archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if Path(name).suffix in {".md", ".json", ".py", ".txt"}
                )
            for marker in forbidden:
                self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
