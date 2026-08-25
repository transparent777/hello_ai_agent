import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

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

# DeepSeek 兼容 OpenAI SDK
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

DEFAULT_MODEL = "deepseek-chat"


def get_completion(prompt, model=DEFAULT_MODEL, temperature=0):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


def chain_of_thought_solve(
    question: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0,
) -> dict:
    """
    思维链（Chain-of-Thought）推理：先逐步思考，再给出最终答案。

    返回:
        reasoning: 模型的完整推理过程
        final_answer: 从回复中提取的最终答案
    """
    prompt = f"""
Solve the following problem using chain-of-thought reasoning.

Instructions:
1. Think step by step and show each reasoning step clearly.
2. After your reasoning, provide the final answer on the last line using:
   Final answer: <your answer>

Problem:
{question}
"""
    reasoning = get_completion(prompt, model=model, temperature=temperature)
    final_answer = extract_final_answer(reasoning)
    return {"reasoning": reasoning, "final_answer": final_answer}



def extract_final_answer(text: str) -> str:
    """从模型回复中提取 Final answer 行。"""
    match = re.search(
        r"final answer\s*[:：]\s*(.+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return text.strip().splitlines()[-1].strip()


if __name__ == "__main__":
    # 课程经典例题：不逐步推理时模型容易答错，思维链能推出正确答案 4
    question = (
        "A juggler can juggle 16 balls. "
        "Half of the balls are golf balls, "
        "and half of the golf balls are blue. "
        "How many blue golf balls does the juggler have?"
    )

    print("=" * 50)
    print("方式 1：结构化思维链（逐步推理 + Final answer）")
    print("=" * 50)
    result = chain_of_thought_solve(question)
    print(result["reasoning"])
    print()
    print(f"提取的最终答案: {result['final_answer']}")
