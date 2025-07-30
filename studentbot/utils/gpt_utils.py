import os
import logging
from datetime import datetime
import openai
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def ask_gpt(prompt: str, user_id: int, model: str = "gpt-3.5-turbo", max_tokens: int = 512) -> str | None:
    """Sends a prompt to GPT model and returns the response."""
    try:
        openai.api_key = config.OPENAI_API_KEY
        if not openai.api_key:
            logger.error("❌ OPENAI_API_KEY is not set.")
            return None

        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
            timeout=10
        )
        answer = response.choices[0].message.content.strip()
        
        await award_points_for_action(user_id, "search")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                prompt,
                answer[:1000],
                0,
                "GPT",
                "N/A",
                "N/A",
                "GPT Request",
                f"GPT response for {prompt}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        logger.info(f"✅ GPT response for user {user_id}: {prompt}")
        return answer
    except openai.error.OpenAIError as e:
        logger.error(f"❌ OpenAI error for user {user_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error in GPT request for user {user_id}: {str(e)}")
        return None