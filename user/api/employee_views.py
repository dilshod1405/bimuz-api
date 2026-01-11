from rest_framework import status, generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction

from user.models import Employee
from user.api.employee_serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeUpdateSerializer
)
from user.api.permissions import IsDeveloperOrAdministrator
from user.api.utils import success_response


class EmployeeListView(generics.ListAPIView):
    queryset = Employee.objects.select_related('user').all()
    serializer_class = EmployeeListSerializer
    permission_classes = [IsDeveloperOrAdministrator]
    
    @swagger_auto_schema(
        operation_description="List all employees (Developer or Administrator only)",
        operation_summary="List Employees",
        responses={
            200: openapi.Response('Employees retrieved successfully', EmployeeListSerializer(many=True)),
            403: openapi.Response('Permission denied - Developer or Administrator role required'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Management']
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
            message='Xodimlar muvaffaqiyatli yuklandi.'
        )


class EmployeeRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Employee.objects.select_related('user').all()
    permission_classes = [IsDeveloperOrAdministrator]
    lookup_field = 'pk'
    
    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        
        if request.method in ['PUT', 'PATCH']:
            if not hasattr(request.user, 'employee_profile'):
                return
            
            user_role = request.user.employee_profile.role
            
            if user_role == 'administrator':
                target_role = obj.role
                if target_role in ['dasturchi', 'direktor']:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Administrator Direktor yoki Dasturchi rollarini yangilay olmaydi.')
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method in ['PUT', 'PATCH']:
            return EmployeeUpdateSerializer
        return EmployeeDetailSerializer
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific employee by ID (Developer or Administrator only)",
        operation_summary="Get Employee",
        responses={
            200: openapi.Response('Employee retrieved successfully', EmployeeDetailSerializer),
            403: openapi.Response('Permission denied'),
            404: openapi.Response('Employee not found'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Management']
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return success_response(
            data=serializer.data,
            message='Xodim muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Update a specific employee (Developer or Administrator only). Administrator cannot update Director or Developer roles.",
        operation_summary="Update Employee",
        request_body=EmployeeUpdateSerializer,
        responses={
            200: openapi.Response('Employee updated successfully', EmployeeDetailSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Cannot update Director or Developer roles'),
            404: openapi.Response('Employee not found'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Management']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a specific employee (Developer or Administrator only). Administrator cannot update Director or Developer roles.",
        operation_summary="Update Employee",
        request_body=EmployeeUpdateSerializer,
        responses={
            200: openapi.Response('Employee updated successfully', EmployeeDetailSerializer),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Cannot update Director or Developer roles'),
            404: openapi.Response('Employee not found'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Management']
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
        
        response_serializer = EmployeeDetailSerializer(instance, context={'request': request})
        return success_response(
            data=response_serializer.data,
            message='Xodim muvaffaqiyatli yangilandi.'
        )
