#!/usr/bin/env python3
"""Fail closed when a proposed release contains secrets or host-specific paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

FORBIDDEN = (
    re.compile(r"https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=", re.I),
    re.compile(r"(?:AKID|secretid|secretkey|authorization:\s*bearer)", re.I),
    re.compile(r"/Users/[^/]+/"),
    re.compile(r"\b(?:tbl|rec)[A-Za-z0-9]{10,}\b"),
    re.compile(r"https?://[^\s/]*feishu\.cn/base/", re.I),
)
SKIP_PARTS = {".git", "__pycache__", ".venv"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt"}
SKIP_FILES = {"release/verify_release.py", "tests/test_release_guard.py"}


def excluded_from_release(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return (relative.parts and relative.parts[0] == "dist") or any(part in SKIP_PARTS for part in relative.parts)


def iter_release_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or excluded_from_release(path, root):
            continue
        if path.relative_to(root).as_posix() in SKIP_FILES:
            # These files contain the forbidden-pattern test definitions themselves.
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        yield path


def scan(root: Path) -> dict:
    violations: list[dict[str, str]] = []
    files: list[dict[str, str]] = []
    for path in iter_release_files(root):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        files.append({"path": relative, "sha256": hashlib.sha256(text.encode()).hexdigest()})
        for pattern in FORBIDDEN:
            if pattern.search(text):
                violations.append({"path": relative, "pattern": pattern.pattern})
    for archive_path in sorted(root.rglob("*.zip")):
        if excluded_from_release(archive_path, root):
            continue
        relative_archive = archive_path.relative_to(root).as_posix()
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in sorted(archive.namelist()):
                    if Path(member).suffix not in TEXT_SUFFIXES:
                        continue
                    try:
                        text = archive.read(member).decode("utf-8")
                    except UnicodeDecodeError:
                        violations.append({"path": f"{relative_archive}!{member}", "pattern": "non_utf8_text_member"})
                        continue
                    for pattern in FORBIDDEN:
                        if pattern.search(text):
                            violations.append({"path": f"{relative_archive}!{member}", "pattern": pattern.pattern})
        except zipfile.BadZipFile:
            violations.append({"path": relative_archive, "pattern": "bad_zip_file"})
    return {"schema": "zhou-release-scan-v1", "files": files, "violations": violations, "ok": not violations}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = scan(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

