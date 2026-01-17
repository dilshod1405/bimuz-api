from rest_framework import status, generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from django.db.models import Q

from user.models import Student
from user.api.student_management_serializers import (
    StudentListSerializer,
    StudentDetailSerializer,
    StudentCreateSerializer,
    StudentUpdateSerializer
)
from user.api.permissions import IsEmployee, IsDeveloperOrAdministrator
from user.api.utils import success_response


class StudentListView(generics.ListCreateAPIView):
    queryset = Student.objects.select_related('user', 'group').all()
    serializer_class = StudentListSerializer
    permission_classes = [IsEmployee]
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method == 'POST':
            return StudentCreateSerializer
        return StudentListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(phone__icontains=search) |
                Q(passport_serial_number__icontains=search) |
                Q(inn__icontains=search) |
                Q(pinfl__icontains=search)
            )
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="List all students. All employees can view. Only Developer and Administrator can create.",
        operation_summary="List Students",
        responses={
            200: openapi.Response('Students retrieved successfully', StudentListSerializer(many=True)),
            403: openapi.Response('Permission denied'),
        },
        security=[{'Bearer': []}],
        tags=['Student Management']
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
            message='Talabalar muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Create a new student (Developer or Administrator only)",
        operation_summary="Create Student",
        request_body=StudentCreateSerializer,
        responses={
            201: openapi.Response('Student created successfully', StudentDetailSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Developer or Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Student Management']
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            student = serializer.save()
        
        response_serializer = StudentDetailSerializer(student, context={'request': request})
        return success_response(
            data=response_serializer.data,
            message='Talaba muvaffaqiyatli qo\'shildi.',
            status_code=status.HTTP_201_CREATED
        )


class StudentRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.select_related('user', 'group').all()
    permission_classes = [IsEmployee]
    lookup_field = 'pk'
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method in ['PUT', 'PATCH']:
            return StudentUpdateSerializer
        return StudentDetailSerializer
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific student by ID. All employees can view.",
        operation_summary="Get Student",
        responses={
            200: openapi.Response('Student retrieved successfully', StudentDetailSerializer),
            403: openapi.Response('Permission denied'),
            404: openapi.Response('Student not found'),
        },
        security=[{'Bearer': []}],
        tags=['Student Management']
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return success_response(
            data=serializer.data,
            message='Talaba muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Update a specific student (Developer or Administrator only)",
        operation_summary="Update Student",
        request_body=StudentUpdateSerializer,
        responses={
            200: openapi.Response('Student updated successfully', StudentDetailSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Developer or Administrator role required'),
            404: openapi.Response('Student not found'),
        },
        security=[{'Bearer': []}],
        tags=['Student Management']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a specific student (Developer or Administrator only)",
        operation_summary="Update Student",
        request_body=StudentUpdateSerializer,
        responses={
            200: openapi.Response('Student updated successfully', StudentDetailSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Developer or Administrator role required'),
            404: openapi.Response('Student not found'),
        },
        security=[{'Bearer': []}],
        tags=['Student Management']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            serializer.save()
        
        response_serializer = StudentDetailSerializer(instance, context={'request': request})
        return success_response(
            data=response_serializer.data,
            message='Talaba muvaffaqiyatli yangilandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Delete a specific student (Developer or Administrator only)",
        operation_summary="Delete Student",
        responses={
            200: openapi.Response('Student deleted successfully'),
            403: openapi.Response('Permission denied - Developer or Administrator role required'),
            404: openapi.Response('Student not found'),
        },
        security=[{'Bearer': []}],
        tags=['Student Management']
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if user has permission to delete
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Ruxsat yo\'q.')
        
        user_role = request.user.employee_profile.role
        
        if user_role not in ['dasturchi', 'administrator']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Talabani o\'chirish uchun Dasturchi yoki Administrator roli kerak.')
        
        with transaction.atomic():
            # Delete the related User if it exists
            if hasattr(instance, 'user') and instance.user:
                instance.user.delete()
            else:
                # If no user, just delete the student
                instance.delete()
        
        return success_response(
            data=None,
            message='Talaba muvaffaqiyatli o\'chirildi.'
        )
