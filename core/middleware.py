# core/middleware.py
class LogRefererMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/ui/"):
            print(
                f"[TRACE] path={request.path} method={request.method} "
                f"referer={request.META.get('HTTP_REFERER')} "
                f"user={request.user if hasattr(request, 'user') and request.user.is_authenticated else 'anon'}"
            )
        return self.get_response(request)
