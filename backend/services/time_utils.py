"""時間字串工具 (S9)：24 時制輸入正規化。

例：「1830」→「18:30」、「830」→「08:30」、「18:30」→「18:30」、「9」→「09:00」。
"""
from __future__ import annotations


def normalize_time(value: str) -> str | None:
    """把使用者輸入正規化成 HH:MM（24 時制）；無法解析回傳 None。"""
    raw = value.strip()
    if not raw:
        return None

    if ":" in raw:
        parts = raw.split(":", 1)
        hh, mm = parts[0].strip(), parts[1].strip()
    else:
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return None
        if len(digits) <= 2:        # 「9」「18」→ 視為整點
            hh, mm = digits, "0"
        elif len(digits) == 3:      # 「830」→ 8:30
            hh, mm = digits[0], digits[1:]
        else:                        # 「1830」→ 18:30（取前四碼）
            hh, mm = digits[:2], digits[2:4]

    try:
        h, m = int(hh), int(mm)
    except ValueError:
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return f"{h:02d}:{m:02d}"
