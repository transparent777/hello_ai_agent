"""
文件与数据处理 Agent — Streamlit 聊天界面

启动：
    cd ai_chat_robot
    streamlit run web_app.py
"""

from __future__ import annotations

import asyncio
import html
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from agents import SQLiteSession
from agents.exceptions import MaxTurnsExceeded

from config.paths import DATA_DIR, PACKAGE_ROOT
from config.file_agent import FILE_AGENT_ENABLED, FILE_AGENT_WORKSPACE
from config.settings import SHOW_REACT_STEPS
from guardrails import GUARDRAILS_ENABLED
from mcp_integration.runtime import mcp_status_summary
from orchestrator.handoff_policy import sanitize_user_visible_output
from orchestrator import (
    DEEPSEEK_FLASH,
    DEEPSEEK_PRO,
    SESSION_DB,
    apply_approval_decision,
    build_run_config,
    describe_interruptions,
    handle_user_turn,
    restore_pending_approval,
)
from services.approval_store import PendingApprovalRecord, has_pending_approval
from services.tracing import configure_tracing, get_recent_trace_count, tracing_status_summary
from services.ui_session_store import (
    append_message,
    clear_all_ui_sessions,
    clear_session_messages,
    count_messages,
    init_ui_store,
    list_sessions,
    load_messages,
    prune_empty_sessions,
)
from specialists import workspace_router
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

UI_DB = SESSION_DB
MODEL_SHORT = {
    DEEPSEEK_FLASH: "Flash · 快速",
    DEEPSEEK_PRO: "Pro · 深度",
}

QUICK_PROMPTS = [
    "写一段关于秋天的短文（对话里直接回复）",
    "列出工作区里有哪些文件",
    "把 data/orders.json 导出为 csv 到 exports/",
    "分析一下 data/orders.json 订单数据",
    "生成一份销售分析报表",
]

