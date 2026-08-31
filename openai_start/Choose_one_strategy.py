import asyncio# 导入 asyncio：Python 异步编程库，用于运行 async/await 协程
import os# 导入 os：读取环境变量、操作系统相关功能
import sys# 导入 sys：访问 Python 解释器信息（如平台、标准输出）
from pydantic import BaseModel
from dataclasses import dataclass


from pathlib import Path# 导入 Path：以对象方式处理文件路径
from dotenv import load_dotenv# 从 python-dotenv 导入 load_dotenv：从 .env 文件加载密钥到环境变量
from agents import Agent, Runner, RunConfig, RunContextWrapper# 从 openai-agents 导入核心类
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