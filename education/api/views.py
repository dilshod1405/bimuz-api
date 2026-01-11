from rest_framework import status, generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction

from education.models import Group, Attendance
from education.api.serializers import (
    GroupSerializer,
    GroupCreateSerializer,
    GroupUpdateSerializer,
    AttendanceSerializer
)
from education.api.permissions import IsAdministrator, IsAdministratorOrMentor
from education.api.exceptions import GroupNotFoundError, AttendanceNotFoundError
from user.api.utils import success_response


class GroupListCreateView(generics.ListCreateAPIView):
    queryset = Group.objects.select_related('mentor', 'mentor__user').prefetch_related('students').all()  # type: ignore
    permission_classes = [IsAdministrator]
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method == 'POST':
            return GroupCreateSerializer
        return GroupSerializer
    
    @swagger_auto_schema(
        operation_description="List all groups (Administrator only)",
        operation_summary="List Groups",
        responses={
            200: openapi.Response('Groups retrieved successfully', GroupSerializer(many=True)),
            403: openapi.Response('Permission denied - Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message='Guruhlar muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Create a new group (Administrator only)",
        operation_summary="Create Group",
        request_body=GroupCreateSerializer,
        responses={
            201: openapi.Response('Group created successfully', GroupSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            group = serializer.save()
        
        response_serializer = GroupSerializer(group, context={'request': request})
        return success_response(
            data=response_serializer.data,
            message='Guruh muvaffaqiyatli yaratildi.',
            status_code=status.HTTP_201_CREATED
        )


class GroupRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.select_related('mentor', 'mentor__user').prefetch_related('students').all()  # type: ignore
    permission_classes = [IsAdministrator]
    lookup_field = 'pk'
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method in ['PUT', 'PATCH']:
            return GroupUpdateSerializer
        return GroupSerializer
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific group by ID (Administrator only)",
        operation_summary="Get Group",
        responses={
            200: openapi.Response('Group retrieved successfully', GroupSerializer),
            404: openapi.Response('Group not found'),
            403: openapi.Response('Permission denied - Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return success_response(
            data=serializer.data,
            message='Guruh muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Update a specific group by ID (Administrator only)",
        operation_summary="Update Group",
        request_body=GroupUpdateSerializer,
        responses={
            200: openapi.Response('Group updated successfully', GroupSerializer),
            400: openapi.Response('Validation errors'),
            404: openapi.Response('Group not found'),
            403: openapi.Response('Permission denied - Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a specific group by ID (Administrator only)",
        operation_summary="Update Group",
        request_body=GroupUpdateSerializer,
        responses={
            200: openapi.Response('Group updated successfully', GroupSerializer),
            400: openapi.Response('Validation errors'),
            404: openapi.Response('Group not found'),
            403: openapi.Response('Permission denied - Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a specific group by ID (Administrator only)",
        operation_summary="Delete Group",
        responses={
            204: openapi.Response('Group deleted successfully'),
            404: openapi.Response('Group not found'),
            403: openapi.Response('Permission denied - Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message='Guruh muvaffaqiyatli o\'chirildi.',
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            serializer.save()
        
        return success_response(
            data=serializer.data,
            message='Guruh muvaffaqiyatli yangilandi.'
        )


class AttendanceListCreateView(generics.ListCreateAPIView):
    queryset = Attendance.objects.select_related(  # type: ignore
        'group', 'group__mentor', 'group__mentor__user', 'mentor', 'mentor__user'
    ).prefetch_related('participants').all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAdministratorOrMentor]
    
    @swagger_auto_schema(
        operation_description="List all attendances (Administrator or Mentor only)",
        operation_summary="List Attendances",
        responses={
            200: openapi.Response('Attendances retrieved successfully', AttendanceSerializer(many=True)),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
        },
        security=[{'Bearer': []}],
        tags=['Attendances']
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message='Davomatlar muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Create a new attendance (Administrator or Mentor only)",
        operation_summary="Create Attendance",
        request_body=AttendanceSerializer,
        responses={
            201: openapi.Response('Attendance created successfully', AttendanceSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
        },
        security=[{'Bearer': []}],
        tags=['Attendances']
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            attendance = serializer.save()
        
        response_serializer = AttendanceSerializer(attendance, context={'request': request})
        return success_response(
            data=response_serializer.data,
            message='Davomat muvaffaqiyatli yaratildi.',
            status_code=status.HTTP_201_CREATED
        )


class AttendanceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Attendance.objects.select_related(  # type: ignore
        'group', 'group__mentor', 'group__mentor__user', 'mentor', 'mentor__user'
    ).prefetch_related('participants').all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAdministratorOrMentor]
    lookup_field = 'pk'
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific attendance by ID (Administrator or Mentor only)",
        operation_summary="Get Attendance",
        responses={
            200: openapi.Response('Attendance retrieved successfully', AttendanceSerializer),
            404: openapi.Response('Attendance not found'),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
        },
        security=[{'Bearer': []}],
        tags=['Attendances']
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return success_response(
            data=serializer.data,
            message='Davomat muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Update a specific attendance by ID (Administrator or Mentor only)",
        operation_summary="Update Attendance",
        request_body=AttendanceSerializer,
        responses={
            200: openapi.Response('Attendance updated successfully', AttendanceSerializer),
            400: openapi.Response('Validation errors'),
            404: openapi.Response('Attendance not found'),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
        },
        security=[{'Bearer': []}],
        tags=['Attendances']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a specific attendance by ID (Administrator or Mentor only)",
        operation_summary="Update Attendance",
        request_body=AttendanceSerializer,
        responses={
            200: openapi.Response('Attendance updated successfully', AttendanceSerializer),
            400: openapi.Response('Validation errors'),
            404: openapi.Response('Attendance not found'),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
        },
        security=[{'Bearer': []}],
        tags=['Attendances']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a specific attendance by ID (Administrator or Mentor only)",
        operation_summary="Delete Attendance",
        responses={
            204: openapi.Response('Attendance deleted successfully'),
            404: openapi.Response('Attendance not found'),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
        },
        security=[{'Bearer': []}],
        tags=['Attendances']
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(
            message='Davomat muvaffaqiyatli o\'chirildi.',
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            serializer.save()
        
        return success_response(
            data=serializer.data,
            message='Davomat muvaffaqiyatli yangilandi.'
        )
