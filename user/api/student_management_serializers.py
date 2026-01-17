from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from user.models import User, Student, Source


class StudentListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    group_name = serializers.SerializerMethodField()
    contract_url = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'passport_serial_number', 'birth_date',
            'source', 'source_display', 'address', 'inn', 'pinfl',
            'group', 'group_name', 'contract_signed', 'is_active',
            'contract_url', 'certificate_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'contract_signed']
    
    def get_group_name(self, obj):
        if obj.group:
            return obj.group.__str__()
        return None
    
    def get_contract_url(self, obj):
        if obj.contract:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.contract.url)
            return obj.contract.url
        return None
    
    def get_certificate_url(self, obj):
        if obj.certificate:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.certificate.url)
            return obj.certificate.url
        return None


class StudentDetailSerializer(StudentListSerializer):
    contract = serializers.FileField(required=False, allow_null=True, read_only=True)
    certificate = serializers.FileField(required=False, allow_null=True, read_only=True)
    
    class Meta(StudentListSerializer.Meta):
        fields = StudentListSerializer.Meta.fields + ['contract', 'certificate']
        read_only_fields = StudentListSerializer.Meta.read_only_fields + ['contract', 'certificate']


class StudentCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True)
    
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


class StudentUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'passport_serial_number', 'birth_date',
            'source', 'source_display', 'address', 'inn', 'pinfl',
            'group', 'certificate', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'first_name', 'last_name', 'created_at', 'updated_at']
    
    def validate_phone(self, value):
        instance = self.instance
        if instance and Student.objects.filter(phone=value).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError('Bu telefon raqami allaqachon ro\'yxatdan o\'tgan.')
        return value
    
    def validate_passport_serial_number(self, value):
        instance = self.instance
        if instance and Student.objects.filter(passport_serial_number=value).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError('Bu passport seriya raqami allaqachon ro\'yxatdan o\'tgan.')
        return value
    
    def update(self, instance, validated_data):
        is_active = validated_data.pop('user', {}).pop('is_active', None)
        
        # Update student fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update user.is_active if provided
        if is_active is not None and instance.user:
            instance.user.is_active = is_active
            instance.user.save()
        
        return instance