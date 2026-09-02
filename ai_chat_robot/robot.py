"""
电商 Agent 终端入口。

Agent 定义见 specialists/，运行循环见 orchestrator/。
"""

from __future__ import annotations

import asyncio

from agents import SQLiteSession

from config.paths import DATA_DIR
from config.settings import SESSION_ID
from orchestrator import (
    SESSION_DB,
    build_run_config,
    handle_user_turn,
    resolve_interruptions,
)
from sandbox.health import check_sandbox_health
from sandbox.runtime import (
    analytics_backend_available,
    ensure_workspace_synced,
    is_docker_available,
    sandbox_mode_label,
)
from sandbox.settings import SANDBOX_HEALTH_CHECK_ON_STARTUP
from services.approval_store import PendingApprovalRecord
from specialists import customer_service_router


async def chat_loop() -> None:
    session = SQLiteSession(SESSION_ID, db_path=SESSION_DB)
    run_config = build_run_config(session_id=session.session_id)

    print("电商客服 Agent 已启动（流式 + Session 半托管）")
    print(f"Session ID: {SESSION_ID}")
    print(f"数据文件: {DATA_DIR}")
    print("输入 quit / exit / q 退出\n")

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("再见！会话已保存在 sessions.db。")
            break

        print("客服: ", end="", flush=True)
        text, result = await handle_user_turn(
            customer_service_router,
            user_input,
            session,
            run_config,
            on_delta=lambda d: print(d, end="", flush=True),
        )
        if result and result.interruptions:
            result = await resolve_interruptions(result, session, run_config)
            text = result.final_output
        elif isinstance(result, PendingApprovalRecord) and result.live_result is not None:
            result = await resolve_interruptions(result.live_result, session, run_config)
            text = result.final_output
        if text:
            print()


async def main() -> None:
    ensure_workspace_synced()
    if is_docker_available() and SANDBOX_HEALTH_CHECK_ON_STARTUP:
        health = check_sandbox_health(pull_if_missing=True)
        if not health.ok:
            print("沙箱健康检查未通过:")
            for issue in health.issues:
                print(f"  - {issue}")
    print(f"电商客服 Agent 已启动 | 数据分析: {sandbox_mode_label()}")
    if not analytics_backend_available():
        print("提示: 数据分析需要 Docker。请启动 Docker Desktop 后重试。")
    await chat_loop()


if __name__ == "__main__":
    asyncio.run(main())
