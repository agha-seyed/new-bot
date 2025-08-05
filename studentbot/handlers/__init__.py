# studentbot/handlers/__init__.py
from .cmd_start import start
from .menu_handler import get_menu_handler
from .search_handler import get_search_handler
from .weather_handler import get_weather_handler
from .profile_handler import get_profile_handler
from .registration_flow import get_registration_handler
from .edit_profile_flow import get_edit_profile_handler
from .isee_handler import get_isee_handler
from .gamification_handler import points, leaderboard
from .news_handler import get_news_handler
from .consult_handler import get_consultation_handler
from .document_handler import get_document_handler
from .cost_handler import get_cost_handler
from .ai_handler import get_ai_handler
from .info_handler import get_info_handler
from .arrival_guide_handler import get_arrival_guide_handler
from .admin_handler import get_admin_handler
from .question_handler import get_question_handler
from .feedback_handler import get_feedback_handler
from .migration_handler import get_migration_handler
from .calendar_handler import get_calendar_handler

def get_all_handlers():
    """Return all handlers for the bot."""
    return (
        [start, points, leaderboard] +
        get_menu_handler() +
        get_search_handler() +
        get_weather_handler() +
        get_profile_handler() +
        get_registration_handler() +
        get_edit_profile_handler() +
        get_isee_handler() +
        get_news_handler() +
        get_consultation_handler() +
        get_document_handler() +
        get_cost_handler() +
        get_ai_handler() +
        get_info_handler() +
        get_arrival_guide_handler() +
        get_admin_handler() +
        get_question_handler() +
        get_feedback_handler() +
        get_migration_handler() +
        get_calendar_handler()
    )
