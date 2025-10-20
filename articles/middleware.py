from django.utils import translation


class LanguageMiddleware:
    """Custom middleware to activate language from session or cookie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Try to get language from session first
        language_session = request.session.get("_language")
        language_cookie = request.COOKIES.get("django_language")

        language = language_session or language_cookie

        # Default to English if nothing is set
        if not language:
            language = "en"


        # Activate the language if valid
        if language in ["en", "it"]:
            translation.activate(language)
            request.LANGUAGE_CODE = language
            # Test if translation is actually working
            from django.utils.translation import gettext

            test_approved = gettext("Approved")
            test_discard = gettext("Discard")

        else:
            # Fallback to English
            translation.activate("en")
            request.LANGUAGE_CODE = "en"

        response = self.get_response(request)
        return response
