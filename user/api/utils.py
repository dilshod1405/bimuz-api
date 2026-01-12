import random
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    response_data = {'success': True}
    if message:
        response_data['message'] = message
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    response_data = {
        'success': False,
        'message': message
    }
    if errors:
        response_data['errors'] = errors
    return Response(response_data, status=status_code)


def generate_verification_code() -> str:
    """
    Generate a random 6-digit verification code
    """
    return str(random.randint(100000, 999999))


def get_verification_code_expiry() -> timezone.datetime:
    """
    Get the expiry datetime for verification code
    """
    expiry_minutes = getattr(settings, 'VERIFICATION_CODE_EXPIRY_MINUTES', 10)
    return timezone.now() + timedelta(minutes=expiry_minutes)
