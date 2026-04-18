import httpx
from config import CLAUDE_API_KEY, CLAUDE_MODEL

CLAUDE_URL = "https://api.anthropic.com/v1/messages"
HEADERS = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}


async def call_claude(system_prompt: str, user_content: str) -> str:
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(CLAUDE_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
