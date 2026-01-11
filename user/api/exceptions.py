from rest_framework import status
from rest_framework.exceptions import APIException


class EmployeeNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Xodim profili topilmadi.'
    default_code = 'employee_not_found'


class EmployeeAlreadyExistsError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Bu email bilan xodim allaqachon mavjud.'
    default_code = 'employee_already_exists'
