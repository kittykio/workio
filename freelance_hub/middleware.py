from django.conf import settings


class FrameAncestorsMiddleware:
    """Allow Workio previews only on explicitly trusted portfolio origins."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ancestors = " ".join(settings.FRAME_ANCESTORS)
        response.headers["Content-Security-Policy"] = f"frame-ancestors {ancestors}"
        return response
