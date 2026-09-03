"""
文件与数据处理 Agent 终端入口。

Agent 定义见 specialists/，运行循环见 orchestrator/。
"""

from __future__ import annotations

import asyncio

from agents import SQLiteSession

from application import build_services
from adapters.agent_runtime import build_run_config
from config.paths import DATA_DIR
from config.settings import SESSION_ID, SHOW_REACT_STEPS
from orchestrator import (
    SESSION_DB,
    resolve_interruptions,
)
from orchestrator.handoff_policy import sanitize_user_visible_output
from sandbox.health import check_sandbox_health
from adapters.sandbox_runtime import (
    analytics_backend_available,
    ensure_workspace_synced,
    is_docker_available,
    sandbox_mode_label,
)
from sandbox.settings import SANDBOX_HEALTH_CHECK_ON_STARTUP
from services.approval_store import PendingApprovalRecord
from services.react_trace import compact_summary
from specialists import workspace_router

application_services = build_services()
chat_service = application_services.chat


async def chat_loop() -> None:
    session = SQLiteSession(SESSION_ID, db_path=SESSION_DB)
    run_config = build_run_config(session_id=session.session_id)

    print("文件与数据助手已启动（流式 + Session 半托管）")
    print(f"Session ID: {SESSION_ID}")
    print(f"示例数据: {DATA_DIR}")
    print("输入 quit / exit / q 退出\n")

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("再见！会话已保存在 sessions.db。")
            break

        print("助手: ", end="", flush=True)
        streamed: list[str] = []

        def on_delta(delta: str) -> None:
            streamed.append(delta)
            print(delta, end="", flush=True)

        text, result, react_steps = await chat_service.execute(
            workspace_router,
            user_input,
            session,
            run_config,
            on_delta=on_delta,
        )

        clean_stream = sanitize_user_visible_output("".join(streamed))
        final_text = sanitize_user_visible_output(text or "")

        # 流式阶段若漏出英文/DSML，用清洗后的终稿覆盖展示
        if final_text and final_text.strip() != clean_stream.strip():
            if clean_stream.strip():
                print()
            print(final_text)

        if clean_stream or final_text:
            print()

        if SHOW_REACT_STEPS and react_steps:
            print(f"  └─ {compact_summary(react_steps)}")
        if result and result.interruptions:
            result = await resolve_interruptions(result, session, run_config)
        elif isinstance(result, PendingApprovalRecord) and result.live_result is not None:
            result = await resolve_interruptions(result.live_result, session, run_config)
        elif not final_text and (
            result is None
            or (
                not getattr(result, "interruptions", None)
                and not isinstance(result, PendingApprovalRecord)
            )
        ):
            print("（助手未返回内容，请查看上方 [运行时失败] 提示）")


async def main() -> None:
    ensure_workspace_synced()
    if is_docker_available() and SANDBOX_HEALTH_CHECK_ON_STARTUP:
        health = check_sandbox_health(pull_if_missing=True)
        if not health.ok:
            print("沙箱健康检查未通过:")
            for issue in health.issues:
                print(f"  - {issue}")
    print(f"文件与数据助手已启动 | 数据分析: {sandbox_mode_label()}")
    if not analytics_backend_available():
        print("提示: 数据分析需要 Docker。请启动 Docker Desktop 后重试。")
    await chat_loop()


if __name__ == "__main__":
    asyncio.run(main())
