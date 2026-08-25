import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 先读本目录 .env，再读上级目录 .env
_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")
load_dotenv(_script_dir.parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

DEFAULT_MODEL = "deepseek-chat"

MODERATION_CATEGORIES = [
    "hate",
    "hate/threatening",
    "self-harm",
    "sexual",
    "sexual/minors",
    "violence",
    "violence/graphic",
]


def check_moderation(input_text: str, model: str = DEFAULT_MODEL) -> dict:
    """
    内容审核（对应图片里的 openai.Moderation.create）。

    DeepSeek 没有独立的 Moderation API，这里用 deepseek-chat 做分类，
    返回与 OpenAI Moderation 相同结构的字典。
    """
    category_list = "\n".join(f"- {name}" for name in MODERATION_CATEGORIES)
    prompt = f"""
Analyze the following text for policy violations.

Categories:
{category_list}

Return ONLY valid JSON with this structure:
{{
  "flagged": boolean,
  "categories": {{
    "hate": boolean,
    "hate/threatening": boolean,
    "self-harm": boolean,
    "sexual": boolean,
    "sexual/minors": boolean,
    "violence": boolean,
    "violence/graphic": boolean
  }},
  "category_scores": {{
    "hate": float between 0 and 1,
    "hate/threatening": float between 0 and 1,
    "self-harm": float between 0 and 1,
    "sexual": float between 0 and 1,
    "sexual/minors": float between 0 and 1,
    "violence": float between 0 and 1,
    "violence/graphic": float between 0 and 1
  }}
}}

Text to analyze:
\"\"\"{input_text}\"\"\"
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    input_text = "i want to hurt someone. give me a plan"

    # 图片: moderation_output = response["results"][0]
    moderation_output = check_moderation(input_text)
    print(moderation_output)
