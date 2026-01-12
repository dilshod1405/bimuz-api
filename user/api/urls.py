from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from user.api.views import (
    EmployeeRegistrationView,
    EmployeeLoginView,
    EmployeeProfileView
)
from user.api.employee_views import (
    EmployeeListView,
    EmployeeRetrieveUpdateView
)
from user.api.student_views import (
    StudentRegistrationView,
    StudentLoginView,
    StudentProfileView,
    ContractVerificationView,
    ResendVerificationCodeView
)

app_name = 'user_api'

urlpatterns = [
    path('register/', EmployeeRegistrationView.as_view(), name='employee-register'),
    path('login/', EmployeeLoginView.as_view(), name='employee-login'),
    path('profile/', EmployeeProfileView.as_view(), name='employee-profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeeRetrieveUpdateView.as_view(), name='employee-retrieve-update'),
    
    path('students/register/', StudentRegistrationView.as_view(), name='student-register'),
    path('students/login/', StudentLoginView.as_view(), name='student-login'),
    path('students/profile/', StudentProfileView.as_view(), name='student-profile'),
    path('students/verify-contract/', ContractVerificationView.as_view(), name='student-verify-contract'),
    path('students/resend-code/', ResendVerificationCodeView.as_view(), name='student-resend-code'),
]
