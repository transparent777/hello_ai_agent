"""
电商 Agent：Agent Loop + Session（半托管）+ 流式输出 + 审批恢复

Agent Loop（Runner 持续循环直到真正停止）：
  1. 调用模型
  2. 检查输出
  3. 有 tool calls → 执行工具 → 继续循环
  4. 有 handoff → 切换智能体 → 继续循环
  5. 有最终答案且无待执行工具 → 返回结果

流式三条规则：
  1. stream 完全结束后，才读取 final_output / interruptions
  2. 审批暂停后，从 RunState 恢复，不要开新 user turn
  3. 中途取消流式后若要继续同一轮，也从 state 恢复
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent
from pathlib import Path

from agents import (
    Agent,
    AsyncOpenAI,
    ModelSettings,
    OpenAIChatCompletionsModel,
    OpenAIProvider,
    RunConfig,
    Runner,
    SQLiteSession,
    set_tracing_disabled,
)
from agents.tracing import flush_traces, trace
from agents.exceptions import (
    InputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
    OutputGuardrailTripwireTriggered,
    ToolInputGuardrailTripwireTriggered,
)

from approval_store import (
    PendingApprovalRecord,
    build_pending_record,
    clear_pending_approval,
    load_pending_approval,
    save_pending_approval,
)
from ecommerce_tools import get_order_status, process_refund, search_products
from guardrails import (
    GUARDRAILS_ENABLED,
    ROUTER_INPUT_GUARDRAILS,
    SPECIALIST_OUTPUT_GUARDRAILS,
    describe_interruption_detail,
    format_input_guardrail_message,
    format_output_guardrail_message,
    log_approval_decision,
)
from sandbox.analytics_tools import (
    run_order_analysis,
    run_pricing_simulation,
    run_sales_report,
)
from sandbox.config import (
    SANDBOX_INSTRUCTIONS,
    build_manifest,
    build_sandbox_capabilities,
    merge_run_config_with_sandbox,
)
from sandbox.health import check_sandbox_health
from sandbox.metrics import record_event, track_duration
from sandbox.ops import run_with_retries, run_with_sandbox_slot
from sandbox.memory_sync import refresh_memory_summary
from sandbox.session_store import save_sandbox_resume_payload
from sandbox.runtime import (
    analytics_backend_available,
    ensure_workspace_synced,
    is_docker_available,
    publish_workspace_outputs,
    sandbox_mode_label,
)
from mcp_integration.runtime import (
    build_hosted_mcp_tools,
    build_local_mcp_servers,
    collect_mcp_servers_from_agents,
    run_with_mcp_lifecycle,
)
from tracing_setup import TRACING_ENABLED, configure_tracing
from sandbox.settings import (
    SANDBOX_ALLOW_LOCAL_FALLBACK,
    SANDBOX_HEALTH_CHECK_ON_STARTUP,
    SANDBOX_PERSIST_SESSION,
    SANDBOX_RUN_TIMEOUT_SECONDS,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")
load_dotenv(_script_dir.parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

set_tracing_disabled(not TRACING_ENABLED)
configure_tracing()

# ---------------------------------------------------------------------------
# Models and providers
# ---------------------------------------------------------------------------

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_FLASH = "deepseek-v4-flash"
DEEPSEEK_PRO = "deepseek-v4-pro"
KNOWN_MODELS = frozenset({DEEPSEEK_FLASH, DEEPSEEK_PRO})

deepseek_provider = OpenAIProvider(
    api_key=api_key,
    base_url=DEEPSEEK_BASE_URL,
    use_responses=False,
)

deepseek_client = AsyncOpenAI(
    api_key=api_key,
    base_url=DEEPSEEK_BASE_URL,
)

flash_model = OpenAIChatCompletionsModel(
    model=DEEPSEEK_FLASH,
    openai_client=deepseek_client,
)
pro_model = OpenAIChatCompletionsModel(
    model=DEEPSEEK_PRO,
    openai_client=deepseek_client,
)

flash_settings = ModelSettings(
    temperature=0.3,
    extra_body={"thinking": {"type": "disabled"}},
)
pro_settings = ModelSettings(
    temperature=0.3,
    extra_body={"thinking": {"type": "disabled"}},
)

PROCESS_DEFAULT_MODEL = os.getenv("DEEPSEEK_DEFAULT_MODEL") or DEEPSEEK_FLASH
os.environ.setdefault("OPENAI_DEFAULT_MODEL", PROCESS_DEFAULT_MODEL)

SESSION_DB = _script_dir / "sessions.db"
SESSION_ID = os.getenv("ECOMMERCE_SESSION_ID", "ecommerce_customer_session")
MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "12"))


def build_run_config(
    run_model: str | None = None,
    *,
    with_sandbox: bool | None = None,
    session_id: str | None = None,
) -> RunConfig:
    model_name = run_model or os.getenv("RUN_DEFAULT_MODEL") or PROCESS_DEFAULT_MODEL
    if model_name not in KNOWN_MODELS:
        raise ValueError(f"未知模型 {model_name!r}，请使用 {sorted(KNOWN_MODELS)}")
    base = RunConfig(
        model_provider=deepseek_provider,
        model=model_name,
        tracing_disabled=not TRACING_ENABLED,
        tool_not_found_behavior="return_error_to_model",
    )

    use_sandbox = is_docker_available() if with_sandbox is None else with_sandbox
    if not use_sandbox:
        return base

    ensure_workspace_synced()
    if SANDBOX_HEALTH_CHECK_ON_STARTUP:
        health = check_sandbox_health()
        if not health.ok:
            raise RuntimeError("沙箱健康检查未通过: " + "; ".join(health.issues))
    return merge_run_config_with_sandbox(
        base,
        session_id=session_id,
        persist_session=SANDBOX_PERSIST_SESSION,
    )


def persist_sandbox_session(session_id: str | None, result: Any) -> None:
    """保存沙箱 resume 状态（E1/E3：供下次 run 或审批后恢复）。"""
    if not session_id or not SANDBOX_PERSIST_SESSION or result is None:
        return
    try:
        run_state = result.to_state()
        sandbox_payload = run_state._sandbox
        if isinstance(sandbox_payload, dict):
            save_sandbox_resume_payload(session_id, sandbox_payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def _create_analytics_specialist():
    """Docker 可用 → SandboxAgent；显式允许时 → 本机脚本回退；否则 → 不可用占位 Agent。"""
    shared_instructions = (
        "你是电商数据分析专员。根据用户需求：\n"
        "- 分析订单数据 → 跑订单分析\n"
        "- 定价/打折模拟 → 跑定价脚本\n"
        "- 生成报表 → 跑报表脚本\n"
        "开始前阅读 repo/task.md；若存在 memories/memory_summary.md 可参考历史分析。\n"
        "用中文总结关键数字，并说明结果文件位置（如 output/report.md）。"
    )

    if is_docker_available():
        from agents.sandbox import SandboxAgent

        ensure_workspace_synced()
        return SandboxAgent(
            name="analytics_specialist",
            handoff_description=(
                "处理订单数据分析、定价模拟、销售报表生成（Docker 沙箱）。"
            ),
            instructions=f"{SANDBOX_INSTRUCTIONS}\n\n{shared_instructions}",
            model=pro_model,
            model_settings=pro_settings,
            default_manifest=build_manifest(),
            capabilities=build_sandbox_capabilities(),
        )

    if SANDBOX_ALLOW_LOCAL_FALLBACK:
        return Agent(
            name="analytics_specialist",
            handoff_description=(
                "处理订单数据分析、定价模拟、销售报表生成（本机脚本回退）。"
            ),
            instructions=(
                f"{shared_instructions}\n"
                "使用工具 run_order_analysis / run_pricing_simulation / run_sales_report，"
                "不要假装已经执行脚本。"
            ),
            tools=[run_order_analysis, run_pricing_simulation, run_sales_report],
            model=pro_model,
            model_settings=pro_settings,
        )

    return Agent(
        name="analytics_specialist",
        handoff_description="数据分析需要 Docker 沙箱，当前环境不可用。",
        instructions=(
            "你是电商数据分析专员，但当前 Docker 沙箱不可用。\n"
            "请明确告知用户：需要启动 Docker Desktop 后才能进行订单分析、定价模拟或报表生成。\n"
            "不要假装已经执行脚本或编造分析结果。"
        ),
        model=pro_model,
        model_settings=pro_settings,
    )


analytics_specialist = _create_analytics_specialist()


def _create_product_specialist() -> Agent:
    from mcp_integration.settings import MCP_HOSTED_ENABLED, MCP_LOCAL_ENABLED

    tools: list = []
    if not MCP_LOCAL_ENABLED:
        tools.append(search_products)
    if MCP_HOSTED_ENABLED:
        tools.extend(build_hosted_mcp_tools())
    mcp_hint = (
        "商品数据可通过 MCP 工具 search_products 查询（本地私有 MCP 或托管 MCP）。"
        if MCP_LOCAL_ENABLED or MCP_HOSTED_ENABLED
        else "需要查商品时调用 search_products，"
    )
    return Agent(
        name="product_specialist",
        handoff_description="处理商品咨询、比价、推荐与库存查询。",
        instructions=(
            "你是电商商品顾问。根据用户需求推荐合适商品，说明价格与库存。"
            f"{mcp_hint}"
            "回答简洁、有购买引导。"
        ),
        tools=tools,
        mcp_servers=build_local_mcp_servers() if MCP_LOCAL_ENABLED else [],
        model=flash_model,
        model_settings=flash_settings,
        output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
    )


product_specialist = _create_product_specialist()

order_specialist = Agent(
    name="order_specialist",
    handoff_description="处理订单查询、物流跟踪、退换货与售后问题。",
    instructions=(
        "你是电商订单与售后专员。帮用户查订单、解释物流状态，"
        "处理退换货规则说明。需要订单详情时调用订单查询工具；"
        "用户明确要求退款时调用退款工具（会进入人工审批）。"
    ),
    tools=[get_order_status, process_refund],
    model=pro_model,
    model_settings=pro_settings,
    output_guardrails=SPECIALIST_OUTPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
)

customer_service_router = Agent(
    name="customer_service_router",
    instructions=(
        "你是电商客服前台，只负责分流，不直接查订单或商品。\n"
        "你当前只能使用 transfer_to_* 转接工具，禁止调用任何业务工具。\n"
        "规则：\n"
        "1. 商品/推荐/库存 → 必须 transfer_to_product_specialist\n"
        "2. 订单/物流/退换货/售后 → 必须 transfer_to_order_specialist\n"
        "3. 数据分析/报表/定价模拟 → 必须 transfer_to_analytics_specialist\n"
        "4. 即使对话历史里出现过查询，新消息仍必须先转接，不能代查\n"
        "5. 仅简单问候可自行回复"
    ),
    handoffs=[product_specialist, order_specialist, analytics_specialist],
    model_settings=flash_settings,
    input_guardrails=ROUTER_INPUT_GUARDRAILS if GUARDRAILS_ENABLED else [],
)

AGENT_REGISTRY: dict[str, Agent] = {
    "customer_service_router": customer_service_router,
    "product_specialist": product_specialist,
    "order_specialist": order_specialist,
    "analytics_specialist": analytics_specialist,
}


def get_agent_by_name(name: str) -> Agent:
    agent = AGENT_REGISTRY.get(name)
    if agent is None:
        raise ValueError(f"未知 Agent：{name!r}")
    return agent


def restore_pending_approval(session_id: str) -> PendingApprovalRecord | None:
    """从磁盘恢复待审批快照（Web 刷新/切换会话后调用）。"""
    return load_pending_approval(session_id)


def capture_pending_approval(session_id: str, run_result: Any) -> PendingApprovalRecord:
    """运行暂停时序列化 RunState 并落盘。"""
    record = build_pending_record(
        session_id,
        run_result,
        interruption_summaries=describe_interruptions(run_result),
    )
    save_pending_approval(record)
    return record


# ---------------------------------------------------------------------------
# Run lifecycle：流式 + 审批恢复 + 失败处理
# ---------------------------------------------------------------------------

def _extract_delta(event: Any) -> str | None:
    if event.type == "raw_response_event" and isinstance(
        event.data, ResponseTextDeltaEvent
    ):
        return event.data.delta
    return None


async def run_streamed_turn(
    agent: Agent,
    user_input: str,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
) -> tuple[str, Any]:
    """一次应用级 turn：流式消费完毕后，才视为 run 已结算。返回 (全文, stream_result)。"""
    stream = Runner.run_streamed(
        agent,
        user_input,
        session=session,
        run_config=run_config,
        max_turns=MAX_TURNS,
    )

    parts: list[str] = []
    async for event in stream.stream_events():
        delta = _extract_delta(event)
        if delta:
            parts.append(delta)
            if on_delta is not None:
                on_delta(delta)

    if stream.run_loop_exception:
        raise stream.run_loop_exception

    return "".join(parts), stream


async def resume_from_state(
    agent: Agent,
    state: Any,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
) -> tuple[str, Any]:
    """规则 2/3：从 RunState 恢复暂停或中断的同一轮，不传新 user message。"""
    stream = Runner.run_streamed(
        agent,
        state,
        session=session,
        run_config=run_config,
        max_turns=MAX_TURNS,
    )

    parts: list[str] = []
    async for event in stream.stream_events():
        delta = _extract_delta(event)
        if delta:
            parts.append(delta)
            if on_delta is not None:
                on_delta(delta)

    if stream.run_loop_exception:
        raise stream.run_loop_exception

    return "".join(parts), stream


def describe_interruptions(run_result: Any) -> list[str]:
    if isinstance(run_result, PendingApprovalRecord):
        return run_result.describe()
    return [describe_interruption_detail(i) for i in run_result.interruptions]


async def apply_approval_decision(
    pending: PendingApprovalRecord | Any,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    approved: bool,
    on_delta: Any | None = None,
) -> tuple[str, Any]:
    """审批后从 state 恢复，继续同一轮任务。"""
    from agents.run_state import RunState

    if isinstance(pending, PendingApprovalRecord):
        record = pending
        if record.live_result is not None:
            state = record.live_result.to_state()
            interruptions = list(record.live_result.interruptions)
        else:
            state = await RunState.from_json(
                customer_service_router,
                record.run_state_json,
            )
            interruptions = state.get_interruptions()
        resume_agent = get_agent_by_name(record.resume_agent_name)
    else:
        run_result = pending
        state = run_result.to_state()
        interruptions = list(run_result.interruptions)
        resume_agent = run_result.last_agent

    for interruption in interruptions:
        if approved:
            state.approve(interruption)
        else:
            state.reject(interruption)

    log_approval_decision(
        session_id=session.session_id,
        approved=approved,
        interruptions=interruptions,
    )

    text, result = await resume_from_state(
        resume_agent,
        state,
        session,
        run_config,
        on_delta=on_delta,
    )
    persist_sandbox_session(session.session_id, result)
    if result.interruptions:
        return text, capture_pending_approval(session.session_id, result)
    clear_pending_approval(session.session_id)
    publish_workspace_outputs()
    refresh_memory_summary(session.session_id)
    return text, result


async def resolve_interruptions(
    run_result: Any,
    session: SQLiteSession,
    run_config: RunConfig,
) -> Any:
    """终端版：审批 = 暂停的任务，从 state 继续而非新 user turn。"""
    current = run_result
    resume_agent = current.last_agent

    while current.interruptions:
        print("\n--- 待审批操作 ---")
        for idx, desc in enumerate(describe_interruptions(current), start=1):
            print(f"{idx}. {desc}")

        choice = input("批准全部？(y/n，默认 n): ").strip().lower()
        _, current = await apply_approval_decision(
            current,
            session,
            run_config,
            approved=(choice == "y"),
            on_delta=lambda d: print(d, end="", flush=True),
        )

    return current


async def handle_user_turn(
    agent: Agent,
    user_input: str,
    session: SQLiteSession,
    run_config: RunConfig,
    *,
    on_delta: Any | None = None,
    actor: str | None = None,
) -> tuple[str | None, Any | None]:
    """处理一轮用户输入。返回 (回复文本, run_result)；审批暂停时 result 带 interruptions。"""
    _ = actor
    servers = collect_mcp_servers_from_agents(*AGENT_REGISTRY.values())

    async def _execute_turn() -> tuple[str | None, Any | None]:
        try:
            with track_duration("agent_turn_total_ms"):
                async def _run_once() -> Any:
                    if run_config.sandbox is not None:
                        return await run_with_sandbox_slot(
                            lambda: run_streamed_turn(
                                agent,
                                user_input,
                                session,
                                run_config,
                                on_delta=on_delta,
                            ),
                            timeout_seconds=SANDBOX_RUN_TIMEOUT_SECONDS,
                        )
                    return await run_streamed_turn(
                        agent, user_input, session, run_config, on_delta=on_delta
                    )

                _, result = await run_with_retries(_run_once)

            if result.interruptions:
                pending = capture_pending_approval(session.session_id, result)
                persist_sandbox_session(session.session_id, result)
                record_event("agent_turn_interrupted")
                return None, pending

            published = publish_workspace_outputs()
            refresh_memory_summary(session.session_id)
            persist_sandbox_session(session.session_id, result)
            record_event(
                "agent_turn_completed",
                sandbox=run_config.sandbox is not None,
                published_files=len(published),
            )
            return result.final_output, result

        except InputGuardrailTripwireTriggered as exc:
            record_event("input_guardrail_triggered")
            message = format_input_guardrail_message(exc)
            return message, None
        except OutputGuardrailTripwireTriggered as exc:
            record_event("output_guardrail_triggered")
            message = format_output_guardrail_message(exc)
            return message, None
        except ToolInputGuardrailTripwireTriggered as exc:
            record_event("tool_input_guardrail_triggered")
            return f"**安全拦截**：工具调用未通过执行前审查（{exc.guardrail.get_name()}）。", None
        except MaxTurnsExceeded:
            record_event("agent_turn_max_turns_exceeded")
            print(
                f"\n[运行时失败] 超过最大轮次限制（max_turns={MAX_TURNS}）。"
                "请简化问题或提高 AGENT_MAX_TURNS。"
            )
        except Exception as exc:
            record_event("agent_turn_failed", error=type(exc).__name__)
            print(f"\n[运行时失败] {type(exc).__name__}: {exc}")

        return None, None

    with trace(
        "ecommerce_user_turn",
        metadata={"session_id": session.session_id, "actor": actor or "user"},
    ):
        outcome = await run_with_mcp_lifecycle(servers, _execute_turn)
    flush_traces()
    return outcome


async def chat_loop() -> None:
    session = SQLiteSession(SESSION_ID, db_path=SESSION_DB)
    run_config = build_run_config(session_id=session.session_id)

    print("电商客服 Agent 已启动（流式 + Session 半托管）")
    print(f"Session ID: {SESSION_ID}")
    print(f"数据文件: {_script_dir / 'data'}")
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
