"""產生 PWA 圖示（可重跑）。

輸出至 frontend/desktop/public/icons/：
  - icon-192.png / icon-512.png      一般圖示（圓角，留透明邊）
  - icon-512-maskable.png            可遮罩圖示（內容置於安全區，背景滿版）
  - apple-touch-icon.png (180)       iOS 加入主畫面用（滿版方形，iOS 自行裁圓角）

用法：python tools/gen_pwa_icons.py
依賴：Pillow（已列於 requirements.txt）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Windows 終端機預設可能是 cp950，輸出中文/符號會崩潰；強制 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "desktop" / "public" / "icons"

# 品牌色（與 app-header / theme-color 一致）
NAVY = (16, 42, 67)        # #102a43
ACCENT = (38, 128, 194)    # #2680c2
WHITE = (255, 255, 255)

# 字型：優先用 Windows 內建粗體，找不到則退回 Pillow 預設點陣字。
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/msjhbd.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_mark(img: Image.Image, *, full_bleed: bool, safe_ratio: float = 1.0) -> None:
    """在 img 上畫圖示：圓角(或滿版)底色 + 中央字母 A + 底部強調點。"""
    size = img.width
    draw = ImageDraw.Draw(img)

    # 內容區（maskable 需縮進到安全區）
    pad = int(size * (1 - safe_ratio) / 2)
    box = (pad, pad, size - pad, size - pad)
    radius = 0 if full_bleed else int(size * 0.22)
    draw.rounded_rectangle(box, radius=radius, fill=NAVY)

    inner = box[2] - box[0]
    # 中央字母
    font = _font(int(inner * 0.62))
    text = "A"
    tb = draw.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    cx = box[0] + inner / 2
    cy = box[1] + inner * 0.46
    draw.text((cx - tw / 2 - tb[0], cy - th / 2 - tb[1]), text, font=font, fill=WHITE)

    # 底部強調點
    r = max(2, int(inner * 0.05))
    dy = box[1] + inner * 0.80
    draw.ellipse((cx - r, dy - r, cx + r, dy + r), fill=ACCENT)


def make(name: str, size: int, *, full_bleed: bool, safe_ratio: float = 1.0) -> None:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _draw_mark(img, full_bleed=full_bleed, safe_ratio=safe_ratio)
    out = OUT / name
    img.save(out)
    print(f"  ✓ {out.relative_to(ROOT)}  ({size}x{size})")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"產生 PWA 圖示 → {OUT.relative_to(ROOT)}")
    make("icon-192.png", 192, full_bleed=False)
    make("icon-512.png", 512, full_bleed=False)
    # 可遮罩：滿版底色，內容縮進安全區（~80%）
    make("icon-512-maskable.png", 512, full_bleed=True, safe_ratio=0.8)
    # iOS：滿版方形，系統自行裁圓角
    make("apple-touch-icon.png", 180, full_bleed=True)
    print("完成。")


if __name__ == "__main__":
    main()
