from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from user.models import User, Employee, Role, Speciality
from user.api.exceptions import EmployeeAlreadyExistsError


class EmployeeRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, write_only=True)
    first_name = serializers.CharField(required=True, write_only=True, max_length=150)
    last_name = serializers.CharField(required=True, write_only=True, max_length=150)
    password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True)
    
    full_name = serializers.CharField(required=True, max_length=255)
    role = serializers.ChoiceField(choices=Role.choices, required=True)
    speciality_id = serializers.ChoiceField(
        choices=Speciality.choices,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Employee
        fields = [
            'email', 'first_name', 'last_name', 'password', 'password_confirm',
            'full_name', 'role', 'speciality_id', 'avatar'
        ]
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise EmployeeAlreadyExistsError()
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        
        role = attrs.get('role')
        speciality_id = attrs.get('speciality_id')
        
        if role == 'mentor' and not speciality_id:
            raise serializers.ValidationError({
                'speciality_id': 'Speciality is required for Mentors.'
            })
        
        if role != 'mentor' and speciality_id:
            raise serializers.ValidationError({
                'speciality_id': 'Speciality should only be set for Mentors.'
            })
        
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm')
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        employee = Employee._default_manager.create(  # type: ignore
            user=user,
            **validated_data
        )
        
        return employee


class EmployeeProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    speciality_display = serializers.CharField(source='get_speciality_id_display', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    role = serializers.CharField(read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'role_display',
            'speciality_id', 'speciality_display',
            'avatar', 'avatar_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'role', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        if self.instance:
            role = self.instance.role
            speciality_id = attrs.get('speciality_id', self.instance.speciality_id)
            
            if role == 'mentor' and not speciality_id:
                raise serializers.ValidationError({
                    'speciality_id': 'Speciality is required for Mentors.'
                })
            
            if role != 'mentor' and speciality_id:
                raise serializers.ValidationError({
                    'speciality_id': 'Speciality should only be set for Mentors.'
                })
        
        return attrs
    
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
        
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({
                'email': 'Invalid email or password.'
            })
        
        if not user.check_password(password):
            raise serializers.ValidationError({
                'email': 'Invalid email or password.'
            })
        
        if not hasattr(user, 'employee_profile'):
            raise serializers.ValidationError({
                'email': 'No employee profile found for this user.'
            })
        
        attrs['user'] = user
        attrs['employee'] = user.employee_profile
        
        return attrs
