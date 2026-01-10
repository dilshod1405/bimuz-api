from rest_framework import status
from rest_framework.exceptions import APIException


class EmployeeNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Employee profile not found.'
    default_code = 'employee_not_found'


class EmployeeAlreadyExistsError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Employee with this email already exists.'
    default_code = 'employee_already_exists'
