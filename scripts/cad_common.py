"""cad-file-reader 公共工具：多个脚本共用的纯函数。

只放确定等价的纯函数/输出辅助；各专业差异逻辑仍留在对应脚本。
"""
from __future__ import annotations

import json
import math
import re
import resource
import sys
from pathlib import Path
from typing import Any


def compact(value: Any, limit: int = 240) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def load_rules(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"识图规则不存在：{path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def pattern_hit(value: str, pattern: Any) -> bool:
    """短 ASCII 代号按边界匹配，避免 AL 误命中 VALVE 等普通单词。"""
    token = str(pattern).upper()
    if re.fullmatch(r"[A-Z]{1,3}", token):
        if re.search(rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])", value):
            return True
        return bool(re.search(rf"(?<![A-Z0-9]){re.escape(token)}\d", value))
    return token in value


def match_rule(text: Any, rules: list[dict[str, Any]], key: str) -> tuple[str, dict[str, Any], str]:
    value = compact(text).upper()
    for rule in rules:
        for pattern in rule.get("patterns") or []:
            if pattern_hit(value, pattern):
                return str(rule.get(key) or ""), rule, str(pattern)
    return "", {}, ""


def segment_length(seg: list[Any] | tuple[Any, ...]) -> float:
    try:
        return math.hypot(float(seg[2]) - float(seg[0]), float(seg[3]) - float(seg[1]))
    except (TypeError, ValueError):
        return 0.0


def peak_rss_mb() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss / 1048576) if sys.platform == "darwin" else int(rss / 1024)


def file_name(data: dict[str, Any], value: Any) -> str:
    if isinstance(value, dict):
        return compact(value.get("name") or value.get("path"))
    files = data.get("files") or []
    if isinstance(value, int) and 0 <= value < len(files):
        item = files[value]
        return compact(item.get("name") or item.get("path")) if isinstance(item, dict) else compact(item)
    return compact(value)
