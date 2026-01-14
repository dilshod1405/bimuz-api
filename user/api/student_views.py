import re
import logging
from rest_framework import status, generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from user.models import Student
from user.api.student_serializers import (
    StudentRegistrationSerializer,
    StudentProfileSerializer,
    StudentLoginSerializer,
    ContractVerificationSerializer
)
from user.api.utils import (
    success_response,
    error_response
)
from user.api.exceptions import EmployeeNotFoundError
# Contract generation moved to booking views - contract is created when student books a group
from user.api.tasks import generate_and_send_verification_code
from user.api.redis_utils import verify_code, get_verification_code, delete_verification_code

logger = logging.getLogger(__name__)


class StudentRegistrationView(generics.CreateAPIView):
    serializer_class = StudentRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Talaba ro'yxatdan o'tkazish va shartnoma PDF yaratish",
        operation_summary="Talaba Ro'yxatdan O'tish",
        request_body=StudentRegistrationSerializer,
        responses={
            201: openapi.Response('Talaba muvaffaqiyatli ro\'yxatdan o\'tdi', StudentProfileSerializer),
            400: openapi.Response('Validatsiya xatolari'),
        },
        tags=['Talaba Autentifikatsiya']
    )
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to format expected by Eskiz (998991234567)
        """
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # If starts with +998, remove +
        if phone_digits.startswith('998'):
            return phone_digits
        # If starts with 998, use as is
        elif phone_digits.startswith('998'):
            return phone_digits
        # If starts with 9 (Uzbek format), add 998 prefix
        elif phone_digits.startswith('9') and len(phone_digits) == 9:
            return '998' + phone_digits
        # Otherwise, assume it's already in correct format or return as is
        return phone_digits
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            student = serializer.save()
            
            # Contract will be generated when student books a group, not during registration
            # Generate contract PDF - REMOVED: Contract is now generated when student books a group
            
            # Normalize phone number for SMS
            normalized_phone = self._normalize_phone(student.phone)
            
            # Generate code, store in Redis, and send SMS asynchronously via Celery
            task_result = generate_and_send_verification_code.delay(
                student_id=student.id,
                phone=normalized_phone
            )
            
            # Prepare response data
            response_data = {
                'student': None,  # Will be set below
                'tokens': None,  # Will be set below
                'sms_queued': True,
            }
            
            # For testing, we can include the code if task completed immediately
            # In production, this won't be available
            try:
                if task_result.ready():
                    result = task_result.get(timeout=1)
                    if result.get('success') and result.get('code'):
                        # Only include in development/testing
                        if settings.DEBUG:
                            response_data['verification_code'] = result.get('code')
                            response_data['note'] = 'Code included for testing. In production, check SMS.'
            except Exception:
                # Task is still running, which is fine
                pass
            
            student.save()
        
        refresh = RefreshToken.for_user(student.user)
        
        student_serializer = StudentProfileSerializer(
            student,
            context={'request': request}
        )
        
        response_data['student'] = student_serializer.data
        response_data['tokens'] = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        return success_response(
            data=response_data,
            message='Talaba muvaffaqiyatli ro\'yxatdan o\'tdi. Tasdiqlash kodi SMS orqali yuborildi. Shartnoma guruh tanlaganingizdan keyin yaratiladi.',
            status_code=status.HTTP_201_CREATED
        )


class StudentLoginView(generics.GenericAPIView):
    serializer_class = StudentLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Talabani autentifikatsiya qilish va JWT tokenlarni olish",
        operation_summary="Talaba Kirish",
        request_body=StudentLoginSerializer,
        responses={
            200: openapi.Response('Kirish muvaffaqiyatli', StudentProfileSerializer),
            400: openapi.Response('Noto\'g\'ri ma\'lumotlar'),
        },
        tags=['Talaba Autentifikatsiya']
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        student = serializer.validated_data['student']
        
        refresh = RefreshToken.for_user(user)
        
        student_serializer = StudentProfileSerializer(
            student,
            context={'request': request}
        )
        
        return success_response(
            data={
                'student': student_serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            },
            message='Kirish muvaffaqiyatli.',
            status_code=status.HTTP_200_OK
        )


class StudentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        if not hasattr(self.request.user, 'student_profile'):
            raise EmployeeNotFoundError()
        return self.request.user.student_profile
    
    @swagger_auto_schema(
        operation_description="Autentifikatsiya qilingan talabaning profil ma'lumotlarini olish",
        operation_summary="Talaba Profilini Olish",
        responses={
            200: openapi.Response('Talaba profili muvaffaqiyatli yuklandi', StudentProfileSerializer),
            401: openapi.Response('Autentifikatsiya talab qilinadi'),
            404: openapi.Response('Talaba profili topilmadi'),
        },
        security=[{'Bearer': []}],
        tags=['Talaba Profili']
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return success_response(
            data=serializer.data,
            message='Talaba profili muvaffaqiyatli yuklandi.'
        )
    
    @swagger_auto_schema(
        operation_description="Autentifikatsiya qilingan talabaning profilini yangilash (qisman yangilash mumkin)",
        operation_summary="Talaba Profilini Yangilash",
        request_body=StudentProfileSerializer,
        responses={
            200: openapi.Response('Talaba profili muvaffaqiyatli yangilandi', StudentProfileSerializer),
            400: openapi.Response('Validatsiya xatolari'),
            401: openapi.Response('Autentifikatsiya talab qilinadi'),
            404: openapi.Response('Talaba profili topilmadi'),
        },
        security=[{'Bearer': []}],
        tags=['Talaba Profili']
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        allowed_fields = ['full_name', 'phone', 'certificate']
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
            message='Talaba profili muvaffaqiyatli yangilandi.'
        )


class ContractVerificationView(generics.GenericAPIView):
    """
    View for verifying contract signing code
    """
    serializer_class = ContractVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Shartnomani elektron imzo bilan tasdiqlash uchun SMS orqali yuborilgan kodni tekshirish",
        operation_summary="Shartnomani Tasdiqlash",
        request_body=ContractVerificationSerializer,
        responses={
            200: openapi.Response('Shartnoma muvaffaqiyatli tasdiqlandi'),
            400: openapi.Response('Noto\'g\'ri kod yoki kod muddati tugagan'),
            401: openapi.Response('Autentifikatsiya talab qilinadi'),
            404: openapi.Response('Talaba profili topilmadi'),
        },
        security=[{'Bearer': []}],
        tags=['Talaba Shartnoma']
    )
    def post(self, request, *args, **kwargs):
        if not hasattr(request.user, 'student_profile'):
            return success_response(
                data=None,
                message='Talaba profili topilmadi.',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        student = request.user.student_profile
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        verification_code = serializer.validated_data['verification_code']
        
        # Check if contract is already signed
        if student.contract_signed:
            return success_response(
                data=None,
                message='Shartnoma allaqachon tasdiqlangan.',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify code from Redis
        code_valid = verify_code(student_id=student.id, code=verification_code)
        
        if not code_valid:
            # Check if code exists at all (to provide better error message)
            stored_code = get_verification_code(student.id)
            if stored_code is None:
                return success_response(
                    data=None,
                    message='Tasdiqlash kodi topilmadi yoki muddati tugagan. Iltimos, yangi kod so\'rang.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            else:
                return success_response(
                    data=None,
                    message='Noto\'g\'ri tasdiqlash kodi.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # Mark contract as signed
        student.contract_signed = True
        student.save()
        
        student_serializer = StudentProfileSerializer(
            student,
            context={'request': request}
        )
        
        return success_response(
            data={
                'student': student_serializer.data,
                'contract_signed': True
            },
            message='Shartnoma muvaffaqiyatli tasdiqlandi.',
            status_code=status.HTTP_200_OK
        )


class ResendVerificationCodeView(generics.GenericAPIView):
    """
    View for resending verification code
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Shartnomani tasdiqlash uchun yangi kod yuborish",
        operation_summary="Tasdiqlash Kodini Qayta Yuborish",
        responses={
            200: openapi.Response('Yangi kod muvaffaqiyatli yuborildi'),
            400: openapi.Response('Shartnoma allaqachon tasdiqlangan yoki xatolik yuz berdi'),
            401: openapi.Response('Autentifikatsiya talab qilinadi'),
            404: openapi.Response('Talaba profili topilmadi'),
        },
        security=[{'Bearer': []}],
        tags=['Talaba Shartnoma']
    )
    def post(self, request, *args, **kwargs):
        if not hasattr(request.user, 'student_profile'):
            return success_response(
                data=None,
                message='Talaba profili topilmadi.',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        student = request.user.student_profile
        
        # Check if contract is already signed
        if student.contract_signed:
            return success_response(
                data=None,
                message='Shartnoma allaqachon tasdiqlangan.',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Normalize phone number for SMS
        normalized_phone = self._normalize_phone(student.phone)
        
        # Generate code, store in Redis, and send SMS asynchronously via Celery
        task_result = generate_and_send_verification_code.delay(  # type: ignore
            student_id=student.id,
            phone=normalized_phone
        )
        
        # Get expiry info from settings
        expiry_minutes = getattr(settings, 'VERIFICATION_CODE_EXPIRY_MINUTES', 2)
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        
        return success_response(
            data={
                'message': 'Yangi tasdiqlash kodi SMS orqali yuborildi.',
                'expires_at': expires_at.isoformat()
            },
            message='Yangi tasdiqlash kodi muvaffaqiyatli yuborildi.',
            status_code=status.HTTP_200_OK
        )
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to format expected by Eskiz (998991234567)
        """
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        # If starts with 998, use as is
        if phone_digits.startswith('998'):
            return phone_digits
        # If starts with 9 (Uzbek format), add 998 prefix
        elif phone_digits.startswith('9') and len(phone_digits) == 9:
            return '998' + phone_digits
        # Otherwise, assume it's already in correct format or return as is
        return phone_digits
