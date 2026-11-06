from __future__ import annotations

import re
from typing import Any


REQUIRED_VISIBLE_FIELDS = (
    "故事标题",
    "故事概要",
    "主方向",
    "次方向",
    "看事索引",
    "单麦作用及依据",
    "可借鉴元素",
    "禁借元素",
)

INTERNAL_CODE = re.compile(
    r"(?:resume_execution_result|blocked_[a-z_]+|CONTENT_REVIEW|internal[_ -]?id|"
    r"debug|traceback|placeholder|TODO|\bNone\b|\bnull\b|普通案例麦(?![^，。；：]{2,}))",
    re.I,
)
RAW_MACHINE_DUMP = re.compile(r"(?:\{\s*[\"'][^\n]{0,40}[\"']\s*:|\[\s*\{)")
VISIBLE_URL = re.compile(r"(?:https?://|feishu-attachment://|cos://)", re.I)
FACT_NUMBER = re.compile(
    r"(?:\d+(?:\.\d+)?|[一二三四五六七八九十百千万两零〇]+)"
    r"(?:岁|年|个月|月|天|万|元|块|%|％|桌|人|次|个)"
)


def _issue(code: str, *, boundary_id: str, field: str, detail: str) -> dict[str, str]:
    return {"code": code, "boundary_id": boundary_id, "field": field, "detail": detail}


def _normalise_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _facts(text: str) -> set[str]:
    return {match.group(0).replace("％", "%") for match in FACT_NUMBER.finditer(text)}


def validate_visible_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate human-facing Chinese cells and their verbatim evidence.

    This gate is intentionally deterministic and conservative.  Passing it is
    necessary but not sufficient: the independent auditor still reviews the
    actual target rows after writing.
    """

    if payload.get("schema") != "zhou-visible-payload-v1":
        raise ValueError("visible_payload_schema")
    source_text = _normalise_text(str(payload.get("source_text") or ""))
    source_identity = payload.get("source_identity") or {}
    boundaries = payload.get("boundaries")
    if not isinstance(boundaries, list) or not boundaries:
        raise ValueError("visible_payload_boundaries")
    issues: list[dict[str, str]] = []
    seen: set[str] = set()
    for boundary in boundaries:
        boundary_id = str(boundary.get("boundary_id") or "")
        if not boundary_id or boundary_id in seen:
            issues.append(_issue("BOUNDARY_ID_INVALID", boundary_id=boundary_id, field="boundary_id", detail="边界编号为空或重复"))
            continue
        seen.add(boundary_id)
        local_identity = boundary.get("source_identity") or source_identity
        for name in ("record_id", "recording_name"):
            expected = str(source_identity.get(name) or "")
            actual = str(local_identity.get(name) or "")
            if expected and actual != expected:
                issues.append(_issue("SOURCE_IDENTITY_MISMATCH", boundary_id=boundary_id, field=name, detail="边界来源与本批来源不一致"))
        cells = boundary.get("cells")
        if not isinstance(cells, dict):
            issues.append(_issue("VISIBLE_CELLS_MISSING", boundary_id=boundary_id, field="cells", detail="缺少人看字段"))
            continue
        for field in REQUIRED_VISIBLE_FIELDS:
            value = cells.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(_issue("VISIBLE_FIELD_EMPTY", boundary_id=boundary_id, field=field, detail="必填字段为空"))
                continue
            text = value.strip()
            if not re.search(r"[\u3400-\u9fff]", text):
                issues.append(_issue("VISIBLE_FIELD_NOT_CHINESE", boundary_id=boundary_id, field=field, detail="字段不是可读中文"))
            if INTERNAL_CODE.search(text):
                issues.append(_issue("VISIBLE_FIELD_INTERNAL_CODE", boundary_id=boundary_id, field=field, detail="字段含内部状态码、占位词或无解释模板"))
            if RAW_MACHINE_DUMP.search(text):
                issues.append(_issue("VISIBLE_FIELD_MACHINE_DUMP", boundary_id=boundary_id, field=field, detail="字段含机器 JSON 转储"))
            if VISIBLE_URL.search(text):
                issues.append(_issue("VISIBLE_FIELD_URL", boundary_id=boundary_id, field=field, detail="业务说明字段不得写存储地址"))
        title = str(cells.get("故事标题") or "")
        if len(title.strip()) < 6 or len(title.strip()) > 60:
            issues.append(_issue("TITLE_LENGTH", boundary_id=boundary_id, field="故事标题", detail="标题需为 6 至 60 个字符"))
        if re.search(r"[，。！？；：、,.!?;:]", title):
            issues.append(_issue("TITLE_PUNCTUATION", boundary_id=boundary_id, field="故事标题", detail="标题不得含标点"))
        evidence = boundary.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            issues.append(_issue("EVIDENCE_MISSING", boundary_id=boundary_id, field="evidence", detail="缺少逐字证据"))
            continue
        for index, item in enumerate(evidence):
            claim = str(item.get("claim") or "").strip()
            quote = _normalise_text(str(item.get("quote") or "").strip())
            field = f"evidence[{index}]"
            if not claim or not quote:
                issues.append(_issue("EVIDENCE_EMPTY", boundary_id=boundary_id, field=field, detail="claim 或 quote 为空"))
                continue
            if quote not in source_text:
                issues.append(_issue("EVIDENCE_NOT_VERBATIM", boundary_id=boundary_id, field=field, detail="引文不是源稿逐字子串"))
            unsupported = sorted(_facts(claim) - _facts(quote))
            if unsupported:
                issues.append(_issue("CLAIM_FACT_UNSUPPORTED", boundary_id=boundary_id, field=field, detail="claim 数字事实未被本条引文覆盖：" + "、".join(unsupported)))
            if INTERNAL_CODE.search(claim):
                issues.append(_issue("CLAIM_INTERNAL_CODE", boundary_id=boundary_id, field=field, detail="证据说明含内部状态码或占位词"))
    return {
        "schema": "zhou-visible-payload-validation-v1",
        "record_id": str(source_identity.get("record_id") or payload.get("record_id") or ""),
        "boundary_count": len(boundaries),
        "issues": issues,
        "passed": not issues,
    }
