"""
电商 Agent Web 界面 — Streamlit 聊天页

启动：
    cd ai_chat_robot
    streamlit run web_app.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import streamlit as st

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from agents import SQLiteSession
from agents.exceptions import MaxTurnsExceeded

from approval_store import PendingApprovalRecord, has_pending_approval
from robot import (
    DEEPSEEK_FLASH,
    DEEPSEEK_PRO,
    SESSION_DB,
    SESSION_ID,
    _script_dir,
    apply_approval_decision,
    build_run_config,
    customer_service_router,
    describe_interruptions,
    handle_user_turn,
    restore_pending_approval,
)
from sandbox.health import check_sandbox_health
from sandbox.memory_sync import has_memory_summary
from sandbox.metrics import get_metrics_summary
from sandbox.runtime import (
    analytics_backend_available,
    ensure_workspace_synced,
    is_docker_available,
    sandbox_mode_label,
)
from sandbox.settings import SANDBOX_HEALTH_CHECK_ON_STARTUP, SANDBOX_PERSIST_SESSION, WEB_APP_API_KEY
from sandbox.session_store import clear_persisted_session
from ui_session_store import (
    append_message,
    clear_session_messages,
    init_ui_store,
    list_sessions,
    load_messages,
    touch_session,
)

UI_DB = SESSION_DB
MODEL_LABELS = {
    DEEPSEEK_FLASH: "Flash（快 / 省 token，前台默认）",
    DEEPSEEK_PRO: "Pro（强推理，前台默认）",
}

st.set_page_config(
    page_title="电商智能客服",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; max-width: 960px; }
    </style>
    """,
    unsafe_allow_html=True,
)

init_ui_store(UI_DB)


def _run_async(coro):
    return asyncio.run(coro)


def _sync_run_config() -> None:
    model = st.session_state.get("run_model", DEEPSEEK_FLASH)
    session_id = st.session_state.agent_session.session_id
    try:
        st.session_state.run_config = build_run_config(
            run_model=model,
            with_sandbox=is_docker_available(),
            session_id=session_id,
        )
        st.session_state.run_config_error = None
    except RuntimeError as exc:
        st.session_state.run_config = build_run_config(
            run_model=model,
            with_sandbox=False,
            session_id=session_id,
        )
        st.session_state.run_config_error = str(exc)


def _ensure_authenticated() -> bool:
    if not WEB_APP_API_KEY:
        return True
    if st.session_state.get("web_authenticated"):
        return True

    st.title("🔐 访问验证")
    st.caption("此实例已启用 WEB_APP_API_KEY 保护。")
    entered = st.text_input("访问密钥", type="password", key="web_api_key_input")
    if st.button("进入", type="primary"):
        if entered == WEB_APP_API_KEY:
            st.session_state.web_authenticated = True
            st.rerun()
        else:
            st.error("密钥不正确")
    return False


def _load_session_into_ui(session_id: str) -> None:
    st.session_state.agent_session = SQLiteSession(session_id, db_path=SESSION_DB)
    st.session_state.ui_messages = load_messages(UI_DB, session_id)
    st.session_state.processing_prompt = None
    st.session_state.pending_approval = restore_pending_approval(session_id)
    # 避免 selectbox 仍记住旧 session_id，把新建/切换的会话又切回去
    st.session_state.pop("session_picker", None)
    _sync_run_config()


def _create_new_session() -> None:
    new_id = f"web_{uuid.uuid4().hex[:8]}"
    touch_session(UI_DB, new_id, title="新对话")
    _load_session_into_ui(new_id)


def _init_state() -> None:
    ensure_workspace_synced()
    if "web_authenticated" not in st.session_state:
        st.session_state.web_authenticated = False
    if "sandbox_health" not in st.session_state:
        st.session_state.sandbox_health = None
    if SANDBOX_HEALTH_CHECK_ON_STARTUP and is_docker_available():
        st.session_state.sandbox_health = check_sandbox_health().to_dict()
    if "run_model" not in st.session_state:
        st.session_state.run_model = os.getenv("RUN_DEFAULT_MODEL") or DEEPSEEK_FLASH

    if "agent_session" not in st.session_state:
        default_id = f"{SESSION_ID}_web"
        _load_session_into_ui(default_id)
    if "run_config" not in st.session_state:
        _sync_run_config()
    if "run_config_error" not in st.session_state:
        st.session_state.run_config_error = None
    if "pending_approval" not in st.session_state:
        st.session_state.pending_approval = None
    if "processing_prompt" not in st.session_state:
        st.session_state.processing_prompt = None


