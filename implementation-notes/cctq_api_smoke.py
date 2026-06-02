import os

from openai import OpenAI


client = OpenAI(
    api_key=os.environ["CCTQ_API_KEY"],
    base_url=os.environ.get("CCTQ_BASE_URL", "https://www.cctq.ai/v1"),
)

response = client.chat.completions.create(
    model=os.environ.get("CCTQ_MODEL", "gpt-5.4"),
    messages=[{"role": "user", "content": "Return only: OK"}],
    max_tokens=20,
)

print("content:", response.choices[0].message.content)
print("usage:", response.usage)
