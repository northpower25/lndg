from django.utils import translation


class UserLanguageMiddleware:
    """Activate persisted user language preference for authenticated users."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = None
        try:
            from gui.models import UserMode

            language = UserMode.load().language
        except Exception:
            language = None
        if not language:
            language = translation.get_language_from_request(request) or "en"
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        response.headers["Content-Language"] = language
        return response
