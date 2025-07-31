import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
from sqlalchemy import select, update
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.models_db import MigrationStatus
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

MIGRATION_STEPS = {
    "en": [
        "Start application",
        "Submit documents",
        "Visa application",
        "Receive visa",
        "Book travel",
        "Arrive in Italy",
        "Register at university",
        "Apply for residence permit",
        "Open bank account",
        "Complete orientation"
    ],
    "fa": [
        "شروع درخواست",
        "ارسال مدارک",
        "درخواست ویزا",
        "دریافت ویزا",
        "رزرو سفر",
        "ورود به ایتالیا",
        "ثبت‌نام در دانشگاه",
        "درخواست اجازه اقامت",
        "باز کردن حساب بانکی",
        "تکمیل دوره آشنایی"
    ],
    "it": [
        "Inizia la domanda",
        "Invia documenti",
        "Richiesta di visto",
        "Ricevi il visto",
        "Prenota il viaggio",
        "Arrivo in Italia",
        "Registrazione all'università",
        "Richiesta di permesso di soggiorno",
        "Apri un conto bancario",
        "Completa l'orientamento"
    ]
}

async def get_user_migration_status(session, user_id: int) -> int:
    """Get the user's migration status from the database."""
    result = await session.execute(select(MigrationStatus).where(MigrationStatus.user_id == user_id))
    migration = result.scalars().first()
    return migration.status if migration else 0

async def update_user_migration_status(session, user_id: int, status: int) -> None:
    """Update the user's migration status in the database."""
    result = await session.execute(select(MigrationStatus).where(MigrationStatus.user_id == user_id))
    migration = result.scalars().first()
    if migration:
        await session.execute(
            update(MigrationStatus).where(MigrationStatus.user_id == user_id).values(status=status)
        )
    else:
        session.add(MigrationStatus(user_id=user_id, status=status))
    await session.commit()

async def migration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's migration status with progress bar and steps."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        async with AsyncSessionLocal() as session:
            status = await get_user_migration_status(session, user_id)
        
        progress_bar = "".join(["✅" if i < status else "⬜" for i in range(10)])
        steps_text = "\n".join(
            [f"{'✅' if i < status else '⬜'} {i+1}. {MIGRATION_STEPS[lang][i]}" for i in range(10)]
        )
        message = f"""
📊 *{sanitize_markdown(get_translated_text('migration_status', lang))}* ({status}/10)
{progress_bar}
📋 *{sanitize_markdown(get_translated_text('migration_steps', lang))}*:
{steps_text}
        """
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
                "Migration Status",
                f"Status: {status}/10",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(message, parse_mode="MarkdownV2")
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "migration_status_checked", f"Status: {status}/10")
        logger.info(f"✅ User {user_id} checked migration status: {status}/10")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Error fetching migration status for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def update_migration_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the user's migration status."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if not context.args:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("migration_status_no_arg", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ No argument provided by user {user_id} for migration status update")
        return

    try:
        new_status = int(context.args[0])
        if not 0 <= new_status <= 10:
            raise ValueError("Out of range")
        
        async with AsyncSessionLocal() as session:
            await update_user_migration_status(session, user_id, new_status)
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
                    "Migration Status Update",
                    f"New status: {new_status}/10",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        message = f"""
✅ *{sanitize_markdown(get_translated_text('migration_status_updated', lang))}*
📊 *{sanitize_markdown(get_translated_text('current_step', lang))}*: {sanitize_markdown(MIGRATION_STEPS[lang][min(new_status, 9)])}
        """
        await update.message.reply_text(message, parse_mode="MarkdownV2")
        await award_points_for_action(user_id, "migration_update")
        await log_event(user_id, "migration_status_updated", f"New status: {new_status}/10")
        logger.info(f"✅ User {user_id} updated migration status to {new_status}")
        
        admin_chat_id = config.ADMIN_CHAT_ID
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=sanitize_markdown(
                    get_translated_text("admin_migration_updated", lang).format(
                        user_id=user_id,
                        status=new_status
                    )
                ),
                parse_mode="MarkdownV2"
            )
    
    except ValueError:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("migration_status_invalid_arg", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid migration status update by user {user_id}: {context.args[0]}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Error updating migration status for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_migration_handler():
    """Return the migration handler."""
    return [
        CommandHandler("migration_status", migration_status),
        CommandHandler("update_migration_status", update_migration_status),
    ]
