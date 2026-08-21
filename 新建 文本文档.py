import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 从本文件所在目录读取 .env
load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit(
        "未检测到 DEEPSEEK_API_KEY。请在同目录的 .env 里填入：\n"
        "DEEPSEEK_API_KEY=你的DeepSeek密钥"
    )

# DeepSeek 兼容 OpenAI SDK，只需改 base_url 和模型名
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)


def get_completion(prompt, model="deepseek-chat"):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,  # this is the degree of randomness of the model's output
    )
    return response.choices[0].message.content


text = f"""
You should express what you want a model to do by \
providing instructions that are as clear and \
specific as you can possibly make them. \
This will guide the model towards the desired output, \
and reduce the chances of receiving irrelevant \
or incorrect responses. Don't confuse writing a \
clear prompt with writing a short prompt. \
In many cases, longer prompts provide more clarity \
and context for the model, which can lead to \
more detailed and relevant outputs.
"""
# prompt = f"""
# Summarize the text delimited by triple backticks \
# into a single sentence.
# ```{text}```
# """
# response = get_completion(prompt)
# print(response)

# prompt = f"""
# 输出三本书的名称，和它的作者，以及类型\
# 用JSON格式，四个关键词，书籍号，书名，作者，类型。
# ```{text}```
# """

# response = get_completion(prompt)
# print(response)

text = f"""
In a charming village, siblings Jack and Jill set out on
a quest to fetch water from a hilltop \
well. As they climbed, singing joyfully, misfortune
struck-Jack tripped on a stone and tumbled \
down the hill, with Jill following suit. \
Though slightly battered, the pair returned home to \
comforting embraces. Despite the mishap,
their adventurous spirits remained undimmed, and they
continued exploring with delight.
"""
#example 1
prompt_1 = f"""
Perform the following actions:
1 - Summarize the following text delimited by triple \
backticks with 1 sentence.
2 - Translate the summary into French.
3 - List each name in the French summary.
Output a json object that contains the following
keys: french_summary, num_names.
Separate your answers with line breaks.
Text:
'''{text}'''
"""

response = get_completion(prompt_1)
print("Completion for prompt 1:")
print(response)
