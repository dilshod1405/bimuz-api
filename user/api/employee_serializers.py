from rest_framework import serializers
from user.models import Employee, User, Role


class EmployeeListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'professionality',
            'avatar_url', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    professionality = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=255
    )
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'professionality',
            'avatar', 'avatar_url', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'first_name', 'last_name', 'created_at', 'updated_at']
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def validate_role(self, value):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'employee_profile'):
            return value
        
        user_role = request.user.employee_profile.role
        
        if user_role == 'administrator':
            if value in ['dasturchi', 'direktor']:
                raise serializers.ValidationError('Administrator Direktor yoki Dasturchi rollarini tayinlay olmaydi.')
        
        return value
    
    def validate(self, attrs):
        return attrs
    
    def update(self, instance, validated_data):
        is_active = None
        if 'user' in validated_data:
            user_data = validated_data.pop('user')
            is_active = user_data.get('is_active')
        elif 'is_active' in validated_data:
            is_active = validated_data.pop('is_active')
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        if is_active is not None and instance.user:
            instance.user.is_active = is_active
            instance.user.save()
        
        return instance


class EmployeeDetailSerializer(EmployeeListSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    class Meta(EmployeeListSerializer.Meta):
        fields = EmployeeListSerializer.Meta.fields + ['avatar']
        read_only_fields = EmployeeListSerializer.Meta.read_only_fields
