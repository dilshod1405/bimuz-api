from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from user.models import User, Student, Source
from user.api.exceptions import EmployeeAlreadyExistsError


class StudentRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True)
    
    full_name = serializers.CharField(required=True, max_length=255)
    phone = serializers.CharField(required=True, max_length=17)
    passport_serial_number = serializers.CharField(required=True, max_length=20)
    birth_date = serializers.DateField(required=True)
    source = serializers.ChoiceField(choices=Source.choices, required=True)
    address = serializers.CharField(required=True, allow_blank=False, help_text='Student full address')
    inn = serializers.CharField(
        required=True,
        max_length=9,
        allow_blank=False,
        help_text='Individual Taxpayer Identification Number (maksimum 9 ta raqam)',
        validators=[
            RegexValidator(
                regex=r'^\d{1,9}$',
                message="INN faqat raqamlardan iborat bo'lishi kerak va maksimum 9 ta belgi bo'lishi kerak."
            )
        ]
    )
    pinfl = serializers.CharField(required=True, max_length=14, allow_blank=False, help_text='Personal Identification Number of Physical Person')
    
    class Meta:
        model = Student
        fields = [
            'email', 'password', 'password_confirm',
            'full_name', 'phone', 'passport_serial_number',
            'birth_date', 'source', 'address', 'inn', 'pinfl'
        ]
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Bu email bilan foydalanuvchi allaqachon mavjud.')
        return value
    
    def validate_phone(self, value):
        if Student.objects.filter(phone=value).exists():
            raise serializers.ValidationError('Bu telefon raqami allaqachon ro\'yxatdan o\'tgan.')
        return value
    
    def validate_passport_serial_number(self, value):
        if Student.objects.filter(passport_serial_number=value).exists():
            raise serializers.ValidationError('Bu passport seriya raqami allaqachon ro\'yxatdan o\'tgan.')
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Parollar mos kelmaydi.'
            })
        
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm')
        email = validated_data.pop('email')
        full_name = validated_data.pop('full_name')
        
        first_name = full_name.split()[0] if full_name else 'Student'
        last_name = ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
        
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        student = Student._default_manager.create(
            user=user,
            full_name=full_name,
            **validated_data
        )
        
        return student


class StudentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    contract_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'passport_serial_number',
            'birth_date', 'source', 'source_display',
            'address', 'inn', 'pinfl',
            'group', 'certificate', 'contract', 'contract_url',
            'contract_signed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'contract_signed']
    
    def get_contract_url(self, obj):
        if obj.contract:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.contract.url)
            return obj.contract.url
        return None


class StudentLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError({
                'email': 'Email va parol talab qilinadi.'
            })
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': 'Noto\'g\'ri email yoki parol.'
            })
        
        if not user.check_password(password):
            raise serializers.ValidationError({
                'email': 'Noto\'g\'ri email yoki parol.'
            })
        
        if not hasattr(user, 'student_profile'):
            raise serializers.ValidationError({
                'email': 'Bu foydalanuvchi uchun talaba profili topilmadi.'
            })
        
        attrs['user'] = user
        attrs['student'] = user.student_profile
        
        return attrs


class ContractVerificationSerializer(serializers.Serializer):
    verification_code = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text='6-digit verification code sent via SMS'
    )
    
    def validate_verification_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('Tasdiqlash kodi faqat raqamlardan iborat bo\'lishi kerak.')
        return value
