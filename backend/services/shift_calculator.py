"""班表自動換算 (S10)。

規則：每班 1.5 小時，列出涵蓋「上班開始後 12 小時」的班次。
已確認決策：含第 12 小時整點那班 → 共 9 班（0、1.5、…、12 小時）。
跨午夜自動回繞（如 22:30 之後為 00:00）。
"""
from __future__ import annotations

from .time_utils import normalize_time

SHIFT_MINUTES = 90       # 每班 1.5 小時
SHIFT_COUNT = 9          # 含端點共 9 班（決策：列入第 12 小時整點）


def shift_slots(start: str) -> list[str]:
    """回傳自上班時間起、每 1.5h 一班、共 9 班的 HH:MM 清單。"""
    normalized = normalize_time(start)
    if normalized is None:
        return []
    h, m = (int(x) for x in normalized.split(":"))
    base = h * 60 + m
    out = []
    for i in range(SHIFT_COUNT):
        total = (base + i * SHIFT_MINUTES) % 1440  # 跨午夜回繞
        out.append(f"{total // 60:02d}:{total % 60:02d}")
    return out
