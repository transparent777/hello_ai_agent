"""将项目 data/ 同步到 sandbox/workspace/data，供本机测试与 Manifest 打包。"""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = Path(__file__).resolve().parent
SRC = PROJECT_ROOT / "data"
DEST = SANDBOX_DIR / "workspace" / "data"
WORKSPACE_DIR = SANDBOX_DIR / "workspace"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(
            f"未找到 {SRC}，请先运行: python scripts/generate_catalog.py"
        )

    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST)

    scripts_dest = WORKSPACE_DIR / "scripts"
    scripts_src = SANDBOX_DIR / "scripts"
    if scripts_dest.exists():
        shutil.rmtree(scripts_dest)
    shutil.copytree(
        scripts_src,
        scripts_dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    out_dir = WORKSPACE_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"已同步 data/ -> {DEST}")
    print(f"已同步 scripts/ -> {scripts_dest}")


if __name__ == "__main__":
    main()
