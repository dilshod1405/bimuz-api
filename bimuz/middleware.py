"""Custom middleware for BIMUZ API."""
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class DisableCSRFForAPI(MiddlewareMixin):
    """
    Middleware to disable CSRF protection for API endpoints.
    
    API endpoints use JWT authentication instead of CSRF tokens,
    so CSRF protection is not needed for /api/ routes.
    This middleware must be placed BEFORE CsrfViewMiddleware in MIDDLEWARE.
    """
    
    def process_request(self, request):
        """Exempt API routes from CSRF protection."""
        # Check if the request path starts with /api/
        # This includes all API endpoints: /api/v1/auth/, /api/v1/education/, etc.
        if request.path.startswith('/api/'):
            # Set a flag to skip CSRF check
            # Django's CsrfViewMiddleware checks this flag
            setattr(request, '_dont_enforce_csrf_checks', True)
            logger.info(f"CSRF disabled for API endpoint: {request.path} (method: {request.method})")
        return None
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Additional check to ensure CSRF is disabled for API views."""
        if request.path.startswith('/api/'):
            # Ensure the flag is set even if process_request didn't catch it
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
