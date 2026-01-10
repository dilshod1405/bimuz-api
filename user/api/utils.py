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
