import asyncio# 导入 asyncio：Python 异步编程库，用于运行 async/await 协程
import os# 导入 os：读取环境变量、操作系统相关功能
import sys# 导入 sys：访问 Python 解释器信息（如平台、标准输出）
import requests


from pathlib import Path# 导入 Path：以对象方式处理文件路径
from dotenv import load_dotenv# 从 python-dotenv 导入 load_dotenv：从 .env 文件加载密钥到环境变量
from agents import Agent, Runner, RunConfig# 从 openai-agents 导入核心类
from agents.models.openai_provider import OpenAIProvider# 导入 OpenAIProvider：模型提供方
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

@function_tool
def get_history_fact(topic: str) -> str: #获取关于特定历史话题的冷知识。
    url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
    
    response = requests.get(url)
    data = response.json()
    
    fact = data.get("text", "")
    return fact

# 定义一个 Agent（智能体）
history_tutor = Agent(
    name="History tutor",  # Agent 名称，用于日志和调试
    instructions="You answer history questions clearly and concisely.",  # 系统指令：定义角色与回答风格
    tools=[get_history_fact],
    model="deepseek-chat", 
)

math_tutor = Agent(
    name="Math tutor",
    handoff_description="Specialist for math questions.",
    instructions="Explain math step by step and include worked examples.",
    model="deepseek-chat", 
)

triage_agent = Agent(
    name="Homework triage",
    instructions="Route each homework question to the right specialist.",
    handoffs=[history_tutor, math_tutor],
    model="deepseek-chat", 
)


# 定义异步主函数：openai-agents 的 Runner.run 是异步的，需在 async 函数里 await
async def main() -> None:
    # 运行 Agent，把用户问题发给它并等待结果
    result = await Runner.run(
        triage_agent,  # 要运行的 Agent
        "Who was the first president of the United States?",  # 用户输入（问题）
        run_config=RunConfig(
            model_provider=deepseek_provider,  
            tracing_disabled=True,  
        ),
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
