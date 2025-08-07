import pytest
from studentbot.utils.common import sanitize_markdown, get_translated_text

def test_sanitize_markdown():
    assert sanitize_markdown("*bold* _italic_") == "\\*bold\\* \\_italic\\_"
    assert sanitize_markdown("[link](http://example.com)") == "\\[link\\]\\(http://example\\.com\\)"
    assert sanitize_markdown("`code`") == "\\`code\\`"
    assert sanitize_markdown("~strikethrough~") == "\\~strikethrough\\~"
    assert sanitize_markdown("> blockquote") == "\\> blockquote"
    assert sanitize_markdown("# header") == "\\# header"
    assert sanitize_markdown("+ list") == "\\+ list"
    assert sanitize_markdown("- list") == "\\- list"
    assert sanitize_markdown("= heading") == "\\= heading"
    assert sanitize_markdown("| table") == "\\| table"
    assert sanitize_markdown("{curly}") == "\\{curly\\}"
    assert sanitize_markdown(".dot") == "\\.dot"
    assert sanitize_markdown("!bang") == "\\!bang"
    assert sanitize_markdown("no special chars") == "no special chars"
    assert sanitize_markdown("") == ""
    assert sanitize_markdown(None) == ""

@pytest.mark.asyncio
async def test_get_translated_text(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data='{"test_key": "Test Value"}'))
    mocker.patch("pathlib.Path.exists", return_value=True)
    assert get_translated_text("test_key", "en") == "Test Value"

@pytest.mark.asyncio
async def test_get_translated_text_fallback(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data='{"test_key": "Test Value"}'))
    mocker.patch("pathlib.Path.exists", return_value=False)
    assert get_translated_text("test_key", "fr") == "Test Value"
