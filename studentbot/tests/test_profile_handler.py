import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from studentbot.handlers.profile_handler import profile

@pytest.mark.asyncio
async def test_profile_handler():
    print("Starting test_profile_handler")
    update = MagicMock()
    update.message = AsyncMock()
    context = MagicMock()
    context.user_data = {"lang": "en"}

    with patch("studentbot.handlers.profile_handler.get_translated_text") as mock_get_translated_text:
        mock_get_translated_text.return_value = "This is where your profile will be displayed."
        print("Calling profile handler")
        await profile(update, context)
        print("Profile handler returned")

    update.message.reply_text.assert_called_once_with("This is where your profile will be displayed.")
    print("Test finished")
