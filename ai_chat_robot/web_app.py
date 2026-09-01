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
)
from sandbox.runtime import ensure_workspace_synced, is_docker_available, sandbox_mode_label
from ui_session_store import (
    append_message,
    clear_session_messages,
    init_ui_store,
    list_sessions,
    load_messages,
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
    st.session_state.run_config = build_run_config(
        run_model=model,
        with_sandbox=is_docker_available(),
    )


def _load_session_into_ui(session_id: str) -> None:
    st.session_state.agent_session = SQLiteSession(session_id, db_path=SESSION_DB)
    st.session_state.ui_messages = load_messages(UI_DB, session_id)
    st.session_state.pending_approval = None
    st.session_state.processing_prompt = None


def _init_state() -> None:
    ensure_workspace_synced()
    if "run_model" not in st.session_state:
        st.session_state.run_model = os.getenv("RUN_DEFAULT_MODEL") or DEEPSEEK_FLASH

    if "agent_session" not in st.session_state:
        default_id = f"{SESSION_ID}_web"
        _load_session_into_ui(default_id)
    if "run_config" not in st.session_state:
        _sync_run_config()
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

        st.divider()

        # --- 历史会话 ---
        st.subheader("历史会话")
        sessions = list_sessions(UI_DB)
        current_id = st.session_state.agent_session.session_id

        if sessions:
            options = [s["session_id"] for s in sessions]
            labels = {
                s["session_id"]: (
                    f"{s.get('title') or s['session_id']} "
                    f"（{s['message_count']} 条 · {s['updated_at'][:16]}）"
                )
                for s in sessions
            }
            picked = st.selectbox(
                "切换会话",
                options=options,
                index=options.index(current_id) if current_id in options else 0,
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
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            st.rerun()

        if st.button("新建会话", use_container_width=True):
            new_id = f"web_{uuid.uuid4().hex[:8]}"
            _load_session_into_ui(new_id)
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

        if result.interruptions:
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

        if result and result.interruptions:
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
    _render_sidebar()
    _render_chat()


if __name__ == "__main__":
    main()
