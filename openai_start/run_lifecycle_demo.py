"""
运行生命周期示例：流式结束、审批暂停恢复、失败处理

对应规则：
1. 流式 run 必须等 stream 完全结束，再读取 final_output / interruptions
2. 审批暂停后，用 RunState 恢复，不要开启新的 user turn
3. 取消流式后若要继续同一轮次，也从 state 恢复
4. 主动区分：运行时失败 vs 预期内暂停（审批）
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent

from agents import Agent, RunConfig, Runner, SQLiteSession, function_tool
from agents.exceptions import MaxTurnsExceeded
from agents.models.openai_provider import OpenAIProvider

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")
load_dotenv(_script_dir.parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit("请在 .env 中配置 DEEPSEEK_API_KEY")

deepseek_provider = OpenAIProvider(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

RUN_CONFIG = RunConfig(
    model_provider=deepseek_provider,
    model="deepseek-chat",
    tracing_disabled=True,
)

DEFAULT_MODEL = "deepseek-chat"


@function_tool(needs_approval=True)
def delete_file(path: str) -> str:
    """Delete a file on the server (demo only)."""
    return f"Deleted {path}"


@function_tool
def ping() -> str:
    """Health check tool."""
    return "pong"


approval_agent = Agent(
    name="File assistant",
    instructions="When the user asks to delete a file, call delete_file.",
    tools=[delete_file],
    model=DEFAULT_MODEL,
)

loop_agent = Agent(
    name="Loop agent",
    instructions="Always call ping before answering.",
    tools=[ping],
    model=DEFAULT_MODEL,
)

chat_agent = Agent(
    name="Planet guide",
    instructions="Answer with short facts.",
    model=DEFAULT_MODEL,
)


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


async def demo_stream_must_finish_before_finalize() -> None:
    """规则 1：必须等 stream 结束，再视为 run 已结算。"""
    print_section("示例 1：流式输出 — 等 stream 完全结束")

    stream = Runner.run_streamed(
        chat_agent,
        "Give me two short facts about Saturn.",
        run_config=RUN_CONFIG,
    )

    print("流式输出: ", end="")
    async for event in stream.stream_events():
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)

    # ✅ 正确：stream_events() 消费完后，再检查异常和最终结果
    if stream.run_loop_exception:
        raise stream.run_loop_exception

    # ❌ 错误：在 async for 之前就 print(stream.final_output)，通常还是 None
    print(f"\n\n流结束后 final_output: {stream.final_output}")


async def demo_approval_resume_from_state_not_new_turn() -> None:
    """规则 2 & 6：审批 = 暂停的任务；恢复时传 RunState，不传新用户消息。"""
    print_section("示例 2：审批暂停 — 从 state 恢复（不是新一轮对话）")

    session = SQLiteSession("approval_demo_session")

    # 第一次 run：会在工具审批处暂停
    paused = await Runner.run(
        approval_agent,
        "Delete the file /tmp/demo.txt",
        session=session,
        run_config=RUN_CONFIG,
    )

    print(f"暂停时 final_output: {paused.final_output!r}")
    print(f"待审批数量: {len(paused.interruptions)}")

    if not paused.interruptions:
        print("模型未触发审批，跳过恢复示例。")
        return

    approval = paused.interruptions[0]
    print(f"待审批工具: {approval.tool_name}")

    # ✅ 正确：审批后从 state 恢复，继续同一轮任务
    state = paused.to_state()
    state.approve(approval)

    resumed = await Runner.run(
        approval_agent,
        state,  # 注意：这里不是新的用户输入字符串
        session=session,
        run_config=RUN_CONFIG,
    )

    print(f"恢复后 final_output: {resumed.final_output}")

    # ❌ 错误做法（不要这样）：
    # resumed = await Runner.run(approval_agent, "批准删除", session=session)
    # 这会被当成新的 user turn，轮次计数和 continuation 都会乱


async def demo_streamed_approval_resume() -> None:
    """规则 1 + 2：流式 run 也要等结束后，再从 interruptions 恢复。"""
    print_section("示例 3：流式 + 审批 — 先等 stream 结束，再恢复")

    stream = Runner.run_streamed(
        approval_agent,
        "Delete the file /tmp/stream-demo.txt",
        run_config=RUN_CONFIG,
    )

    async for _event in stream.stream_events():
        pass

    if stream.run_loop_exception:
        raise stream.run_loop_exception

    if not stream.interruptions:
        print("未触发审批。")
        return

    state = stream.to_state()
    state.approve(stream.interruptions[0])

    resumed = await Runner.run(approval_agent, state, run_config=RUN_CONFIG)
    print(f"恢复结果: {resumed.final_output}")


async def demo_runtime_failure_max_turns() -> None:
    """规则 4：运行时失败 — 例如超过 max_turns，需要显式捕获。"""
    print_section("示例 4：运行时失败 — max_turns 超限")

    try:
        await Runner.run(
            loop_agent,
            "Say hello.",
            max_turns=1,
            run_config=RUN_CONFIG,
        )
    except MaxTurnsExceeded:
        print("已捕获 MaxTurnsExceeded：这是运行时失败，不是审批暂停。")
        print("处理方式：提高 max_turns、简化任务，或检查是否陷入工具循环。")



async def main() -> None:
    await demo_stream_must_finish_before_finalize()
    await demo_approval_resume_from_state_not_new_turn()
    await demo_streamed_approval_resume()
    await demo_runtime_failure_max_turns()


if __name__ == "__main__":
    asyncio.run(main())