def _append_and_persist(role: str, content: str) -> None:
    st.session_state.ui_messages.append({"role": role, "content": content})
    append_message(
        UI_DB,
        st.session_state.agent_session.session_id,
        role,
        content,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("控制台")

        # --- 模型切换（Run 级默认）---
        st.subheader("模型")
        selected = st.radio(
            "前台 / Run 默认模型",
            options=[DEEPSEEK_FLASH, DEEPSEEK_PRO],
            index=0 if st.session_state.run_model == DEEPSEEK_FLASH else 1,
            format_func=lambda m: MODEL_LABELS[m],
            key="run_model",
            help=(
                "影响 customer_service_router（前台分诊）。"
                "商品专员固定 Flash，订单专员固定 Pro。"
            ),
        )
        if selected != st.session_state.run_config.model:
            _sync_run_config()

        st.caption("专员模型（Agent 级，不可在此页切换）")
        st.markdown("- 商品顾问 → Flash")
        st.markdown("- 订单客服 → Pro")
        st.markdown("- 数据分析 → Pro + " + sandbox_mode_label())
        if SANDBOX_PERSIST_SESSION:
            st.caption("同一会话内多次分析可恢复沙箱工作区与记忆")
        if not analytics_backend_available():
            st.warning("数据分析需要 Docker。请启动 Docker Desktop。")
        if SANDBOX_PERSIST_SESSION:
            sid = st.session_state.agent_session.session_id
            mem = "有" if has_memory_summary(sid) else "无"
            st.caption(f"沙箱持久化：开启 · 跨运行记忆：{mem}")
        from guardrails import GUARDRAILS_ENABLED

        st.caption(f"输入/输出护栏：{'开启' if GUARDRAILS_ENABLED else '关闭'}")
        if has_pending_approval(st.session_state.agent_session.session_id):
            st.info("本会话有未完成的审批（已持久化，刷新页面仍可继续）")
        health = st.session_state.get("sandbox_health")
        if health is not None:
            status = "✅ 就绪" if health.get("ok") else "⚠️ 异常"
            st.caption(f"沙箱健康检查：{status}")
            if health.get("issues"):
                for issue in health["issues"]:
                    st.caption(f"- {issue}")
        if st.session_state.get("run_config_error"):
            st.error(st.session_state.run_config_error)

        metrics = get_metrics_summary()
        if metrics["counters"] or metrics["timings"]:
            with st.expander("运行指标（本会话进程）", expanded=False):
                st.json(metrics)

        st.divider()

        # --- 历史会话 ---
        st.subheader("历史会话")
        sessions = list_sessions(UI_DB)
        current_id = st.session_state.agent_session.session_id

        if sessions:
            options = [s["session_id"] for s in sessions]
            if current_id not in options:
                options = [current_id, *options]
            labels = {
                s["session_id"]: (
                    f"{s.get('title') or s['session_id']} "
                    f"（{s['message_count']} 条 · {s['updated_at'][:16]}）"
                )
                for s in sessions
            }
            if current_id not in labels:
                labels[current_id] = f"新对话（{current_id}）"
            picked = st.selectbox(
                "切换会话",
                options=options,
                index=options.index(current_id),
                format_func=lambda sid: labels.get(sid, sid),
                key="session_picker",
            )
            if picked != current_id:
                _load_session_into_ui(picked)
                st.rerun()
        else:
            st.caption("暂无历史，发送第一条消息后会自动保存。")

        st.caption("Agent Session ID")
        st.code(current_id, language=None)

        data_dir = _script_dir / "data"
        ok = (data_dir / "products.json").exists() and (
            data_dir / "orders.json"
        ).exists()
        st.write("演示数据", "✅" if ok else "❌")
        if not ok:
            st.info("运行：`python scripts/generate_catalog.py`")

        st.divider()
        st.markdown("**示例**")
        st.markdown(
            "- 有没有适合办公的键盘？\n"
            "- 查订单 10001 物流\n"
            "- 订单 10001 申请退款，商品有瑕疵\n"
            "- 分析一下订单数据\n"
            "- 生成销售报表"
        )

        if st.button("清空当前会话记录", use_container_width=True):
            clear_session_messages(UI_DB, current_id)
            clear_persisted_session(current_id)
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            _sync_run_config()
            st.rerun()

        if st.button("新建会话", use_container_width=True):
            _create_new_session()
            st.rerun()


def _handle_approval(approved: bool) -> None:
    pending = st.session_state.pending_approval
    if pending is None:
        return

    buffer = {"text": ""}

    def on_delta(delta: str) -> None:
        buffer["text"] += delta

    try:
        text, result = _run_async(
            apply_approval_decision(
                pending,
                st.session_state.agent_session,
                st.session_state.run_config,
                approved=approved,
                on_delta=on_delta,
            )
        )
        st.session_state.pending_approval = None

        if isinstance(result, PendingApprovalRecord):
            st.session_state.pending_approval = result
            content = buffer["text"] or "_仍有待审批操作…_"
        elif result and getattr(result, "interruptions", None):
            st.session_state.pending_approval = result
            content = buffer["text"] or "_仍有待审批操作…_"
        else:
            content = buffer["text"] or text or (
                "已拒绝该操作。" if not approved else ""
            )

        if content:
            _append_and_persist("assistant", content)
    except Exception as exc:
        _append_and_persist("assistant", f"**审批恢复失败**：{exc}")


def _process_pending_prompt() -> None:
    prompt = st.session_state.processing_prompt
    if not prompt:
        return

    with st.chat_message("assistant"):
        placeholder = st.empty()
        buffer = {"text": ""}

        def on_delta(delta: str) -> None:
            buffer["text"] += delta
            placeholder.markdown(buffer["text"])

        try:
            text, result = _run_async(
                handle_user_turn(
                    customer_service_router,
                    prompt,
                    st.session_state.agent_session,
                    st.session_state.run_config,
                    on_delta=on_delta,
                )
            )
        except MaxTurnsExceeded:
            _append_and_persist(
                "assistant", "**运行失败**：超过最大轮次，请简化问题。"
            )
            st.session_state.processing_prompt = None
            st.rerun()
            return
        except Exception as exc:
            _append_and_persist(
                "assistant", f"**运行失败**：{type(exc).__name__}: {exc}"
            )
            st.session_state.processing_prompt = None
            st.rerun()
            return

        if isinstance(result, PendingApprovalRecord):
            st.session_state.pending_approval = result
            note = buffer["text"] or "_已触发敏感操作，请在下方审批…_"
            _append_and_persist("assistant", note)
        elif result and getattr(result, "interruptions", None):
            st.session_state.pending_approval = result
            note = buffer["text"] or "_已触发敏感操作，请在下方审批…_"
            _append_and_persist("assistant", note)
        else:
            final = buffer["text"] or text or ""
            if final:
                _append_and_persist("assistant", final)

    st.session_state.processing_prompt = None
    st.rerun()


def _render_chat() -> None:
    st.title("🛒 电商智能客服")
    run_model = st.session_state.run_config.model
    st.caption(
        f"流式输出 · Session 记忆 · 退款审批 · 前台模型：`{run_model}` · "
        f"数据分析：{sandbox_mode_label()}"
    )

    # 先渲染全部历史（含用户 + 客服）
    for msg in st.session_state.ui_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.pending_approval:
        st.warning("⚠️ 有待审批的敏感操作（暂停的任务，不是新对话）")
        st.caption(
            "审批记录的是「批准执行工具」。决策后从同一 RunState 继续；"
            "状态已持久化，刷新页面仍可审批。"
        )
        for desc in describe_interruptions(st.session_state.pending_approval):
            st.write(f"- {desc}")
        c1, c2 = st.columns(2)
        if c1.button("✅ 批准", type="primary", key="approve"):
            _handle_approval(True)
            st.rerun()
        if c2.button("❌ 拒绝", key="reject"):
            _handle_approval(False)
            st.rerun()
        return

    # 第二阶段：处理上一轮提交的用户输入（保证用户消息已写入并 rerun 后再调模型）
    if st.session_state.processing_prompt:
        _process_pending_prompt()
        return

    if prompt := st.chat_input("查订单、搜商品、申请退款…"):
        _append_and_persist("user", prompt)
        st.session_state.processing_prompt = prompt
        st.rerun()


def main() -> None:
    _init_state()
    if not _ensure_authenticated():
        return
    _render_sidebar()
    _render_chat()


if __name__ == "__main__":
    main()
