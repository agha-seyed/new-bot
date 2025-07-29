import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..utils.db_utils import get_user

@pytest.mark.asyncio
async def test_get_user():
    user_id = 123
    with patch("studentbot.utils.db_utils.AsyncSessionLocal") as mock_session:
        mock_session.return_value.__aenter__.return_value.execute.return_value.one_or_none.return_value = (user_id, "John", "Doe", 30, "test@test.com", "USA", "CS")
        user = await get_user(user_id)
        assert user[0] == user_id
