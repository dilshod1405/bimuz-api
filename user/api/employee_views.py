from rest_framework import status, generics
from rest_framework.filters import SearchFilter
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from django.db.models import Q

from user.models import Employee
from user.api.employee_serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeUpdateSerializer
)
from user.api.permissions import IsDeveloperOrAdministrator, IsEmployee
from user.api.utils import success_response


class EmployeeListView(generics.ListAPIView):
    """
    List view for employees.
    All authenticated employees can read (GET).
    Write operations (POST) require Developer, Director, or Administrator role.
    """
    queryset = Employee.objects.select_related('user').all()
    serializer_class = EmployeeListSerializer
    # All employees can read, but only specific roles can create (handled in permission class)
    permission_classes = [IsEmployee]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(role__icontains=search) |
                Q(professionality__icontains=search)
            )
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="List all employees. All authenticated employees can read this endpoint.",
        operation_summary="List Employees",
        responses={
            200: openapi.Response('Employees retrieved successfully', EmployeeListSerializer(many=True)),
            403: openapi.Response('Permission denied - Authentication required'),
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


class EmployeeRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Employee.objects.select_related('user').all()
    permission_classes = [IsDeveloperOrAdministrator]
    lookup_field = 'pk'
    
    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        
        if request.method in ['PUT', 'PATCH']:
            if not hasattr(request.user, 'employee_profile'):
                return
            
            user_role = request.user.employee_profile.role
            target_role = obj.role
            
            # Director cannot update Developer
            if user_role == 'direktor':
                if target_role == 'dasturchi':
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Direktor Dasturchi rolini yangilay olmaydi.')
            
            # Administrator cannot update Director or Developer
            elif user_role == 'administrator':
                if target_role in ['dasturchi', 'direktor']:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Administrator Direktor yoki Dasturchi rollarini yangilay olmaydi.')
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method in ['PUT', 'PATCH']:
            return EmployeeUpdateSerializer
        return EmployeeDetailSerializer
    
    @swagger_auto_schema(
        operation_description="Retrieve a specific employee by ID (Developer, Director, or Administrator only)",
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
        operation_description="Update a specific employee (Developer, Director, or Administrator only). Director cannot update Developer. Administrator cannot update Director or Developer roles.",
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
        operation_description="Update a specific employee (Developer, Director, or Administrator only). Director cannot update Developer. Administrator cannot update Director or Developer roles.",
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
    
    @swagger_auto_schema(
        operation_description="Delete a specific employee (Developer, Director, or Administrator only). Director cannot delete Developer. Administrator cannot delete Director or Developer roles.",
        operation_summary="Delete Employee",
        responses={
            200: openapi.Response('Employee deleted successfully'),
            403: openapi.Response('Permission denied - Cannot delete Director or Developer roles'),
            404: openapi.Response('Employee not found'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Management']
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if user has permission to delete this specific employee
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Ruxsat yo\'q.')
        
        user_role = request.user.employee_profile.role
        target_role = instance.role
        
        # Director cannot delete Developer
        if user_role == 'direktor':
            if target_role == 'dasturchi':
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Direktor Dasturchi rolini o\'chira olmaydi.')
        
        # Administrator cannot delete Director or Developer roles
        elif user_role == 'administrator':
            if target_role in ['dasturchi', 'direktor']:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Administrator Direktor yoki Dasturchi rollarini o\'chira olmaydi.')
        
        with transaction.atomic():
            # Delete the related User if it exists
            if hasattr(instance, 'user') and instance.user:
                instance.user.delete()
            else:
                # If no user, just delete the employee
                instance.delete()
        
        return success_response(
            data=None,
            message='Xodim muvaffaqiyatli o\'chirildi.'
        )