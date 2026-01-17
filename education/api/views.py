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
from education.api.permissions import IsAdministrator, IsAdministratorOrMentor, CanViewGroups
from education.api.exceptions import GroupNotFoundError, AttendanceNotFoundError
from user.api.utils import success_response


class GroupListCreateView(generics.ListCreateAPIView):
    queryset = Group.objects.select_related('mentor', 'mentor__user').prefetch_related('students').all()
    permission_classes = [CanViewGroups]
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method == 'POST':
            return GroupCreateSerializer
        return GroupSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # If user is Mentor, filter to show only their groups
        if hasattr(self.request.user, 'employee_profile'):
            user_role = self.request.user.employee_profile.role
            if user_role == 'mentor':
                mentor_employee = self.request.user.employee_profile
                queryset = queryset.filter(mentor=mentor_employee)
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="Ro'yxatdan o'tgan guruhlarni ko'rsatish. Mentor faqat o'z guruhlarini ko'radi, Dasturchi/Direktor/Administrator barcha guruhlarni ko'radi.",
        operation_summary="Guruhlarni Ro'yxatlash",
        responses={
            200: openapi.Response('Guruhlar muvaffaqiyatli yuklandi.', GroupSerializer(many=True)),
            403: openapi.Response('Ruxsat yo\'q'),
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
        operation_description="Yangi guruh yaratish (Faqat Dasturchi, Direktor yoki Administrator uchun)",
        operation_summary="Guruh Yaratish",
        request_body=GroupCreateSerializer,
        responses={
            201: openapi.Response('Guruh muvaffaqiyatli yaratildi.', GroupSerializer),
            400: openapi.Response('Validatsiya xatolari'),
            403: openapi.Response('Ruxsat yo\'q - Faqat Dasturchi, Direktor yoki Administrator'),
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
    permission_classes = [CanViewGroups]
    lookup_field = 'pk'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # If user is Mentor, filter to show only their groups
        if hasattr(self.request.user, 'employee_profile'):
            user_role = self.request.user.employee_profile.role
            if user_role == 'mentor':
                mentor_employee = self.request.user.employee_profile
                queryset = queryset.filter(mentor=mentor_employee)
        
        return queryset
    
    def get_serializer_class(self):  # type: ignore
        if self.request.method in ['PUT', 'PATCH']:
            return GroupUpdateSerializer
        return GroupSerializer
    
    @swagger_auto_schema(
        operation_description="ID bo'yicha guruhni olish. Mentor faqat o'z guruhlarini ko'radi.",
        operation_summary="Guruhni Olish",
        responses={
            200: openapi.Response('Guruh muvaffaqiyatli yuklandi.', GroupSerializer),
            404: openapi.Response('Guruh topilmadi'),
            403: openapi.Response('Ruxsat yo\'q'),
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
        operation_description="Guruhni yangilash (Faqat Dasturchi, Direktor yoki Administrator uchun)",
        operation_summary="Guruhni Yangilash",
        request_body=GroupUpdateSerializer,
        responses={
            200: openapi.Response('Guruh muvaffaqiyatli yangilandi.', GroupSerializer),
            400: openapi.Response('Validatsiya xatolari'),
            404: openapi.Response('Guruh topilmadi'),
            403: openapi.Response('Ruxsat yo\'q - Faqat Dasturchi, Direktor yoki Administrator'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Guruhni yangilash (Faqat Dasturchi, Direktor yoki Administrator uchun)",
        operation_summary="Guruhni Yangilash",
        request_body=GroupUpdateSerializer,
        responses={
            200: openapi.Response('Guruh muvaffaqiyatli yangilandi.', GroupSerializer),
            400: openapi.Response('Validatsiya xatolari'),
            404: openapi.Response('Guruh topilmadi'),
            403: openapi.Response('Ruxsat yo\'q - Faqat Dasturchi, Direktor yoki Administrator'),
        },
        security=[{'Bearer': []}],
        tags=['Groups']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Guruhni o'chirish (Faqat Dasturchi, Direktor yoki Administrator uchun)",
        operation_summary="Guruhni O'chirish",
        responses={
            200: openapi.Response('Guruh muvaffaqiyatli o\'chirildi.'),
            404: openapi.Response('Guruh topilmadi'),
            403: openapi.Response('Ruxsat yo\'q - Faqat Dasturchi, Direktor yoki Administrator'),
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
