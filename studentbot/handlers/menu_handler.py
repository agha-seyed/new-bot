import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import get_user, AsyncSessionLocal, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the main menu with a modern, horizontal layout."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [
                InlineKeyboardButton(f"📝 {get_translated_text('register_menu', lang)}", callback_data="register"),
                InlineKeyboardButton(f"👤 {get_translated_text('profile_menu', lang)}", callback_data="profile"),
                InlineKeyboardButton(f"❓ {get_translated_text('question_menu', lang)}", callback_data="question"),
            ],
            [
                InlineKeyboardButton(f"🔍 {get_translated_text('search_menu', lang)}", callback_data="search"),
                InlineKeyboardButton(f"📰 {get_translated_text('news_menu', lang)}", callback_data="news"),
                InlineKeyboardButton(f"☁️ {get_translated_text('weather_menu', lang)}", callback_data="weather"),
            ],
            [
                InlineKeyboardButton(f"💰 {get_translated_text('cost_of_living_menu', lang)}", callback_data="cost"),
                InlineKeyboardButton(f"📤 {get_translated_text('upload_document_menu', lang)}", callback_data="upload"),
                InlineKeyboardButton(f"🎮 {get_translated_text('gamification_menu', lang)}", callback_data="gamification"),
            ],
            [
                InlineKeyboardButton(f"📢 {get_translated_text('feedback_menu', lang)}", callback_data="feedback"),
                InlineKeyboardButton(f"🎓 {get_translated_text('scholarships_menu', lang)}", callback_data="scholarships"),
                InlineKeyboardButton(f"🌍 {get_translated_text('migration_menu', lang)}", callback_data="migration"),
            ],
            [
                InlineKeyboardButton(f"🏠 {get_translated_text('housing_menu', lang)}", callback_data="housing"),
                InlineKeyboardButton(f"📄 {get_translated_text('documents_menu', lang)}", callback_data="documents"),
                InlineKeyboardButton(f"🗣️ {get_translated_text('consulting_menu', lang)}", callback_data="consulting"),
            ],
            [
                InlineKeyboardButton(f"📊 {get_translated_text('isee_menu', lang)}", callback_data="isee"),
                InlineKeyboardButton(f"⏰ {get_translated_text('deadlines_menu', lang)}", callback_data="deadlines"),
                InlineKeyboardButton(f"🗣️ {get_translated_text('language_courses_menu', lang)}", callback_data="language_courses"),
            ],
            [
                InlineKeyboardButton(f"🌐 {get_translated_text('language_menu', lang)}", callback_data="language"),
                InlineKeyboardButton(f"📋 {get_translated_text('migration_status_menu', lang)}", callback_data="migration_status"),
                InlineKeyboardButton(f"❔ {get_translated_text('help_menu', lang)}", callback_data="help"),
            ],
            [
                InlineKeyboardButton(f"📞 {get_translated_text('contact_menu', lang)}", callback_data="contact"),
                InlineKeyboardButton(f"ℹ️ {get_translated_text('about_menu', lang)}", callback_data="about"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            f"🎉 *{sanitize_markdown(get_translated_text('welcome_message', lang))}*\n\n"
            f"{sanitize_markdown(get_translated_text('main_menu', lang))}"
        )
        await update.message.reply_text(
            welcome_message,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                    user_id,
                    user.first_name,
                    user.last_name or "N/A",
                    user.age or 0,
                    user.email or "N/A",
                    user.field_of_study or "N/A",
                    user.country or "N/A",
                    "Menu Display",
                    "Displayed main menu",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "menu_displayed", "Displayed main menu")
        logger.info(f"✅ Main menu displayed for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying menu for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu callback actions."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        command_map = {
            "register": "/register",
            "profile": "/profile",
            "question": "/question",
            "search": "/search",
            "news": "/news",
            "weather": "/weather",
            "cost": "/cost",
            "upload": "/upload",
            "gamification": "/points",
            "feedback": "/feedback",
            "language": "/language",
            "migration_status": "/migration_status",
            "help": "/help",
            "contact": "/contact",
            "about": "/about",
            "scholarships": "/search scholarships",
            "migration": "/search migration",
            "housing": "/search housing",
            "documents": "/search documents",
            "consulting": "/consult",
            "isee": "/isee",
            "deadlines": "/search deadlines",
            "language_courses": "/search language courses"
        }
        
        command = command_map.get(query.data, None)
        if command:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("menu_selected", lang).format(command=command)),
                parse_mode="MarkdownV2"
            )
            async with AsyncSessionLocal() as session:
                user = await get_user(session, user_id)
                if user:
                    interaction_data = [
                        user_id,
                        user.first_name,
                        user.last_name or "N/A",
                        user.age or 0,
                        user.email or "N/A",
                        user.field_of_study or "N/A",
                        user.country or "N/A",
                        "Menu Selection",
                        f"Selected {query.data}",
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
            await award_points_for_action(user_id, "interaction")
            await log_event(user_id, "menu_selected", f"Selected menu option: {query.data}")
            logger.info(f"✅ User {user_id} selected menu option: {query.data}")
        else:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_selection", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid menu selection by user {user_id}: {query.data}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling menu callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_menu_handler():
    """Return the menu handler."""
    return [
        CommandHandler("menu", menu),
        CommandHandler("start", menu),
        CallbackQueryHandler(menu_callback)
    ]
