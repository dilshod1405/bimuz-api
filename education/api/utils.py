from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message='Muvaffaqiyatli', status_code=status.HTTP_200_OK):
    return Response({
        'success': True,
        'message': message,
        'data': data
    }, status=status_code)


def error_response(message='Xatolik', errors=None, status_code=status.HTTP_400_BAD_REQUEST, data=None):
    response_data = {
        'success': False,
        'message': message,
        'errors': errors
    }
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)
