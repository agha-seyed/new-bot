from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from smartstudentbot.utils.common import sanitize_markdown

router = Router()

class ISEEState(StatesGroup):
    waiting_for_income = State()
    waiting_for_assets = State()
    waiting_for_members = State()
    waiting_for_rent = State()

@router.message(Command("isee"))
async def start_isee(message: types.Message, state: FSMContext):
    await message.answer(
        "🧮 **ISEE Calculator**\n\n"
        "This tool helps you estimate your ISEE Parificato value.\n"
        "Please enter your **Family's Total Annual Income** (in EUR):"
    )
    await state.set_state(ISEEState.waiting_for_income)

@router.message(ISEEState.waiting_for_income)
async def process_income(message: types.Message, state: FSMContext):
    try:
        income = float(message.text.replace(',', '.'))
        if income < 0: raise ValueError
        await state.update_data(income=income)
        await message.answer("✅ Saved. Now enter **Total Family Assets** (Bank savings + Property value * 0.2):")
        await state.set_state(ISEEState.waiting_for_assets)
    except ValueError:
        await message.answer("❌ Invalid number. Please enter a positive number (e.g., 15000.50).")

@router.message(ISEEState.waiting_for_assets)
async def process_assets(message: types.Message, state: FSMContext):
    try:
        assets = float(message.text.replace(',', '.'))
        if assets < 0: raise ValueError
        await state.update_data(assets=assets)
        await message.answer("✅ Saved. How many **Family Members** are in your household?")
        await state.set_state(ISEEState.waiting_for_members)
    except ValueError:
        await message.answer("❌ Invalid number.")

@router.message(ISEEState.waiting_for_members)
async def process_members(message: types.Message, state: FSMContext):
    try:
        members = int(message.text)
        if members < 1: raise ValueError
        await state.update_data(members=members)

        # Determine Equivalence Scale (Standard Italian Formula)
        # 1 -> 1.0, 2 -> 1.57, 3 -> 2.04, 4 -> 2.46, 5 -> 2.85
        scale_map = {1: 1.0, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85}
        # Simplified formula for members > 5: +0.35 per extra person
        scale = scale_map.get(members, 2.85 + (members - 5) * 0.35)

        await state.update_data(scale=scale)

        # Trigger Calculation
        data = await state.get_data()

        # ISEE Formula: (ISR + 20% of ISP) / Equivalence Scale
        # ISR = Income
        # ISP = Assets
        ise = data['income'] + (0.20 * data['assets'])
        isee_value = ise / scale

        scholarship_limit = 24335.11 # 2023/2024 value

        result_text = (
            f"📊 **ISEE Calculation Result**\n\n"
            f"💰 **Income (ISR):** €{data['income']:,.2f}\n"
            f"🏠 **Assets (ISP):** €{data['assets']:,.2f}\n"
            f"👨‍👩‍👧 **Scale ({data['members']}):** {scale}\n\n"
            f"🏁 **Estimated ISEE:** `€{isee_value:,.2f}`\n\n"
        )

        if isee_value <= scholarship_limit:
            result_text += "✅ **You are likely ELIGIBLE for the scholarship!**"
        else:
            result_text += f"⚠️ **You are above the limit (€{scholarship_limit:,.2f}).**"

        await message.answer(sanitize_markdown(result_text), parse_mode="MarkdownV2")
        await state.clear()

    except ValueError:
        await message.answer("❌ Invalid integer.")
