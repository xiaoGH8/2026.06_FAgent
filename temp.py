"""Minimal OpenAI-compatible model connectivity smoke test.

Configure DIAGNOSIS_AGENT_API_KEY and DIAGNOSIS_AGENT_BASE_URL in .env first.
"""
from backend.config.settings import load_agent_config
from openai import OpenAI


config = load_agent_config()
if not config["llm_api_key"] or not config["llm_base_url"]:
    raise RuntimeError("DIAGNOSIS_AGENT_API_KEY/BASE_URL is not configured")

client = OpenAI(
    api_key=config["llm_api_key"],
    base_url=config["llm_base_url"],
)
completion = client.chat.completions.create(
    model=config["llm_model"],
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请回复：连接成功。"},
    ],
)
print(completion.choices[0].message.content)