import os
import openai
from studentbot.utils.logging_utils import logger

openai.api_key = os.getenv("OPENAI_API_KEY")

async def ask_gpt(prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 512) -> str | None:
    """Sends a prompt to GPT model and returns the response."""
    try:
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ GPT Error: {e}")
        return None
