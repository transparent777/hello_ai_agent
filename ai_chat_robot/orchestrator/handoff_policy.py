"""Handoff 辅助：意图识别、Router 输入增强、终稿清洗与护栏兜底。"""

from __future__ import annotations

import re

from config.settings import ROUTER_VERIFY_MAX_RETRIES
from orchestrator.turn_state import get_turn_state
from services.react_trace import ReactStep

_DELIVERABLE_PATTERNS = (
    r"docx|word|\.doc\b",
    r"导出.*(?:csv|xlsx|excel|表格|报表)",
    r"(?:csv|xlsx|excel|表格).*(?:导出|生成|制作)",
    r"(?:统计|分析|报表|数据处理).*(?:数据|订单|销售|json)",
    r"(?:计划表|作文|思政|长文).*(?:写|生成|制作|导出)",
    r"(?:写|生成|制作).*(?:计划表|作文|思政|docx|word)",
)

_FAILURE_NARRATION = (
    r"转接.*(?:失败|无效|没有产生|似乎|未成功)",
    r"让我(?:重新|再).*(?:转接|transfer)",
    r"看起来转接",
    r"handoff.*(?:fail|失败)",
)

_ENGLISH_LINE = re.compile(r"^[A-Za-z0-9\s,'\"`.:;!?\-–—()]+$")

_ROUTER_AGENT_NAMES = frozenset({"workspace_router", "customer_service_router"})

_SPECIALIST_NAMES = frozenset(
    {"document_specialist", "writer_specialist", "data_specialist"}
)

_DELIVERABLE_HINT = (
    "[系统-勿复述] 交付型任务：缺关键信息时可先简短追问用户对齐；"
    "信息足够后 handoff 给对应专员，由 L1 验收后终稿。"
    "禁止声称转接失败，禁止输出 DSML/英文工具原文。\n\n"
)


def detect_deliverable_intent(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(p, lowered, flags=re.IGNORECASE) for p in _DELIVERABLE_PATTERNS)


def prepare_router_input(user_input: str) -> str:
    if detect_deliverable_intent(user_input):
        return _DELIVERABLE_HINT + user_input
    return user_input


def can_router_dispatch_specialist(
    _ctx: object,
    _calling_agent: object,
    *,
    specialist_name: str,
) -> bool:
    return get_turn_state().can_dispatch(
        specialist_name,
        max_retries=ROUTER_VERIFY_MAX_RETRIES,
    )


def note_react_step(step: ReactStep) -> None:
    state = get_turn_state()
    label = step.label
    detail = step.detail

    if step.kind == "handoff":
        target = _handoff_target_name(label)
        if step.layer == "L1" and target in _SPECIALIST_NAMES:
            state.record_dispatch(target)
        if step.layer == "L2" and target in _ROUTER_AGENT_NAMES:
            state.verification_received = True

    if step.kind == "observation":
        if "验收" in detail:
            state.verification_received = True
        if "已导出 DOCX" in detail:
            for path in _extract_export_paths(detail):
                state.export_paths = [path]


def _handoff_target_name(label: str) -> str:
    raw = label.split("→")[-1].strip()
    return raw.removeprefix("transfer_to_")


def _extract_export_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(
        r"(?:exports/[^\s`\"']+\.(?:docx|csv|xlsx|md)|"
        r"[A-Za-z]:\\[^\s`\"']+\.(?:docx|csv|xlsx|md))",
        text,
        flags=re.IGNORECASE,
    ):
        paths.append(match.group(0))
    return paths


def _is_mostly_english(line: str) -> bool:
    if not line or len(line) < 12:
        return False
    ascii_chars = sum(1 for ch in line if ord(ch) < 128)
    return ascii_chars / len(line) > 0.85 and bool(_ENGLISH_LINE.match(line))


_DSML_BLOCK = re.compile(
    r"<｜｜DSML｜｜[\s\S]*?(?:</｜｜DSML｜｜tool_calls>|$)",
    re.IGNORECASE,
)


def sanitize_user_visible_output(text: str) -> str:
    """终稿展示用：去掉 DSML、英文独白、转接废话。"""
    if not text:
        return text

    cleaned = _DSML_BLOCK.sub("", text)
    cleaned = re.sub(
        r"(?:^|\n)(?:I need to|Let me|Now let me|I'll |I will |I'm going to|handle this docx)[^\n]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = sanitize_router_output(cleaned)
    return cleaned or ""


_DSML_MARKERS = ("<｜｜DSML｜｜", "tool_calls", 'invoke name="transfer_to_')


def _looks_like_tool_markup(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in _DSML_MARKERS)


def sanitize_router_output(text: str) -> str:
    if not text:
        return text

    if _looks_like_tool_markup(text):
        return ""

    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if _looks_like_tool_markup(stripped):
            continue
        if _is_mostly_english(stripped):
            continue
        if any(re.search(p, stripped, flags=re.IGNORECASE) for p in _FAILURE_NARRATION):
            continue
        kept.append(line)

    return "\n".join(kept).strip()


def build_deliverable_fallback(steps: list[ReactStep]) -> str | None:
    paths = _collect_deliverable_paths(steps)
    if not paths:
        return None

    path = paths[-1]
    return (
        f"已为您导出 Word 文档：\n\n"
        f"- `{path}`\n\n"
        f"如需调整内容或格式，请说明要改的部分。"
    )


def _collect_deliverable_paths(steps: list[ReactStep]) -> list[str]:
    """仅取本轮最后一次 export_docx 工具返回的路径。"""
    last_path: str | None = None
    awaiting_export = False

    for step in steps:
        if step.kind == "action" and "export_docx" in step.label:
            awaiting_export = True
            continue
        if step.kind != "observation" or not awaiting_export:
            continue
        if "已导出 DOCX" not in step.detail:
            continue
        paths = [
            p
            for p in _extract_export_paths(step.detail)
            if not _is_placeholder_path(p)
        ]
        if paths:
            last_path = paths[0]
        awaiting_export = False

    if last_path:
        return [last_path]

    # 次选：验收 handoff 摘要里提到的路径（仍只取最后一个）
    verify_path: str | None = None
    for step in steps:
        if step.kind != "observation" or "验收" not in step.detail:
            continue
        if "export_docx" not in step.detail:
            continue
        paths = [
            p
            for p in _extract_export_paths(step.detail)
            if not _is_placeholder_path(p)
        ]
        if paths:
            verify_path = paths[0]
    return [verify_path] if verify_path else []


def _is_placeholder_path(path: str) -> bool:
    lowered = path.lower()
    return "xxx" in lowered or lowered.endswith("/test.docx")
