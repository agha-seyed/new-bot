from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # Language Selection
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇸 English", callback_data="lang_en")
    builder.button(text="🇮🇷 فارسی", callback_data="lang_fa")
    builder.button(text="🇮🇹 Italiano", callback_data="lang_it")
    builder.adjust(1)

    await message.answer(
        "👋 Welcome to **SmartStudentBot Perugia**!\n\n"
        "Please select your language:\n"
        "لطفاً زبان خود را انتخاب کنید:\n"
        "Seleziona la tua lingua:",
        reply_markup=builder.as_markup()
    )
