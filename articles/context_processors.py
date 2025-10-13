from django.utils import translation


def language_context(request):
    """Add language context to all templates using Django's i18n system."""

    # Get language from request (set by our middleware)
    current_language = getattr(request, "LANGUAGE_CODE", None)

    # Fallback to Django's translation system
    if not current_language:
        current_language = translation.get_language()

    return {
        "current_language": current_language,
        "available_languages": [
            ("it", "Italiano"),
            ("en", "English"),
        ],
        "LANGUAGE_CODE": current_language,  # For compatibility
    }
