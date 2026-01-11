from django.urls import path
from education.api.views import (
    GroupListCreateView,
    GroupRetrieveUpdateDestroyView,
    AttendanceListCreateView,
    AttendanceRetrieveUpdateDestroyView
)

app_name = 'education_api'

urlpatterns = [
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', GroupRetrieveUpdateDestroyView.as_view(), name='group-retrieve-update-destroy'),
    path('attendances/', AttendanceListCreateView.as_view(), name='attendance-list-create'),
    path('attendances/<int:pk>/', AttendanceRetrieveUpdateDestroyView.as_view(), name='attendance-retrieve-update-destroy'),
]
