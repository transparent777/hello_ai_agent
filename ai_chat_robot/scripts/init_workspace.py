"""初始化用户工作区与示例文件。"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from config.paths import DATA_DIR, WORKSPACE_USER_DIR
from tools.file import ensure_workspace


def main() -> None:
    ensure_workspace()
    demo_dir = WORKSPACE_USER_DIR / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    hello = demo_dir / "hello.txt"
    if not hello.exists():
        hello.write_text(
            "这是 workspace_user/demo 下的示例文本。\n"
            "你可以让助手阅读、总结，或写入 notes/ 目录。\n",
            encoding="utf-8",
        )
    print(f"工作区已就绪: {WORKSPACE_USER_DIR}")
    if not (DATA_DIR / "orders.json").exists():
        print(
            "提示: 运行 python scripts/generate_catalog.py 可生成沙箱示例数据集（data/）"
        )


if __name__ == "__main__":
    main()
