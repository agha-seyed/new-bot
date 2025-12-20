from aiogram import Router, types, F
from aiogram.filters import Command
from smartstudentbot.ai.question_answering import qa_engine
from smartstudentbot.utils.logger import logger

router = Router()

@router.message(F.text)
async def handle_text_question(message: types.Message):
    """
    Handles generic text messages as questions for the AI.
    """
    # Simple logic: if it's not a command, treat as a question
    user_query = message.text
    user_lang = message.from_user.language_code or "en"

    # Normalize lang
    if "fa" in user_lang: user_lang = "fa"
    elif "it" in user_lang: user_lang = "it"
    else: user_lang = "en"

    # Send typing action
    await message.bot.send_chat_action(message.chat.id, action="typing")

    try:
        answer = await qa_engine.get_answer(user_query, lang=user_lang)

        if answer:
            await message.reply(answer)
        else:
            # Fallback or silent?
            # For a bot, maybe better to say "I don't know yet" or just ignore if it looks like chat
            # Here we reply with a helpful fallback
            fallback_msg = {
                "en": "I'm not sure about that yet. Try asking differently or check /help.",
                "it": "Non sono sicuro. Prova a chiedere diversamente o controlla /help.",
                "fa": "هنوز در این مورد مطمئن نیستم. لطفاً سوال خود را تغییر دهید یا /help را بزنید."
            }
            await message.reply(fallback_msg.get(user_lang, fallback_msg["en"]))

    except Exception as e:
        logger.error(f"AI Error: {e}")
        await message.reply("⚠️ Sorry, I encountered an error processing your request.")
