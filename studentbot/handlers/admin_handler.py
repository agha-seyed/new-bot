import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from studentbot.utils.db_utils import (
    get_all_consultation_requests,
    update_consultation_request_status,
    get_all_users,
)
from studentbot.utils.text_formatter import get_translated_text

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# چک کردن مجوز ادمین
def is_admin(user_id):
    return int(user_id) == ADMIN_CHAT_ID

# 📋 نمایش درخواست‌های مشاوره
async def admin_consultations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ شما مجاز به استفاده از این دستور نیستید.")
        return

    requests = await get_all_consultation_requests()
    if not requests:
        await update.message.reply_text("هیچ درخواستی یافت نشد.")
        return

    for req in requests:
        keyboard = [
            [f"📥 پاسخ به {req[2]}", f"🗂 بایگانی {req[0]}", f"📁 فایل {req[0]}"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        request_text = f"""
📌 *درخواست شماره:* {req[0]}
👤 *کاربر:* {req[2]}
🎓 *رشته:* {req[3]}
📊 *معدل:* {req[5]}
🌍 *کشور مقصد:* {req[6]}
🗂 *وضعیت:* {req[11]}
        """
        await update.message.reply_text(request_text.strip(), parse_mode="Markdown", reply_markup=reply_markup)

# ✅ بایگانی درخواست مشاوره
async def archive_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ مجوز ندارید.")
        return
    try:
        request_id = int(update.message.text.split(" ")[-1])
        await update_consultation_request_status(request_id, "archived")
        await update.message.reply_text(f"✅ درخواست شماره {request_id} بایگانی شد.", reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("❌ خطا در شناسایی درخواست.")

# 💬 پاسخ به درخواست (در نسخه بعدی قابل پیاده‌سازی)
async def reply_to_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🛠 قابلیت پاسخ‌گویی به‌زودی فعال می‌شود.")

# 📎 نمایش فایل ضمیمه (در نسخه بعدی)
async def view_consultation_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📎 قابلیت مشاهده فایل در نسخه بعدی فعال می‌شود.")

# 📢 ارسال پیام به کاربران هدف
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ شما مجاز به استفاده از این دستور نیستید.")
        return
    await update.message.reply_text("لطفاً پیام ارسالی را وارد کنید:")
    context.user_data["awaiting_broadcast"] = True

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_broadcast"):
        context.user_data["broadcast_text"] = update.message.text
        await update.message.reply_text("📍 لطفاً رشته مورد نظر را وارد کنید (مثلاً: پزشکی یا 'همه'):")
        context.user_data["awaiting_field_filter"] = True
        context.user_data.pop("awaiting_broadcast")

    elif context.user_data.get("awaiting_field_filter"):
        field = update.message.text
        users = await get_all_users()
        filtered = users if field.lower() == "همه" else [u for u in users if u["field_of_study"].lower() == field.lower()]

        count = 0
        for u in filtered:
            try:
                await update.get_bot().send_message(
                    chat_id=u["id"],
                    text=context.user_data["broadcast_text"]
                )
                count += 1
            except:
                continue
        await update.message.reply_text(f"✅ پیام به {count} نفر ارسال شد.")
        context.user_data.pop("awaiting_field_filter")
        context.user_data.pop("broadcast_text", None)

# ⚙️ هندلرها
def get_admin_handler():
    return [
        CommandHandler("admin_consultations", admin_consultations),
        CommandHandler("broadcast", broadcast),
        MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_CHAT_ID), handle_broadcast_message),
        MessageHandler(filters.Regex("^🗂 بایگانی"), archive_consultation),
        MessageHandler(filters.Regex("^📥 پاسخ"), reply_to_consultation),
        MessageHandler(filters.Regex("^📁 فایل"), view_consultation_file),
    ]
