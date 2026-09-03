"""护栏与审核：输入阻断、工具执行前校验、输出安全、审批审计。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    input_guardrail,
    output_guardrail,
)
from agents.tool_guardrails import (
    ToolGuardrailFunctionOutput,
    ToolInputGuardrailData,
    tool_input_guardrail,
)

from sandbox.audit import log_audit_event

# ---------------------------------------------------------------------------
# 规则集（低成本、阻塞执行，run_in_parallel=False）
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt",
    r"你现在是(?!.*助手)",
    r"扮演(?!.*助手).*(黑客|管理员|root)",
    r"jailbreak",
    r"<\s*/?\s*system\s*>",
)

_EXFIL_PATTERNS = (
    r"\b(api[_-]?key|secret|password|token|credential)\b",
    r"\.env",
    r"sk-[a-zA-Z0-9]{10,}",
    r"导出\s*(全部|所有)\s*(用户|订单|客户)",
    r"上传\s*到\s*(http|ftp)",
    r"curl\s+",
    r"wget\s+",
)

_OFF_TOPIC_PATTERNS = (
    r"作业|数学题|物理题|化学题|英语作文",
    r"写一段代码|帮我编程|leetcode",
    r"写一篇论文|毕业论文",
)

_GENERAL_ASSISTANT_HINTS = (
    r"你好|谢谢|帮助|怎么用|是什么|为什么|如何|解释|讨论|聊聊",
    r"文案|邮件|通知|标题|口号|营销|小红书|朋友圈|作文|写诗|写一段|润色",
    r"总结|摘要|概括|建议|想法|意见|推荐",
)

_WORKSPACE_TASK_HINTS = (
    r"文件|文件夹|目录|folder|file|读取|写入|保存|创建文件|列出|整理|总结|摘要",
    r"txt|csv|json|markdown|\.md|workspace_user|工作区|data/",
    r"导出|清单|excel|表格|报表|分析|统计|图表|处理|数据|dataset",
    r"阅读|概括|归纳|笔记|notes|exports",
)

_SECRET_IN_OUTPUT = re.compile(
    r"(sk-[a-zA-Z0-9]{10,}|DEEPSEEK_API_KEY|OPENAI_API_KEY|WEB_APP_API_KEY|"
    r"api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)
_INTERNAL_PATH = re.compile(r"(/workspace/|sandbox/persist/|\\\.env)", re.IGNORECASE)

_ORDER_ID_RE = re.compile(r"^#?\d{5}$")


def _extract_user_text(user_input: str | list[Any]) -> str:
    if isinstance(user_input, str):
        return user_input.strip()
    parts: list[str] = []
    for item in user_input:
        if isinstance(item, dict):
            content = item.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(str(block.get("text", "")))
        elif isinstance(item, str):
            parts.append(item)
    return "\n".join(parts).strip()


def _matches_any(text: str, patterns: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for pattern in patterns:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return pattern
    return None


def _has_general_assistant_hint(text: str) -> bool:
    return _matches_any(text, _GENERAL_ASSISTANT_HINTS) is not None


def _has_workspace_task_hint(text: str) -> bool:
    return _matches_any(text, _WORKSPACE_TASK_HINTS) is not None


def _has_router_allowed_topic(text: str) -> bool:
    return _has_workspace_task_hint(text) or _has_general_assistant_hint(text)


def _tripwire(
    *,
    reason: str,
    user_message: str,
    guardrail_name: str,
    extra: dict[str, Any] | None = None,
) -> GuardrailFunctionOutput:
    log_audit_event(
        "input_guardrail_blocked",
        status="blocked",
        detail=reason,
        extra={"guardrail": guardrail_name, **(extra or {})},
    )
    return GuardrailFunctionOutput(
        tripwire_triggered=True,
        output_info={
            "reason": reason,
            "user_message": user_message,
            "guardrail": guardrail_name,
        },
    )


@input_guardrail(name="block_prompt_injection", run_in_parallel=False)
def block_prompt_injection(
    context: RunContextWrapper[Any],
    agent: Agent[Any],
    user_input: str | list[Any],
) -> GuardrailFunctionOutput:
    _ = context, agent
    text = _extract_user_text(user_input)
    if not text:
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)

    hit = _matches_any(text, _INJECTION_PATTERNS)
    if hit:
        return _tripwire(
            reason=f"prompt_injection:{hit}",
            user_message="检测到疑似提示注入，请直接描述文件阅读、数据整理或报表需求。",
            guardrail_name="block_prompt_injection",
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)


@input_guardrail(name="block_sensitive_exfiltration", run_in_parallel=False)
def block_sensitive_exfiltration(
    context: RunContextWrapper[Any],
    agent: Agent[Any],
    user_input: str | list[Any],
) -> GuardrailFunctionOutput:
    _ = context, agent
    text = _extract_user_text(user_input)
    if not text:
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)

    hit = _matches_any(text, _EXFIL_PATTERNS)
    if hit:
        return _tripwire(
            reason=f"exfiltration:{hit}",
            user_message="无法协助获取密钥、凭证或批量导出敏感数据。请说明具体文件或分析任务。",
            guardrail_name="block_sensitive_exfiltration",
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)


@input_guardrail(name="block_off_topic", run_in_parallel=False)
def block_off_topic(
    context: RunContextWrapper[Any],
    agent: Agent[Any],
    user_input: str | list[Any],
) -> GuardrailFunctionOutput:
    _ = context, agent
    text = _extract_user_text(user_input)
    if not text:
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)

    if _has_router_allowed_topic(text):
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)

    hit = _matches_any(text, _OFF_TOPIC_PATTERNS)
    if hit:
        return _tripwire(
            reason=f"off_topic:{hit}",
            user_message=(
                "我是通用工作台助手，可聊天、写文案、处理文件与数据。"
                "请换个相关问题试试。"
            ),
            guardrail_name="block_off_topic",
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)


@output_guardrail(name="sanitize_agent_output")
def sanitize_agent_output(
    context: RunContextWrapper[Any],
    agent: Agent[Any],
    output: Any,
) -> GuardrailFunctionOutput:
    _ = context, agent
    text = output if isinstance(output, str) else str(output)
    if _SECRET_IN_OUTPUT.search(text) or _INTERNAL_PATH.search(text):
        log_audit_event(
            "output_guardrail_blocked",
            status="blocked",
            detail="sensitive_content_in_output",
            extra={"agent": getattr(agent, "name", "unknown")},
        )
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info={
                "reason": "sensitive_output",
                "user_message": "回复包含敏感信息，已被安全策略拦截。请重新提问。",
            },
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)


def _parse_tool_args(data: ToolInputGuardrailData) -> dict[str, Any]:
    try:
        parsed = json.loads(data.context.tool_arguments or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@tool_input_guardrail(name="validate_order_id")
def validate_order_id(data: ToolInputGuardrailData) -> ToolGuardrailFunctionOutput:
    args = _parse_tool_args(data)
    order_id = str(args.get("order_id", "")).strip()
    if not order_id:
        return ToolGuardrailFunctionOutput.reject_content(
            message="请提供订单号（5 位数字）。",
            output_info={"check": "missing_order_id"},
        )
    if not _ORDER_ID_RE.match(order_id):
        log_audit_event(
            "tool_guardrail_rejected",
            status="rejected",
            detail="invalid_order_id_format",
            extra={"tool": data.context.tool_name, "order_id": order_id},
        )
        return ToolGuardrailFunctionOutput.reject_content(
            message="订单号格式无效，请提供 5 位数字订单号（如 10001）。",
            output_info={"check": "order_id_format", "order_id": order_id},
        )
    return ToolGuardrailFunctionOutput.allow(output_info={"check": "order_id_ok"})


@tool_input_guardrail(name="validate_refund_request")
def validate_refund_request(data: ToolInputGuardrailData) -> ToolGuardrailFunctionOutput:
    args = _parse_tool_args(data)
    order_id = str(args.get("order_id", "")).strip()
    reason = str(args.get("reason", "")).strip()

    if not reason or len(reason) < 4:
        return ToolGuardrailFunctionOutput.reject_content(
            message="退款原因过短，请补充具体说明（至少 4 个字）。",
            output_info={"check": "refund_reason_too_short"},
        )

    suspicious = _matches_any(
        reason,
        (
            r"测试审批",
            r"随便填",
            r"ignore\s+instructions",
            r"删除\s*所有",
        ),
    )
    if suspicious:
        log_audit_event(
            "tool_guardrail_rejected",
            status="rejected",
            detail=f"suspicious_refund_reason:{suspicious}",
            extra={"tool": data.context.tool_name, "order_id": order_id},
        )
        return ToolGuardrailFunctionOutput.raise_exception(
            output_info={"check": "suspicious_refund_reason"},
        )

    return ToolGuardrailFunctionOutput.allow(
        output_info={"check": "refund_request_ok", "order_id": order_id},
    )


@tool_input_guardrail(name="validate_file_tool_path")
def validate_file_tool_path(data: ToolInputGuardrailData) -> ToolGuardrailFunctionOutput:
    from tools.file import is_blocked_relative_path, is_data_virtual_path

    args = _parse_tool_args(data)
    tool_name = data.context.tool_name or ""
    path_key = "relative_dir" if tool_name == "list_files" else "relative_path"
    rel = str(args.get(path_key, "")).strip()

    if tool_name in {"read_file", "write_file"} and not rel:
        return ToolGuardrailFunctionOutput.reject_content(
            message="请提供文件路径，例如 demo/hello.txt 或 data/products.json。",
            output_info={"check": "missing_file_path"},
        )

    if tool_name == "write_file" and rel and is_data_virtual_path(rel):
        return ToolGuardrailFunctionOutput.reject_content(
            message="data/ 为只读示例数据，不可写入。请使用 workspace_user 下路径。",
            output_info={"check": "data_readonly"},
        )

    if rel:
        blocked = is_blocked_relative_path(rel)
        if blocked:
            log_audit_event(
                "tool_guardrail_rejected",
                status="rejected",
                detail=f"blocked_file_path:{blocked}",
                extra={"tool": tool_name, "path": rel},
            )
            return ToolGuardrailFunctionOutput.reject_content(
                message="该路径不允许访问（越界或命中安全黑名单）。",
                output_info={"check": "blocked_file_path", "reason": blocked},
            )

    return ToolGuardrailFunctionOutput.allow(output_info={"check": "file_path_ok"})


def format_input_guardrail_message(exc: Exception) -> str:
    from agents.exceptions import InputGuardrailTripwireTriggered

    if isinstance(exc, InputGuardrailTripwireTriggered):
        info = exc.guardrail_result.output.output_info
        if isinstance(info, dict) and info.get("user_message"):
            return str(info["user_message"])
        name = exc.guardrail_result.guardrail.get_name()
        return f"请求未通过输入护栏（{name}），请调整后重试。"
    return f"请求被安全策略拦截：{exc}"


def format_output_guardrail_message(exc: Exception) -> str:
    from agents.exceptions import OutputGuardrailTripwireTriggered

    if isinstance(exc, OutputGuardrailTripwireTriggered):
        info = exc.guardrail_result.output.output_info
        if isinstance(info, dict) and info.get("user_message"):
            return str(info["user_message"])
    return "回复未通过输出安全校验，请重新提问。"


def log_approval_decision(
    *,
    session_id: str,
    approved: bool,
    interruptions: list[Any],
    actor: str | None = None,
) -> None:
    tools = []
    for item in interruptions:
        name = getattr(item, "tool_name", None) or "unknown"
        args = _extract_interruption_args(item)
        tools.append({"tool": name, "arguments": args})
    log_audit_event(
        "human_approval_decision",
        status="approved" if approved else "rejected",
        session_id=session_id,
        actor=actor or "web_user",
        extra={"tools": tools},
    )


def _extract_interruption_args(interruption: Any) -> dict[str, Any]:
    raw = getattr(interruption, "raw_item", None)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        args_raw = raw.get("arguments") or raw.get("input")
    else:
        args_raw = getattr(raw, "arguments", None) or getattr(raw, "input", None)
    if not args_raw:
        return {}
    if isinstance(args_raw, dict):
        return args_raw
    if isinstance(args_raw, str):
        try:
            parsed = json.loads(args_raw)
            return parsed if isinstance(parsed, dict) else {"raw": args_raw}
        except json.JSONDecodeError:
            return {"raw": args_raw}
    return {"raw": str(args_raw)}


def describe_interruption_detail(interruption: Any) -> str:
    name = getattr(interruption, "tool_name", None) or "unknown"
    args = _extract_interruption_args(interruption)
    if not args:
        return f"工具 `{name}` 需要人工审批"
    arg_text = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return f"工具 `{name}`({arg_text}) 需要人工审批"


# 供 Agent 挂载
ROUTER_INPUT_GUARDRAILS = [
    block_prompt_injection,
    block_sensitive_exfiltration,
    block_off_topic,
]

SPECIALIST_OUTPUT_GUARDRAILS = [sanitize_agent_output]

GUARDRAILS_ENABLED = os.getenv("GUARDRAILS_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
