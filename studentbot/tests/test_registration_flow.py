import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from studentbot.handlers.registration_flow import (
    start_registration,
    first_name,
    last_name,
    age,
    email,
    country,
    field_of_study,
    FIRST_NAME,
    LAST_NAME,
    AGE,
    EMAIL,
    COUNTRY,
    FIELD_OF_STUDY,
)

@pytest.mark.asyncio
async def test_start_registration():
    update = MagicMock()
    update.message = AsyncMock()
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "Please enter your first name:"
        state = await start_registration(update, context)

    update.message.reply_text.assert_called_once_with("Please enter your first name:")
    assert state == FIRST_NAME

@pytest.mark.asyncio
async def test_first_name():
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "John"
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "Please enter your last name:"
        state = await first_name(update, context)

    assert context.user_data["first_name"] == "John"
    update.message.reply_text.assert_called_once_with("Please enter your last name:")
    assert state == LAST_NAME

@pytest.mark.asyncio
async def test_last_name():
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "Doe"
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "Please enter your age:"
        state = await last_name(update, context)

    assert context.user_data["last_name"] == "Doe"
    update.message.reply_text.assert_called_once_with("Please enter your age:")
    assert state == AGE

@pytest.mark.asyncio
async def test_age():
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "30"
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "Please enter your email address:"
        state = await age(update, context)

    assert context.user_data["age"] == "30"
    update.message.reply_text.assert_called_once_with("Please enter your email address:")
    assert state == EMAIL

@pytest.mark.asyncio
async def test_email():
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "test@example.com"
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "Please enter your country of residence:"
        state = await email(update, context)

    assert context.user_data["email"] == "test@example.com"
    update.message.reply_text.assert_called_once_with("Please enter your country of residence:")
    assert state == COUNTRY

@pytest.mark.asyncio
async def test_country():
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "USA"
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "Please enter your field of study:"
        state = await country(update, context)

    assert context.user_data["country"] == "USA"
    update.message.reply_text.assert_called_once_with("Please enter your field of study:")
    assert state == FIELD_OF_STUDY

@pytest.mark.asyncio
async def test_field_of_study():
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "Computer Science"
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.registration_flow.get_translated_text") as mock_get_translated_text, \
         patch("studentbot.handlers.registration_flow.create_user") as mock_create_user, \
         patch("studentbot.handlers.registration_flow.add_user_to_sheet") as mock_add_user_to_sheet:
        mock_get_translated_text.return_value = "Thank you for registering!"
        state = await field_of_study(update, context)

    assert context.user_data["field_of_study"] == "Computer Science"
    mock_create_user.assert_called_once()
    mock_add_user_to_sheet.assert_called_once()
    update.message.reply_text.assert_called_once_with("Thank you for registering!")
    assert state == -1 # ConversationHandler.END
