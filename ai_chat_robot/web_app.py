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
from mcp_integration.runtime import mcp_status_summary
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
from tracing_setup import get_recent_trace_count, tracing_status_summary
from ui_session_store import (
    append_message,
    clear_session_messages,
    init_ui_store,
    list_sessions,
    load_messages,
    touch_session,
)

UI_DB = SESSION_DB
MODEL_SHORT = {
    DEEPSEEK_FLASH: "Flash · 快速",
    DEEPSEEK_PRO: "Pro · 深度",
}

QUICK_PROMPTS = [
    "有没有适合办公的键盘？",
    "查订单 10001 物流",
    "订单 10001 申请退款，商品有瑕疵",
    "分析一下订单数据",
    "生成销售报表",
]

st.set_page_config(
    page_title="电商智能客服",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --bg: #f4f6fb;
        --card: #ffffff;
        --text: #1a1d26;
        --muted: #6b7280;
        --accent: #4f46e5;
        --accent-soft: #eef2ff;
        --border: #e5e7eb;
        --user-bubble: #4f46e5;
        --bot-bubble: #f3f4f6;
    }
    .stApp { background: var(--bg); }
  header[data-testid="stHeader"] { background: transparent; }
    section[data-testid="stSidebar"] {
        background: var(--card);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
    .main .block-container {
        max-width: 820px;
        padding-top: 1.5rem;
        padding-bottom: 6rem;
    }
    .app-hero {
        margin-bottom: 1rem;
    }
    .app-hero h1 {
        font-size: 1.65rem;
        font-weight: 700;
        color: var(--text);
        margin: 0 0 0.25rem 0;
        letter-spacing: -0.02em;
    }
    .app-hero p {
        color: var(--muted);
        font-size: 0.92rem;
        margin: 0;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        background: var(--accent-soft);
        color: var(--accent);
        margin-top: 0.5rem;
    }
    .status-pill.ok { background: #ecfdf5; color: #059669; }
    .status-pill.warn { background: #fffbeb; color: #d97706; }
    .empty-wrap {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem;
        color: var(--muted);
    }
    .empty-wrap h3 {
        color: var(--text);
        font-weight: 600;
        margin-bottom: 0.35rem;
    }
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 0.35rem 0 !important;
    }
    div[data-testid="stChatMessageContent"] {
        border-radius: 14px !important;
        padding: 0.85rem 1rem !important;
        line-height: 1.55 !important;
    }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
        div[data-testid="stChatMessageContent"] {
        background: var(--user-bubble) !important;
        color: #fff !important;
    }
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
        div[data-testid="stChatMessageContent"] {
        background: var(--bot-bubble) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }
    .approval-card {
        background: var(--card);
        border: 1px solid #fcd34d;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        margin: 0.75rem 0 1rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
    }
    .approval-card h4 { margin: 0 0 0.35rem; color: #92400e; }
    .approval-card p { margin: 0 0 0.75rem; color: var(--muted); font-size: 0.88rem; }
    div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"] {
        border-radius: 10px;
        font-weight: 600;
    }
    div[data-testid="stChatInput"] textarea {
        border-radius: 14px !important;
        border: 1px solid var(--border) !important;
    }
    #MainMenu, footer { visibility: hidden; }
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


def _session_label(s: dict) -> str:
    title = (s.get("title") or "新对话").strip()
    if len(title) > 22:
        title = title[:22] + "…"
    return f"{title} · {s['message_count']}条"


def _system_status() -> tuple[str, str]:
    """返回 (级别, 一句话状态)。"""
    if st.session_state.get("run_config_error"):
        return "warn", "沙箱未就绪"
    if not analytics_backend_available():
        return "warn", "数据分析需 Docker"
    if has_pending_approval(st.session_state.agent_session.session_id):
        return "warn", "待审批"
    return "ok", "服务正常"


def _ensure_authenticated() -> bool:
    if not WEB_APP_API_KEY:
        return True
    if st.session_state.get("web_authenticated"):
        return True

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔐 访问验证")
        st.caption("请输入访问密钥以继续")
        entered = st.text_input("密钥", type="password", key="web_api_key_input", label_visibility="collapsed", placeholder="访问密钥")
        if st.button("进入", type="primary", use_container_width=True):
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
    st.session_state.pop("session_picker", None)
    _sync_run_config()


def _create_new_session() -> None:
    new_id = f"web_{uuid.uuid4().hex[:8]}"
    touch_session(UI_DB, new_id, title="新对话")
    _load_session_into_ui(new_id)


def _init_state() -> None:
    ensure_workspace_synced()
    from tracing_setup import configure_tracing

    configure_tracing()
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


def _submit_user_prompt(prompt: str) -> None:
    _append_and_persist("user", prompt)
    st.session_state.processing_prompt = prompt
    st.rerun()


def _render_advanced_settings(current_id: str) -> None:
    from guardrails import GUARDRAILS_ENABLED

    with st.expander("高级设置", expanded=False):
        st.caption(f"会话 ID：`{current_id}`")
        st.caption(f"数据分析 · {sandbox_mode_label()}")
        if SANDBOX_PERSIST_SESSION:
            mem = "有" if has_memory_summary(current_id) else "无"
            st.caption(f"沙箱记忆 · {mem}")
        st.caption(f"护栏 · {'开' if GUARDRAILS_ENABLED else '关'}")
        st.caption(f"MCP · {mcp_status_summary()}")
        st.caption(f"Tracing · {tracing_status_summary()}")
        trace_n = get_recent_trace_count()
        if trace_n:
            st.caption(f"Trace 记录 · 约 {trace_n} 条")

        health = st.session_state.get("sandbox_health")
        if health is not None and not health.get("ok"):
            for issue in health.get("issues", []):
                st.caption(f"⚠ {issue}")

        if st.session_state.get("run_config_error"):
            st.error(st.session_state.run_config_error)

        metrics = get_metrics_summary()
        if metrics["counters"] or metrics["timings"]:
            st.json(metrics, expanded=False)

        data_dir = _script_dir / "data"
        ok = (data_dir / "products.json").exists() and (data_dir / "orders.json").exists()
        if not ok:
            st.info("演示数据未生成：`python scripts/generate_catalog.py`")


def _render_sidebar() -> None:
    current_id = st.session_state.agent_session.session_id
    level, status_text = _system_status()

    with st.sidebar:
        if st.button("＋ 新对话", type="primary", use_container_width=True):
            _create_new_session()
            st.rerun()

        st.markdown(
            f'<span class="status-pill {level}">● {status_text}</span>',
            unsafe_allow_html=True,
        )

        st.divider()

        sessions = list_sessions(UI_DB)
        if sessions:
            options = [s["session_id"] for s in sessions]
            if current_id not in options:
                options = [current_id, *options]
            labels = {s["session_id"]: _session_label(s) for s in sessions}
            if current_id not in labels:
                labels[current_id] = "新对话 · 0条"
            picked = st.selectbox(
                "历史对话",
                options=options,
                index=options.index(current_id),
                format_func=lambda sid: labels.get(sid, sid),
                key="session_picker",
                label_visibility="collapsed",
            )
            if picked != current_id:
                _load_session_into_ui(picked)
                st.rerun()
        else:
            st.caption("发送消息后自动保存")

        st.divider()

        selected = st.selectbox(
            "前台模型",
            options=[DEEPSEEK_FLASH, DEEPSEEK_PRO],
            index=0 if st.session_state.run_model == DEEPSEEK_FLASH else 1,
            format_func=lambda m: MODEL_SHORT[m],
            key="run_model",
            label_visibility="visible",
        )
        if selected != st.session_state.run_config.model:
            _sync_run_config()

        _render_advanced_settings(current_id)

        st.divider()
        if st.button("清空当前对话", use_container_width=True):
            clear_session_messages(UI_DB, current_id)
            clear_persisted_session(current_id)
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            _sync_run_config()
            st.rerun()


def _render_quick_prompts() -> None:
    st.markdown(
        """
        <div class="empty-wrap">
            <h3>有什么可以帮您？</h3>
            <p>查商品、跟物流、办退款，或让数据分析专员跑报表</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, text in enumerate(QUICK_PROMPTS):
        with cols[i % 2]:
            if st.button(text, key=f"quick_{i}", use_container_width=True):
                _submit_user_prompt(text)


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
            content = buffer["text"] or "仍有待审批操作，请继续确认。"
        elif result and getattr(result, "interruptions", None):
            st.session_state.pending_approval = result
            content = buffer["text"] or "仍有待审批操作，请继续确认。"
        else:
            content = buffer["text"] or text or (
                "已拒绝该操作。" if not approved else ""
            )

        if content:
            _append_and_persist("assistant", content)
    except Exception as exc:
        _append_and_persist("assistant", f"**审批失败**：{exc}")


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
            _append_and_persist("assistant", "运行超时：问题较复杂，请拆分后重试。")
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
            note = buffer["text"] or "已触发敏感操作，请在下方确认。"
            _append_and_persist("assistant", note)
        elif result and getattr(result, "interruptions", None):
            st.session_state.pending_approval = result
            note = buffer["text"] or "已触发敏感操作，请在下方确认。"
            _append_and_persist("assistant", note)
        else:
            final = buffer["text"] or text or ""
            if final:
                _append_and_persist("assistant", final)

    st.session_state.processing_prompt = None
    st.rerun()


def _render_approval_card() -> None:
    items = describe_interruptions(st.session_state.pending_approval)
    items_html = "".join(f"<li>{item}</li>" for item in items)
    st.markdown(
        f"""
        <div class="approval-card">
            <h4>需要您的确认</h4>
            <p>以下操作涉及敏感变更，批准后将从中断处继续执行（非新对话）。</p>
            <ul style="margin:0;padding-left:1.1rem;color:#374151;font-size:0.9rem;">{items_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("批准", type="primary", use_container_width=True, key="approve"):
        _handle_approval(True)
        st.rerun()
    if c2.button("拒绝", use_container_width=True, key="reject"):
        _handle_approval(False)
        st.rerun()


def _render_chat() -> None:
    st.markdown(
        """
        <div class="app-hero">
            <h1>电商智能客服</h1>
            <p>商品咨询 · 订单物流 · 退款售后 · 数据分析</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.ui_messages and not st.session_state.processing_prompt:
        _render_quick_prompts()

    for msg in st.session_state.ui_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.pending_approval:
        _render_approval_card()
        return

    if st.session_state.processing_prompt:
        _process_pending_prompt()
        return

    if prompt := st.chat_input("输入消息，Enter 发送"):
        _submit_user_prompt(prompt)


def main() -> None:
    _init_state()
    if not _ensure_authenticated():
        return
    _render_sidebar()
    _render_chat()


if __name__ == "__main__":
    main()
