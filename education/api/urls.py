from django.urls import path
from education.api.views import (
    GroupListCreateView,
    GroupRetrieveUpdateDestroyView,
    AttendanceListCreateView,
    AttendanceRetrieveUpdateDestroyView
)
from education.api import booking_views

app_name = 'education_api'

urlpatterns = [
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', GroupRetrieveUpdateDestroyView.as_view(), name='group-retrieve-update-destroy'),
    path('attendances/', AttendanceListCreateView.as_view(), name='attendance-list-create'),
    path('attendances/<int:pk>/', AttendanceRetrieveUpdateDestroyView.as_view(), name='attendance-retrieve-update-destroy'),
    
    path('booking/groups/', booking_views.GroupBookingListView.as_view(), name='booking-group-list'),
    path('booking/book/', booking_views.StudentBookingCreateView.as_view(), name='booking-create'),
    path('booking/cancel/', booking_views.StudentBookingCancelView.as_view(), name='booking-cancel'),
    path('booking/change-group/', booking_views.StudentGroupChangeView.as_view(), name='booking-change-group'),
]
