"""打包腳本：產生單一免安裝 exe，輸出到「打包輸出/」(X1)，並清除過程檔 (X2)。

流程：
  1. （可選）建置 Vue 前端：frontend/desktop → npm run build。
  2. PyInstaller --onefile，入口 run.py，內含 app.toml 與前端 dist。
  3. 將 exe 搬到「打包輸出/」，檔名取自 app.toml（如 AhhOuch_v1.0.0.exe）。
  4. 刪除 build/、*.spec、dist/ 等過程檔。

用法：
  python build.py            # 完整打包（含前端建置）
  python build.py --no-front # 略過前端建置（沿用既有 dist）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 終端機預設可能是 cp950，會在輸出中文/emoji 時崩潰；強制 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend import version  # noqa: E402

OUTPUT_DIR = ROOT / "打包輸出"
FRONTEND_DESKTOP = ROOT / "frontend" / "desktop"
FRONTEND_DIST = FRONTEND_DESKTOP / "dist"
APP_TOML = ROOT / "app.toml"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def build_frontend() -> None:
    if not FRONTEND_DESKTOP.exists():
        print("略過前端建置：frontend/desktop 不存在。")
        return
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        print("[警告] 找不到 npm，略過前端建置（將沿用既有 dist）。")
        return
    if not (FRONTEND_DESKTOP / "node_modules").exists():
        _run([npm, "install"], cwd=FRONTEND_DESKTOP)
    _run([npm, "run", "build"], cwd=FRONTEND_DESKTOP)


def _add_data(src: Path, dest: str) -> list[str]:
    # PyInstaller --add-data 在不同平台用不同分隔符 (Windows ';')
    return ["--add-data", f"{src}{os.pathsep}{dest}"]


def build_exe() -> Path:
    name = version.build_filename()
    work = ROOT / "build"
    dist = ROOT / "dist"
    spec = ROOT / f"{name}.spec"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--name", name,
        "--distpath", str(dist),
        "--workpath", str(work),
        "--specpath", str(ROOT),
        # uvicorn 動態載入 loop/protocol 子模組，需一併收集
        "--collect-submodules", "uvicorn",
        *_add_data(APP_TOML, "."),
    ]
    if FRONTEND_DIST.exists():
        cmd += _add_data(FRONTEND_DIST, "frontend/desktop/dist")
    else:
        print("[警告] 前端 dist 不存在，打包後僅有後端提示頁。")
    cmd.append(str(ROOT / "run.py"))

    _run(cmd)

    exe = dist / f"{name}.exe"
    if not exe.exists():
        raise FileNotFoundError(f"打包失敗，找不到 {exe}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / exe.name
    if target.exists():
        target.unlink()
    shutil.move(str(exe), str(target))

    # 清除過程檔 (X2)
    for p in (work, dist, spec):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()

    return target


def main() -> None:
    skip_front = "--no-front" in sys.argv
    print(f"=== 打包 {version.full_title()} ===")
    if not skip_front:
        build_frontend()
    target = build_exe()
    print(f"\n✅ 完成：{target}")
    print(f"   位置：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
