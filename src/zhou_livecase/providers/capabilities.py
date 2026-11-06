from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


INLINE_ROUTE = "inline_single_window"
DELEGATED_ROUTE = "delegated_chatgpt"

COMMON_REQUIRED = (
    "filesystem_read_write",
    "python_execution",
    "live_source_pagination",
    "private_runner_call",
    "private_auditor_call",
    "target_system_readback",
)

ROUTE_REQUIRED = {
    INLINE_ROUTE: COMMON_REQUIRED + ("structured_analysis",),
    DELEGATED_ROUTE: COMMON_REQUIRED
    + (
        "visible_browser_automation",
        "chatgpt_file_upload",
        "chatgpt_result_download",
        "chatgpt_conversation_cleanup",
    ),
}

AUTHORIZATION_HINTS = {
    "live_source_pagination": "请授权只读访问来源多维表，并提供私有环境中的表标识；不要在聊天中粘贴密钥。",
    "private_runner_call": "请授权调用私有生产 runner；runner 持有最小写权限，机器人不得直接持有写密钥。",
    "private_auditor_call": "请授权调用独立只读 auditor；其身份必须与 runner 分离。",
    "target_system_readback": "请授权只读回读 COS、案例库、案例匹配和源表。",
    "visible_browser_automation": "请提供受支持的可见浏览器自动化能力；禁止调用未公开的内部接口。",
    "chatgpt_file_upload": "请授权普通 ChatGPT 页面上传本批输入文件。",
    "chatgpt_result_download": "请授权下载普通 ChatGPT 页面生成的结果文件。",
    "chatgpt_conversation_cleanup": "请授权通过可见界面逐条删除本轮已验收会话并刷新确认消失。",
}

SECRET_KEY = re.compile(r"(?:token|secret|password|cookie|webhook|credential|api[_-]?key)", re.I)


@dataclass(frozen=True)
class RouteAssessment:
    route: str
    executable: bool
    missing_capabilities: tuple[str, ...]
    authorization_requests: tuple[str, ...]


def _capabilities(profile: dict[str, Any]) -> dict[str, bool]:
    raw = profile.get("capabilities")
    if not isinstance(raw, dict):
        return {}
    if any(not isinstance(value, bool) for value in raw.values()):
        raise ValueError("capability_values_must_be_boolean")
    return {str(key): value for key, value in raw.items()}


def _contains_secret_material(value: Any, path: str = "") -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if SECRET_KEY.search(key_text):
                return True
            if _contains_secret_material(child, child_path):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_secret_material(item, f"{path}[]") for item in value)
    return False


def evaluate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Return a no-secret, provider-neutral production capability report."""

    if profile.get("schema") != "zhou-bot-capability-profile-v1":
        raise ValueError("capability_profile_schema")
    if _contains_secret_material(profile):
        raise ValueError("capability_profile_contains_secret_material")
    provider = str(profile.get("provider") or "").strip().lower()
    if provider not in {"grok", "muse", "generic"}:
        raise ValueError("capability_profile_provider")
    capabilities = _capabilities(profile)
    assessments: list[RouteAssessment] = []
    for route, required in ROUTE_REQUIRED.items():
        missing = tuple(name for name in required if capabilities.get(name) is not True)
        requests = tuple(AUTHORIZATION_HINTS[name] for name in missing if name in AUTHORIZATION_HINTS)
        assessments.append(RouteAssessment(route, not missing, missing, requests))
    return {
        "schema": "zhou-bot-capability-report-v1",
        "provider": provider,
        "profile_id": str(profile.get("profile_id") or ""),
        "routes": [
            {
                "route": item.route,
                "executable": item.executable,
                "missing_capabilities": list(item.missing_capabilities),
                "authorization_requests": list(item.authorization_requests),
            }
            for item in assessments
        ],
        "secrets_present": False,
    }


def select_route(profile: dict[str, Any], preferred: str = "auto") -> dict[str, Any]:
    report = evaluate_profile(profile)
    routes = {item["route"]: item for item in report["routes"]}
    if preferred not in {"auto", INLINE_ROUTE, DELEGATED_ROUTE}:
        raise ValueError("route_preference")
    if preferred != "auto":
        chosen = preferred if routes[preferred]["executable"] else None
    elif routes[INLINE_ROUTE]["executable"]:
        chosen = INLINE_ROUTE
    elif routes[DELEGATED_ROUTE]["executable"]:
        chosen = DELEGATED_ROUTE
    else:
        chosen = None
    report["selected_route"] = chosen
    report["ready"] = chosen is not None
    return report
