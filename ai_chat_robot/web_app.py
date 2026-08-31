"""
电商 Agent Web 界面 — Streamlit 聊天页

启动：
    cd ai_chat_robot
    streamlit run web_app.py
"""

from __future__ import annotations

import asyncio
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
    SESSION_DB,
    SESSION_ID,
    _script_dir,
    apply_approval_decision,
    build_run_config,
    customer_service_router,
    describe_interruptions,
    handle_user_turn,
)

st.set_page_config(
    page_title="电商智能客服",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; max-width: 900px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _init_state() -> None:
    defaults = {
        "ui_messages": [],
        "pending_approval": None,
        "run_config": build_run_config(),
        "agent_session": SQLiteSession(f"{SESSION_ID}_web", db_path=SESSION_DB),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_async(coro):
    return asyncio.run(coro)


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("控制台")
        st.caption("Session（半托管 · SQLite 持久化）")
        st.code(st.session_state.agent_session.session_id, language=None)

        data_dir = _script_dir / "data"
        ok = (data_dir / "products.json").exists() and (
            data_dir / "orders.json"
        ).exists()
        st.write("演示数据", "✅ 已就绪" if ok else "❌ 未生成")
        if not ok:
            st.info("终端执行：`python scripts/generate_catalog.py`")

        st.divider()
        st.markdown("**示例问题**")
        st.markdown(
            "- 有没有适合办公的键盘？\n"
            "- 帮我查订单 10001 物流\n"
            "- 帮订单 10001 申请退款，商品有瑕疵"
        )

        if st.button("清空页面聊天记录", use_container_width=True):
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            st.rerun()

        if st.button("新建 Agent 会话", use_container_width=True):
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            st.session_state.agent_session = SQLiteSession(
                f"web_{uuid.uuid4().hex[:8]}",
                db_path=SESSION_DB,
            )
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
            content = buffer["text"] or text or ("已拒绝该操作。" if not approved else "")

        if content:
            st.session_state.ui_messages.append(
                {"role": "assistant", "content": content}
            )
    except Exception as exc:
        st.session_state.ui_messages.append(
            {"role": "assistant", "content": f"**审批恢复失败**：{exc}"}
        )


def _run_user_turn(prompt: str, on_delta) -> tuple[str | None, object | None]:
    try:
        return _run_async(
            handle_user_turn(
                customer_service_router,
                prompt,
                st.session_state.agent_session,
                st.session_state.run_config,
                on_delta=on_delta,
            )
        )
    except MaxTurnsExceeded as exc:
        raise exc
    except Exception:
        raise


def _render_chat() -> None:
    st.title("🛒 电商智能客服")
    st.caption("多 Agent · 流式输出 · Session 记忆 · 退款需审批")

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

    if prompt := st.chat_input("查订单、搜商品、申请退款…"):
        st.session_state.ui_messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            buffer = {"text": ""}

            def on_delta(delta: str) -> None:
                buffer["text"] += delta
                placeholder.markdown(buffer["text"])

            try:
                text, result = _run_user_turn(prompt, on_delta)
            except MaxTurnsExceeded:
                err = "**运行失败**：超过最大轮次，请简化问题。"
                placeholder.markdown(err)
                st.session_state.ui_messages.append(
                    {"role": "assistant", "content": err}
                )
                return
            except Exception as exc:
                err = f"**运行失败**：{type(exc).__name__}: {exc}"
                placeholder.markdown(err)
                st.session_state.ui_messages.append(
                    {"role": "assistant", "content": err}
                )
                return

            if result and result.interruptions:
                st.session_state.pending_approval = result
                note = buffer["text"] or "_已触发敏感操作，请在下方审批…_"
                placeholder.markdown(note)
                st.session_state.ui_messages.append(
                    {"role": "assistant", "content": note}
                )
            else:
                final = buffer["text"] or text or ""
                if final:
                    st.session_state.ui_messages.append(
                        {"role": "assistant", "content": final}
                    )


def main() -> None:
    _init_state()
    _render_sidebar()
    _render_chat()


if __name__ == "__main__":
    main()
