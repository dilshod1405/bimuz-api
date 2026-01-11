from rest_framework import status, generics, permissions
from rest_framework.response import Response
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from education.models import Group
from user.models import Student
from education.api.serializers import GroupSerializer
from education.api.booking_serializers import (
    GroupBookingSerializer,
    StudentBookingSerializer,
    AlternativeGroupSuggestionSerializer
)
from education.api.utils import success_response, error_response


class GroupBookingListView(generics.ListAPIView):
    """
    List all groups available for booking.
    Shows groups that can accept bookings based on 10-day rule.
    """
    serializer_class = GroupBookingSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Group._default_manager.all().select_related('mentor', 'mentor__user').prefetch_related('students')
        return queryset
    
    @swagger_auto_schema(
        operation_description="List all groups available for booking",
        operation_summary="List Available Groups for Booking",
        responses={
            200: openapi.Response('List of available groups', GroupBookingSerializer(many=True)),
        },
        tags=['Student Booking']
    )
    def get(self, request, *args, **kwargs):
        groups = self.get_queryset()
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentBookingCreateView(generics.CreateAPIView):
    """
    Create a booking for a student in a group.
    Validates:
    - Student exists and is not already booked
    - Group has available seats
    - Group can accept bookings (10-day rule)
    """
    serializer_class = StudentBookingSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Book a student into a group. Validates seat availability and 10-day rule.",
        operation_summary="Book Student into Group",
        request_body=StudentBookingSerializer,
        responses={
            201: openapi.Response('Booking created successfully'),
            400: openapi.Response('Validation errors or booking not allowed'),
        },
        tags=['Student Booking']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        student_id = serializer.validated_data['student_id']
        group_id = serializer.validated_data['group_id']
        
        try:
            with transaction.atomic():  # type: ignore
                student = Student._default_manager.select_for_update().get(id=student_id)
                group = Group._default_manager.select_for_update().get(id=group_id)
                
                if student.group:
                    return error_response(
                        message='Student is already booked in another group.',
                        errors={'student_id': ['Student already has a booking.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                if group.available_seats <= 0:
                    alternatives = self._get_alternative_groups(group)
                    return error_response(
                        message='No available seats in this group.',
                        errors={'group_id': ['Group is full.']},
                        status_code=status.HTTP_400_BAD_REQUEST,
                        data={'alternatives': alternatives} if alternatives else None
                    )
                
                if not group.can_accept_bookings():
                    days_since = group.days_since_start()
                    if days_since is not None and days_since >= 10:
                        alternatives = self._get_alternative_groups(group)
                        return error_response(
                            message=f'Cannot book this group. It started {days_since} days ago (10-day limit exceeded).',
                            errors={'group_id': ['10-day booking limit exceeded.']},
                            status_code=status.HTTP_400_BAD_REQUEST,
                            data={'alternatives': alternatives} if alternatives else None
                        )
                
                student.group = group
                student.save()
                
                group_serializer = GroupBookingSerializer(group, context={'request': request})
                
                return success_response(
                    data={
                        'booking': {
                            'student_id': student.id,
                            'student_name': student.full_name,
                            'group': group_serializer.data
                        }
                    },
                    message='Student booked successfully into the group.',
                    status_code=status.HTTP_201_CREATED
                )
        except Student.DoesNotExist:
            return error_response(
                message='Student not found.',
                errors={'student_id': ['Student does not exist.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return error_response(
                message='Group not found.',
                errors={'group_id': ['Group does not exist.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    def _get_alternative_groups(self, original_group):
        """
        Get alternative groups with similar speciality that are planned and have available seats.
        """
        alternatives = Group._default_manager.filter(
            speciality_id=original_group.speciality_id,
            is_active=True
        ).exclude(id=original_group.id).select_related('mentor', 'mentor__user').prefetch_related('students')
        
        available_alternatives = []
        for group in alternatives:
            if group.can_accept_bookings() and group.available_seats > 0:
                available_alternatives.append(group)
        
        if available_alternatives:
            serializer = AlternativeGroupSuggestionSerializer(available_alternatives[:5], many=True)
            return serializer.data
        return []


class StudentBookingCancelView(generics.GenericAPIView):
    """
    Cancel a student's booking (remove student from group).
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Cancel a student's booking by removing them from their group",
        operation_summary="Cancel Student Booking",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'student_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Student ID')
            },
            required=['student_id']
        ),
        responses={
            200: openapi.Response('Booking cancelled successfully'),
            400: openapi.Response('Student has no booking'),
            404: openapi.Response('Student not found'),
        },
        tags=['Student Booking']
    )
    def post(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        
        if not student_id:
            return error_response(
                message='student_id is required.',
                errors={'student_id': ['This field is required.']},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():  # type: ignore
                student = Student._default_manager.select_for_update().get(id=student_id)
                
                if not student.group:
                    return error_response(
                        message='Student has no active booking.',
                        errors={'student_id': ['Student is not booked in any group.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                group = student.group
                student.group = None
                student.save()
                
                return success_response(
                    data={
                        'cancelled_booking': {
                            'student_id': student.id,
                            'student_name': student.full_name,
                            'group_id': group.id,
                            'group_name': str(group)
                        }
                    },
                    message='Booking cancelled successfully.',
                    status_code=status.HTTP_200_OK
                )
        except Student.DoesNotExist:  # type: ignore
            return error_response(
                message='Student not found.',
                errors={'student_id': ['Student does not exist.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
