from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
COMMON = ("README.md", "contracts/transcript.json", "contracts/deep.json", "contracts/field_mapping.json")
PACKS = {
    "transcript_rule_pack_public_v1_0.zip": COMMON + ("prompts/01_transcript.md",),
    "deep_rule_pack_public_v1_0.zip": COMMON + ("prompts/02_deep.md",),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    DIST.mkdir(parents=True, exist_ok=True)
    result = {"schema": "zhou-public-rule-packs-v1", "packs": []}
    for name, members in PACKS.items():
        output = DIST / name
        manifest = []
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member in sorted(members):
                source = ROOT / member
                info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                data = source.read_bytes()
                archive.writestr(info, data)
                manifest.append({"path": member, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
            info = zipfile.ZipInfo("RULE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, json.dumps({"schema": "zhou-public-rule-pack-v1", "files": manifest}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        result["packs"].append({"path": f"dist/{name}", "sha256": digest(output), "size": output.stat().st_size})
    (DIST / "RULE_PACKS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
