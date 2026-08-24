import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 与 prompt_test 一致：先读本目录 .env，再读上级目录 .env
_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")
load_dotenv(_script_dir.parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

# DeepSeek 兼容 OpenAI SDK
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

DEFAULT_MODEL = "deepseek-chat"


def get_completion(prompt, model=DEFAULT_MODEL):
  """单条用户 prompt，对应图片里的 get_completion。"""
  messages = [{"role": "user", "content": prompt}]
  response = client.chat.completions.create(
      model=model,
      messages=messages,
      temperature=0,  # this is the degree of randomness of the model's output
  )
  return response.choices[0].message.content


def get_completion_from_messages(messages, model=DEFAULT_MODEL, temperature=0):
  """多轮对话，对应图片里的 get_completion_from_messages。"""
  response = client.chat.completions.create(
      model=model,
      messages=messages,
      temperature=temperature,
  )
  return response.choices[0].message.content


def chat_loop(
    system_prompt: str = "You are a helpful assistant.",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
):
  """交互式聊天：维护 messages 历史，循环读取用户输入。"""
  messages = [{"role": "system", "content": system_prompt}]

  print("DeepSeek 聊天机器人已启动。输入 quit / exit / q 退出。")
  print("-" * 40)

  while True:
      user_input = input("你: ").strip()
      if not user_input:
          continue
      if user_input.lower() in {"quit", "exit", "q"}:
          print("再见！")
          break

      messages.append({"role": "user", "content": user_input})
      response = get_completion_from_messages(
          messages, model=model, temperature=temperature
      )
      messages.append({"role": "assistant", "content": response})
      print(f"AI: {response}\n")


if __name__ == "__main__":
  chat_loop()
