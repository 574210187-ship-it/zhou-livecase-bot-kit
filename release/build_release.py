from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from verify_release import scan


EXCLUDED_PARTS = {".git", ".venv", "__pycache__"}
EXCLUDED_FILES = {"PUBLIC_RELEASE.json"}


def release_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.as_posix() in EXCLUDED_FILES:
            continue
        if (relative.parts and relative.parts[0] == "dist") or any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        files.append(path)
    return sorted(files)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path, output: Path) -> dict:
    report = scan(root)
    if not report["ok"]:
        raise ValueError("release_scan_failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = release_files(root)
    manifest = {
        "schema": "zhou-release-manifest-v1",
        "files": [{"path": str(path.relative_to(root)), "sha256": sha256(path), "size": path.stat().st_size} for path in files],
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("RELEASE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    manifest["zip_sha256"] = sha256(output)
    manifest["zip_size"] = output.stat().st_size
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a scanned, deterministic release ZIP.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.root.resolve(), args.output.resolve()), ensure_ascii=False, indent=2))
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
