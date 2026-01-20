"""Custom middleware for BIMUZ API."""
import logging
import sys
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware

# Use root logger to ensure logs are visible
logger = logging.getLogger('bimuz.middleware')
# Also log to stdout for Gunicorn
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


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
            # Also set csrf_exempt attribute for DRF compatibility
            setattr(request, 'csrf_exempt', True)
            # Log to both logger and stdout
            msg = f"CSRF disabled for API endpoint: {request.path} (method: {request.method})"
            logger.info(msg)
            print(f"[DisableCSRFForAPI] {msg}")  # Also print to stdout for Gunicorn
        return None
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Additional check to ensure CSRF is disabled for API views."""
        if request.path.startswith('/api/'):
            # Ensure the flag is set even if process_request didn't catch it
            setattr(request, '_dont_enforce_csrf_checks', True)
            setattr(request, 'csrf_exempt', True)
            msg = f"CSRF disabled in process_view for: {request.path}"
            logger.debug(msg)
            print(f"[DisableCSRFForAPI] {msg}")  # Also print to stdout for Gunicorn
        return None
