import asyncio# 导入 asyncio：Python 异步编程库，用于运行 async/await 协程
import os# 导入 os：读取环境变量、操作系统相关功能
import sys# 导入 sys：访问 Python 解释器信息（如平台、标准输出）
from pydantic import BaseModel
from dataclasses import dataclass


from pathlib import Path# 导入 Path：以对象方式处理文件路径
from dotenv import load_dotenv# 从 python-dotenv 导入 load_dotenv：从 .env 文件加载密钥到环境变量
from agents import Agent, Runner, RunConfig, RunContextWrapper,  SQLiteSession# 从 openai-agents 导入核心类
from agents.models.openai_provider import OpenAIProvider# 导入 OpenAIProvider：模型提供方
from openai.types.responses import ResponseTextDeltaEvent
from agents import function_tool

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")# 若在 Windows 上运行，把终端输出编码设为 UTF-8，避免中文乱码


_script_dir = Path(__file__).resolve().parent# 获取当前脚本所在目录的绝对路径
load_dotenv(_script_dir / ".env")# 尝试加载 /.env
load_dotenv(_script_dir.parent / ".env")# 尝试加载你实际放密钥的位置

# 从环境变量读取 DeepSeek API Key
api_key = os.getenv("DEEPSEEK_API_KEY")
# 若未读到密钥，打印提示并退出，避免后续调用 API 时报错
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

# 创建 DeepSeek 模型提供方
# DeepSeek 接口兼容 OpenAI，只需改 base_url，无需换 SDK
deepseek_provider = OpenAIProvider(
    api_key=api_key,  
    base_url="https://api.deepseek.com",  
)

##session
'''
agent = Agent(
    name="Tour guide",
    instructions="Answer with compact travel facts.",
    model="deepseek-chat", 
)


session = SQLiteSession("conversation_123")


async def main() -> None:
    first_turn = await Runner.run(
        agent,
        "What city is the Golden Gate Bridge in?",
        session=session,
        run_config=RunConfig(
            model_provider=deepseek_provider,  
            tracing_disabled=True
        ),
    )
    print(first_turn.final_output)

    second_turn = await Runner.run(
        agent,
        "What state is it in?",
        session=session,
        run_config=RunConfig(
            model_provider=deepseek_provider,  
            tracing_disabled=True
            ),  
    )
    print(second_turn.final_output)

'''

#Stream runs incrementally
agent = Agent(
    name="Planet guide",
    instructions="Answer with short facts.",
    model="deepseek-chat", 
)


async def main() -> None:
    stream = Runner.run_streamed(
        agent,
        "Give me three short facts about Saturn.",
        run_config=RunConfig(
            model_provider=deepseek_provider,  
            tracing_disabled=True
            ),  
    )

    async for event in stream.stream_events():
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)

    # 规则：必须等 stream 完全结束，再读取 final_output
    if stream.run_loop_exception:
        raise stream.run_loop_exception

    print(f"\nFinal: {stream.final_output}")




if __name__ == "__main__":
    asyncio.run(main())