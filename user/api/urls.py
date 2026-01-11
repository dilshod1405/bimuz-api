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

app_name = 'user_api'

urlpatterns = [
    path('register/', EmployeeRegistrationView.as_view(), name='employee-register'),
    path('login/', EmployeeLoginView.as_view(), name='employee-login'),
    path('profile/', EmployeeProfileView.as_view(), name='employee-profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeeRetrieveUpdateView.as_view(), name='employee-retrieve-update'),
]
