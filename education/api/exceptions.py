from rest_framework.exceptions import APIException
from rest_framework import status


class GroupNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Group not found.'
    default_code = 'group_not_found'


class AttendanceNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Attendance not found.'
    default_code = 'attendance_not_found'


class InvalidParticipantError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'One or more participants are not members of the selected group.'
    default_code = 'invalid_participant'
