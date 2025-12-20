from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from smartstudentbot.utils.common import validate_file, sanitize_markdown
from smartstudentbot.config import settings
from smartstudentbot.utils.logger import logger
from smartstudentbot.models_db import News
from aiogram import Bot
# In a real scenario, we'd inject the DB session. For now, mocking saving.

router = Router()

class NewsState(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_media = State()
    confirmation = State()

# --- Google Drive Stub ---
async def upload_to_drive(file_obj, filename: str) -> str:
    """
    Stub for Google Drive Upload.
    In production, use google-api-python-client with Service Account.
    Returns: Web View Link of the uploaded file.
    """
    if not settings.GOOGLE_CREDENTIALS_JSON:
        logger.warning("Google Drive credentials not configured. Skipping upload.")
        return "http://mock-drive-link.com/file"

    try:
        # Example Implementation Logic:
        # creds = service_account.Credentials.from_service_account_info(json.loads(settings.GOOGLE_CREDENTIALS_JSON))
        # service = build('drive', 'v3', credentials=creds)
        # file_metadata = {'name': filename, 'parents': ['FOLDER_ID']}
        # media = MediaIoBaseUpload(file_obj, mimetype='image/jpeg', resumable=True)
        # file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        # return file.get('webViewLink')
        logger.info(f"Uploading {filename} to Google Drive...")
        return "https://drive.google.com/file/d/MOCK_FILE_ID/view"
    except Exception as e:
        logger.error(f"Drive Upload Failed: {e}")
        return ""

@router.message(Command("post_news"))
async def start_news_post(message: types.Message, state: FSMContext):
    # RBAC Check (Mocked for example, normally check DB/Config)
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ Access Denied.")
        return

    await message.answer("📢 **Admin News Posting**\n\nPlease enter the **Title** of the news:", parse_mode="MarkdownV2")
    await state.set_state(NewsState.waiting_for_title)

@router.message(NewsState.waiting_for_title)
async def news_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Good. Now enter the **Content/Body** of the news:")
    await state.set_state(NewsState.waiting_for_content)

@router.message(NewsState.waiting_for_content)
async def news_content(message: types.Message, state: FSMContext):
    await state.update_data(content=message.text)

    kb = [
        [types.KeyboardButton(text="Skip Media")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

    await message.answer("Attach an image/file (optional) or click **Skip Media**:", reply_markup=keyboard, parse_mode="MarkdownV2")
    await state.set_state(NewsState.waiting_for_media)

@router.message(NewsState.waiting_for_media, F.content_type.in_({'photo', 'document', 'video'}))
async def news_media(message: types.Message, state: FSMContext):
    file_id = None
    media_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"

        # Validate size (Telegram bot API limit is 20MB for bots, but we restricted to 10MB in requirements)
        # Note: We can't check size easily without downloading info, relying on Telegram's limit for now or check file_size attr
        if message.document.file_size > 10 * 1024 * 1024:
             await message.answer("File too large. Max 10MB.")
             return

    await state.update_data(media_file_id=file_id, media_type=media_type)
    await show_preview(message, state)

@router.message(NewsState.waiting_for_media, F.text == "Skip Media")
async def skip_media(message: types.Message, state: FSMContext):
    await state.update_data(media_file_id=None, media_type=None)
    await show_preview(message, state)

async def show_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()

    preview_text = (
        f"👀 **Preview**\n\n"
        f"**{sanitize_markdown(data['title'])}**\n\n"
        f"{sanitize_markdown(data['content'])}"
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Publish", callback_data="news_publish")],
        [types.InlineKeyboardButton(text="❌ Cancel", callback_data="news_cancel")]
    ])

    if data.get('media_file_id'):
        if data['media_type'] == 'photo':
            await message.answer_photo(data['media_file_id'], caption=preview_text, reply_markup=kb, parse_mode="MarkdownV2")
        else:
            await message.answer_document(data['media_file_id'], caption=preview_text, reply_markup=kb, parse_mode="MarkdownV2")
    else:
        await message.answer(preview_text, reply_markup=kb, parse_mode="MarkdownV2")

    await state.set_state(NewsState.confirmation)

@router.callback_query(NewsState.confirmation, F.data == "news_publish")
async def publish_news(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    # 1. Archive to Drive (Async/Background recommended)
    drive_link = None
    if data.get('media_file_id'):
        # In a real app, we would download the file from Telegram first:
        # file_obj = await bot.download(data['media_file_id'])
        # drive_link = await upload_to_drive(file_obj, f"news_{data['title'][:10]}.jpg")
        pass # Placeholder for download logic

    # 2. Save to Database (Mock logic)
    # db.add(NewsItem(title=data['title'], content=data['content'], media_url=drive_link...))
    logger.info(f"News saved to DB: {data['title']}")

    # 3. Broadcast to Channels (Mocking Channel ID for example)
    # In production, these IDs come from config or DB
    channel_ids = ["@perugia_students_channel"]

    success_count = 0
    for chat_id in channel_ids:
        try:
            caption = f"📢 **{sanitize_markdown(data['title'])}**\n\n{sanitize_markdown(data['content'])}"
            if data.get('media_file_id'):
                if data['media_type'] == 'photo':
                    await bot.send_photo(chat_id, photo=data['media_file_id'], caption=caption, parse_mode="MarkdownV2")
                else:
                    await bot.send_document(chat_id, document=data['media_file_id'], caption=caption, parse_mode="MarkdownV2")
            else:
                await bot.send_message(chat_id, text=caption, parse_mode="MarkdownV2")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {chat_id}: {e}")

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ News published successfully to {success_count} channels!")
    await state.clear()

@router.callback_query(NewsState.confirmation, F.data == "news_cancel")
async def cancel_news(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ News posting cancelled.")
    await state.clear()