st.set_page_config(
    page_title="文件与数据助手",
    page_icon="📁",
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
        --font-sans: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei",
            "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", sans-serif;
        --font-mono: "Cascadia Mono", "Cascadia Code", "Microsoft YaHei",
            "Consolas", monospace;
    }
    html, body, .stApp, [data-testid="stMarkdownContainer"],
    div[data-testid="stChatMessageContent"], .stTextInput input, textarea {
        font-family: var(--font-sans) !important;
        -webkit-font-smoothing: antialiased;
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
        letter-spacing: 0;
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
    .react-step-line {
        font-size: 0.78rem;
        color: var(--muted);
        font-family: var(--font-mono);
        margin: 0.1rem 0;
    }
    .react-summary {
        font-size: 0.8rem;
        color: var(--muted);
        margin-top: 0.35rem;
    }
        background: transparent !important;
        border: none !important;
        padding: 0.35rem 0 !important;
    }
    div[data-testid="stChatMessageContent"] {
        border-radius: 14px !important;
        padding: 0.85rem 1rem !important;
        line-height: 1.7 !important;
        font-size: 0.95rem !important;
    }
    /* JSON/代码块：等宽 + 中文字体回退，避免 Windows 下中文挤成一团 */
    div[data-testid="stChatMessageContent"] pre,
    div[data-testid="stChatMessageContent"] code,
    .stMarkdown pre, .stMarkdown code {
        font-family: var(--font-mono) !important;
        font-size: 0.86rem !important;
        line-height: 1.65 !important;
        letter-spacing: 0 !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
    div[data-testid="stChatMessageContent"] pre {
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        background: #f8fafc !important;
        border: 1px solid var(--border) !important;
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


def _format_session_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    now = datetime.now()
    if dt.date() == now.date():
        return dt.strftime("今天 %H:%M")
    return dt.strftime("%m-%d %H:%M")


def _session_label(s: dict) -> str:
    title = (s.get("title") or "对话").strip()
    if title == s.get("session_id"):
        title = "对话"
    if len(title) > 26:
        title = title[:26] + "…"
    n = int(s.get("message_count") or 0)
    t = _format_session_time(str(s.get("updated_at") or ""))
    suffix = f"{n} 条"
    if t:
        suffix = f"{suffix} · {t}"
    return f"{title}（{suffix}）"


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


def _load_session_into_ui(session_id: str, *, bump_nav: bool = False) -> None:
    st.session_state.agent_session = SQLiteSession(session_id, db_path=SESSION_DB)
    st.session_state.ui_messages = load_messages(
        UI_DB, session_id, owner_id=st.session_state.web_owner_id
    )
    st.session_state.pending_approval = restore_pending_approval(session_id)
    if bump_nav:
        st.session_state.session_nav_token = (
            st.session_state.get("session_nav_token", 0) + 1
        )
    _sync_run_config()


def _new_session_id() -> str:
    return f"web_{st.session_state.web_owner_id}_{uuid.uuid4().hex}"


def _switch_session(session_id: str) -> None:
    if not session_id.startswith(f"web_{st.session_state.web_owner_id}_"):
        st.error("无法访问该会话")
        return
    if session_id == st.session_state.agent_session.session_id:
        return
    _load_session_into_ui(session_id, bump_nav=True)
    st.rerun()


def _create_new_session() -> None:
    new_id = _new_session_id()
    _load_session_into_ui(new_id, bump_nav=True)
    st.session_state.pending_approval = None


def _resolve_initial_session_id() -> str:
    """每次打开页面使用新会话，不自动恢复旧对话。"""
    return _new_session_id()


def _init_state() -> None:
    ensure_workspace_synced()
    prune_empty_sessions(UI_DB)
    configure_tracing()
    if "web_authenticated" not in st.session_state:
        st.session_state.web_authenticated = False
    if "web_owner_id" not in st.session_state:
        st.session_state.web_owner_id = uuid.uuid4().hex
    if "session_nav_token" not in st.session_state:
        st.session_state.session_nav_token = 0
    if "sandbox_health" not in st.session_state:
        st.session_state.sandbox_health = None
    if SANDBOX_HEALTH_CHECK_ON_STARTUP and is_docker_available():
        st.session_state.sandbox_health = check_sandbox_health().to_dict()
    if "run_model" not in st.session_state:
        st.session_state.run_model = os.getenv("RUN_DEFAULT_MODEL") or DEEPSEEK_FLASH

    if "agent_session" not in st.session_state:
        _load_session_into_ui(_resolve_initial_session_id())
    if "ui_messages" not in st.session_state:
        st.session_state.ui_messages = load_messages(
            UI_DB,
            st.session_state.agent_session.session_id,
            owner_id=st.session_state.web_owner_id,
        )
    if "run_config" not in st.session_state:
        _sync_run_config()
    if "run_config_error" not in st.session_state:
        st.session_state.run_config_error = None
    if "pending_approval" not in st.session_state:
        st.session_state.pending_approval = None
    if "show_react_steps" not in st.session_state:
        st.session_state.show_react_steps = SHOW_REACT_STEPS


def _append_and_persist(
    role: str,
    content: str,
    *,
    react_steps: list[ReactStep] | None = None,
) -> None:
    meta_json = None
    if react_steps:
        meta_json = steps_to_json(react_steps)
    msg: dict = {"role": role, "content": content}
    if meta_json:
        msg["meta_json"] = meta_json
    st.session_state.ui_messages.append(msg)
    append_message(
        UI_DB,
        st.session_state.agent_session.session_id,
        role,
        content,
        meta_json=meta_json,
        owner_id=st.session_state.web_owner_id,
    )


def _render_react_steps(steps: list[ReactStep]) -> None:
    if not steps:
        return
    summary = compact_summary(steps)
    with st.expander(f"步骤 · {len(steps)}（{summary}）", expanded=False):
        for step in steps:
            st.markdown(
                f'<div class="react-step-line">[{step.layer}] {step.agent} · '
                f"{step.label}</div>",
                unsafe_allow_html=True,
            )
            if step.detail:
                st.caption(step.detail[:500])


def _is_ephemeral_session(session_id: str) -> bool:
    return (
        count_messages(
            UI_DB, session_id, owner_id=st.session_state.web_owner_id
        )
        == 0
    )


def _render_advanced_settings(current_id: str) -> None:
    with st.expander("高级设置", expanded=False):
        st.caption(f"会话 ID：`{current_id}`")
        if FILE_AGENT_ENABLED:
            st.caption(f"文件工作区 · `{FILE_AGENT_WORKSPACE}`")
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

        data_dir = DATA_DIR
        ok = (data_dir / "products.json").exists() and (data_dir / "orders.json").exists()
        if not ok:
            st.info("沙箱示例数据未生成：`python scripts/generate_catalog.py`（仅数据分析需要）")


def _render_sidebar() -> None:
    current_id = st.session_state.agent_session.session_id
    level, status_text = _system_status()
    nav_token = st.session_state.session_nav_token

    with st.sidebar:
        if st.button("＋ 新对话", type="primary", use_container_width=True):
            _create_new_session()
            st.rerun()

        st.markdown(
            f'<span class="status-pill {level}">● {status_text}</span>',
            unsafe_allow_html=True,
        )

        st.divider()

        sessions = list_sessions(
            UI_DB, min_messages=1, owner_id=st.session_state.web_owner_id
        )
        session_ids = [str(s["session_id"]) for s in sessions]
        labels = {str(s["session_id"]): _session_label(s) for s in sessions}

        if _is_ephemeral_session(current_id):
            st.caption("当前：新对话（发送首条消息后保存到历史）")
            if sessions:
                picker_key = f"history_picker_{nav_token}"
                selected_history = st.selectbox(
                    "切换到历史对话",
                    options=session_ids,
                    index=None,
                    placeholder="选择历史对话…",
                    format_func=lambda sid: labels.get(sid, sid),
                    key=picker_key,
                    label_visibility="collapsed",
                )
                # 仅当用户主动从下拉框选择时才切换（不能用 if picked，默认第一项会立刻跳回旧会话）
                if selected_history and selected_history != current_id:
                    _switch_session(selected_history)
        elif sessions:
            if current_id not in session_ids:
                session_ids = [current_id, *session_ids]
                labels[current_id] = "当前对话"
            picked = st.selectbox(
                "历史对话",
                options=session_ids,
                index=session_ids.index(current_id),
                format_func=lambda sid: labels.get(sid, sid),
                key=f"session_picker_{nav_token}",
                label_visibility="collapsed",
            )
            if picked != current_id:
                _switch_session(picked)
        else:
            st.caption("发送消息后自动出现在这里")

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

        st.toggle(
            "显示 ReAct 步骤",
            key="show_react_steps",
            help="默认折叠缩写；展开可看工具调用详情",
        )

        st.divider()
        if st.button("清空当前对话", use_container_width=True):
            clear_session_messages(
                UI_DB, current_id, owner_id=st.session_state.web_owner_id
            )
            clear_persisted_session(current_id)
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            _load_session_into_ui(_new_session_id(), bump_nav=True)
            st.rerun()

        if st.button("删除全部历史", use_container_width=True):
            clear_all_ui_sessions(UI_DB, owner_id=st.session_state.web_owner_id)
            clear_persisted_session(current_id)
            st.session_state.ui_messages = []
            st.session_state.pending_approval = None
            _load_session_into_ui(_new_session_id(), bump_nav=True)
            st.rerun()


def _render_quick_prompts() -> None:
    """空对话时展示快捷问题（点击后走统一的消息派发逻辑）。"""
    st.markdown(
        """
        <div class="empty-wrap">
            <h3>有什么可以帮您？</h3>
            <p>阅读总结 workspace 文件，或在沙箱中统计分析、生成报表</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, text in enumerate(QUICK_PROMPTS):
        with cols[i % 2]:
            if st.button(text, key=f"quick_{i}", use_container_width=True):
                st.session_state.dispatch_prompt = text
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


def _execute_agent_turn(prompt: str) -> None:
    """在同一轮渲染内流式执行 Agent，避免整页双重重跑。"""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        buffer = {"text": ""}

        def on_delta(delta: str) -> None:
            buffer["text"] += delta
            placeholder.markdown(buffer["text"])

        react_steps: list[ReactStep] = []

        try:
            text, result, react_steps = _run_async(
                handle_user_turn(
                    workspace_router,
                    prompt,
                    st.session_state.agent_session,
                    st.session_state.run_config,
                    on_delta=on_delta,
                )
            )
        except MaxTurnsExceeded:
            _append_and_persist("assistant", "运行超时：问题较复杂，请拆分后重试。")
            return
        except Exception as exc:
            _append_and_persist(
                "assistant", f"**运行失败**：{type(exc).__name__}: {exc}"
            )
            return

        if isinstance(result, PendingApprovalRecord):
            st.session_state.pending_approval = result
            note = buffer["text"] or "已触发敏感操作，请在下方确认。"
            _append_and_persist("assistant", note, react_steps=react_steps)
        elif result and getattr(result, "interruptions", None):
            st.session_state.pending_approval = result
            note = buffer["text"] or "已触发敏感操作，请在下方确认。"
            _append_and_persist("assistant", note, react_steps=react_steps)
        else:
            streamed = sanitize_user_visible_output(buffer["text"])
            final = sanitize_user_visible_output(text or "") or streamed
            if final:
                placeholder.markdown(final)
                _append_and_persist("assistant", final, react_steps=react_steps)
                if st.session_state.show_react_steps:
                    _render_react_steps(react_steps)


def _render_approval_card() -> None:
    items = describe_interruptions(st.session_state.pending_approval)
    items_html = "".join(f"<li>{html.escape(item)}</li>" for item in items)
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


def _dispatch_user_prompt(prompt: str) -> None:
    """执行一轮用户消息（快捷问题或输入框共用）。"""
    _append_and_persist("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)
    _execute_agent_turn(prompt)


def _render_chat() -> None:
    st.markdown(
        """
        <div class="app-hero">
            <h1>通用工作台助手</h1>
            <p>聊天 · 文案 · 文件 · 数据 · 层级 ReAct</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dispatch = st.session_state.pop("dispatch_prompt", None)
    if dispatch:
        _dispatch_user_prompt(dispatch)
        st.rerun()

    for msg in st.session_state.ui_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("meta_json"):
                steps = steps_from_json(msg["meta_json"])
                if steps and st.session_state.show_react_steps:
                    _render_react_steps(steps)

    if st.session_state.pending_approval:
        _render_approval_card()

    if not st.session_state.ui_messages:
        _render_quick_prompts()

    prompt = st.chat_input(
        "输入消息，Enter 发送",
        disabled=bool(st.session_state.pending_approval),
    )
    if prompt:
        if st.session_state.pending_approval:
            st.warning("请先处理上方审批，再继续输入。")
            return
        _dispatch_user_prompt(prompt)
        st.rerun()


def main() -> None:
    _init_state()
    if not _ensure_authenticated():
        return
    _render_sidebar()
    _render_chat()


if __name__ == "__main__":
    main()
