from rest_framework import status, generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from user.models import Employee
from user.api.serializers import (
    EmployeeRegistrationSerializer,
    EmployeeProfileSerializer,
    EmployeeLoginSerializer
)
from user.api.utils import success_response
from user.api.exceptions import EmployeeNotFoundError

User = get_user_model()


class EmployeeRegistrationView(generics.CreateAPIView):
    serializer_class = EmployeeRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # Disable authentication for this view
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Register a new employee account with user and employee profile",
        operation_summary="Employee Registration",
        request_body=EmployeeRegistrationSerializer,
        responses={
            201: openapi.Response('Employee registered successfully', EmployeeProfileSerializer),
            400: openapi.Response('Validation errors'),
        },
        tags=['Employee Authentication']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            employee = serializer.save()
            
        refresh = RefreshToken.for_user(employee.user)
        
        employee_serializer = EmployeeProfileSerializer(
            employee,
            context={'request': request}
        )
        
        return success_response(
            data={
                'employee': employee_serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            },
            message='Xodim muvaffaqiyatli ro\'yxatdan o\'tdi.',
            status_code=status.HTTP_201_CREATED
        )


class EmployeeLoginView(generics.GenericAPIView):
    serializer_class = EmployeeLoginSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # Disable authentication for this view
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Authenticate an employee and receive JWT tokens",
        operation_summary="Employee Login",
        request_body=EmployeeLoginSerializer,
        responses={
            200: openapi.Response('Login successful', EmployeeProfileSerializer),
            400: openapi.Response('Invalid credentials'),
        },
        tags=['Employee Authentication']
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        employee = serializer.validated_data['employee']
        
        refresh = RefreshToken.for_user(user)
        
        employee_serializer = EmployeeProfileSerializer(
            employee,
            context={'request': request}
        )
        
        return success_response(
            data={
                'employee': employee_serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            },
            message='Kirish muvaffaqiyatli.',
            status_code=status.HTTP_200_OK
        )


class EmployeeProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        if not hasattr(self.request.user, 'employee_profile'):
            raise EmployeeNotFoundError()
        return self.request.user.employee_profile
    
    @swagger_auto_schema(
        operation_description="Retrieve the authenticated employee's profile information",
        operation_summary="Get Employee Profile",
        responses={
            200: openapi.Response('Employee profile retrieved successfully', EmployeeProfileSerializer),
            401: openapi.Response('Authentication required'),
            404: openapi.Response('Employee profile not found'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Profile']
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return success_response(
            data=serializer.data,
            message='Xodim profili muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Update the authenticated employee's profile (partial update allowed)",
        operation_summary="Update Employee Profile",
        request_body=EmployeeProfileSerializer,
        responses={
            200: openapi.Response('Employee profile updated successfully', EmployeeProfileSerializer),
            400: openapi.Response('Validation errors'),
            401: openapi.Response('Authentication required'),
            404: openapi.Response('Employee profile not found'),
        },
        security=[{'Bearer': []}],
        tags=['Employee Profile']
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        allowed_fields = ['full_name', 'professionality', 'avatar']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(
            instance,
            data=data,
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return success_response(
            data=serializer.data,
            message='Xodim profili muvaffaqiyatli yangilandi.'
        )
