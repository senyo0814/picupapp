from django.http import HttpResponseForbidden
import logging

logger = logging.getLogger(__name__)

BLOCKED_PATHS = [
    '/xmlrpc.php',
    '/license.txt',
    '/readme.html',
    '/wp-admin',
    '/wp-includes',
    '/wp-login.php',
    '/wp-content',
]

class BlockBotProbeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower()
        if any(path.startswith(p) for p in BLOCKED_PATHS):
            logger.warning(f"Blocked bot probe: {request.path} from {request.META.get('REMOTE_ADDR')}")
            return HttpResponseForbidden("Forbidden")
        return self.get_response(request)
