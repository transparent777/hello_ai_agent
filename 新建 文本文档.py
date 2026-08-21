import os

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI


_ = load_dotenv(find_dotenv())  # Read the local .env file.


def get_completion(prompt: str, model: str = "gpt-5.6-sol") -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to a local .env file or "
            "set it as an environment variable."
        )

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        input=prompt,
        reasoning={"effort": "none"},
    )
    return response.output_text


text = """
You should express what you want a model to do by
providing instructions that are as clear and
specific as you can possibly make them.
This will guide the model towards the desired output,
and reduce the chances of receiving irrelevant
or incorrect responses. Don't confuse writing a
clear prompt with writing a short prompt.
In many cases, longer prompts provide more clarity
and context for the model, which can lead to
more detailed and relevant outputs.
"""

prompt = f"""
Summarize the text delimited by triple backticks
into a single sentence.
```{text}```
"""

response = get_completion(prompt)
print(response)
