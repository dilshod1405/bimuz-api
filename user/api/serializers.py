from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from user.models import User, Employee, Role
from user.api.exceptions import EmployeeAlreadyExistsError


class EmployeeRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, write_only=True)
    first_name = serializers.CharField(required=True, write_only=True, max_length=150)
    last_name = serializers.CharField(required=True, write_only=True, max_length=150)
    password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True)
    
    full_name = serializers.CharField(required=True, max_length=255)
    role = serializers.ChoiceField(choices=Role.choices, required=True)
    professionality = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=255
    )
    avatar = serializers.ImageField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)
    
    class Meta:
        model = Employee
        fields = [
            'email', 'first_name', 'last_name', 'password', 'password_confirm',
            'full_name', 'role', 'professionality', 'avatar', 'is_active'
        ]
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise EmployeeAlreadyExistsError()
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
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        is_active = validated_data.pop('is_active', True)
        
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active
        )
        
        employee = Employee._default_manager.create(
            user=user,
            **validated_data
        )
        
        return employee


class EmployeeProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'role_display',
            'professionality',
            'avatar', 'avatar_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'role', 'created_at', 'updated_at']
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class EmployeeLoginSerializer(serializers.Serializer):
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
        
        if not hasattr(user, 'employee_profile'):
            raise serializers.ValidationError({
                'email': 'Bu foydalanuvchi uchun xodim profili topilmadi.'
            })
        
        attrs['user'] = user
        attrs['employee'] = user.employee_profile
        
        return attrs
