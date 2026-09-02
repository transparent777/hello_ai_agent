"""将项目 data/、repo/、scripts/ 同步到 sandbox/workspace/。"""

from __future__ import annotations

import shutil
from pathlib import Path

from config.paths import DATA_DIR

SANDBOX_DIR = Path(__file__).resolve().parent
SRC_DATA = DATA_DIR
DEST_DATA = SANDBOX_DIR / "workspace" / "data"
WORKSPACE_DIR = SANDBOX_DIR / "workspace"
SRC_REPO = SANDBOX_DIR / "repo"
DEST_REPO = WORKSPACE_DIR / "repo"


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def main() -> None:
    if not SRC_DATA.exists():
        raise SystemExit(
            f"未找到 {SRC_DATA}，请先运行: python scripts/generate_catalog.py"
        )
    if not SRC_REPO.exists():
        raise SystemExit(f"未找到 {SRC_REPO}，请确认 sandbox/repo/ 存在")

    _copy_tree(SRC_DATA, DEST_DATA)
    _copy_tree(SRC_REPO, DEST_REPO)

    scripts_dest = WORKSPACE_DIR / "scripts"
    scripts_src = SANDBOX_DIR / "scripts"
    _copy_tree(scripts_src, scripts_dest)

    out_dir = WORKSPACE_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"已同步 data/ -> {DEST_DATA}")
    print(f"已同步 repo/ -> {DEST_REPO}")
    print(f"已同步 scripts/ -> {scripts_dest}")


if __name__ == "__main__":
    main()
