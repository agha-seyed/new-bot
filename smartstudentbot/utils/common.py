import re
import html
import magic
from typing import Optional, Tuple
from smartstudentbot.config import settings

def sanitize_markdown(text: str) -> str:
    """
    Sanitizes text to be safe for Telegram MarkdownV2.
    Escapes characters that have special meaning in MarkdownV2.
    """
    if not text:
        return ""

    # Telegram MarkdownV2 special chars
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)

def validate_file(file_content: bytes, max_size_mb: int = 10, allowed_mimes: list = None) -> Tuple[bool, str]:
    """
    Validates file size and real MIME type using python-magic.
    """
    if len(file_content) > max_size_mb * 1024 * 1024:
        return False, f"File too large. Max size is {max_size_mb}MB."

    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(file_content)

    if allowed_mimes and file_type not in allowed_mimes:
        return False, f"Invalid file type: {file_type}. Allowed: {allowed_mimes}"

    return True, "Valid"

def format_currency(amount: float, currency: str = "EUR", locale: str = "en_US") -> str:
    from babel.numbers import format_currency as babel_fmt
    return babel_fmt(amount, currency, locale=locale)
