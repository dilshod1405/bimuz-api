from rest_framework import serializers
from education.models import Group
from user.models import Student, Speciality


class GroupBookingSerializer(serializers.ModelSerializer):
    """Serializer for group booking with availability info."""
    speciality_display = serializers.CharField(source='get_speciality_id_display', read_only=True)
    dates_display = serializers.CharField(source='get_dates_display', read_only=True)
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    current_students_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_planned = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    can_accept_bookings = serializers.BooleanField(read_only=True)
    days_since_start = serializers.IntegerField(read_only=True, allow_null=True)
    
    class Meta:
        model = Group
        fields = [
            'id', 'speciality_id', 'speciality_display',
            'dates', 'dates_display', 'time', 'starting_date',
            'seats', 'current_students_count', 'available_seats',
            'is_planned', 'is_active', 'can_accept_bookings',
            'days_since_start', 'mentor', 'mentor_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StudentBookingSerializer(serializers.Serializer):
    """Serializer for student booking a group."""
    student_id = serializers.IntegerField(required=True)
    group_id = serializers.IntegerField(required=True)
    
    def validate_student_id(self, value):
        try:
            student = Student._default_manager.get(id=value)
        except Student.DoesNotExist:
            raise serializers.ValidationError('Student not found.')
        return value
    
    def validate_group_id(self, value):
        try:
            group = Group._default_manager.get(id=value)
        except Group.DoesNotExist:
            raise serializers.ValidationError('Group not found.')
        return value
    
    def validate(self, attrs):
        student_id = attrs.get('student_id')
        group_id = attrs.get('group_id')
        
        student = Student._default_manager.get(id=student_id)
        group = Group._default_manager.get(id=group_id)
        
        if student.group and student.group.id == group_id:
            raise serializers.ValidationError({
                'group_id': 'Student is already booked in this group.'
            })
        
        if student.group:
            raise serializers.ValidationError({
                'student_id': 'Student is already booked in another group. Please cancel the existing booking first.'
            })
        
        if group.available_seats <= 0:
            raise serializers.ValidationError({
                'group_id': 'No available seats in this group.'
            })
        
        if not group.can_accept_bookings():
            days_since = group.days_since_start()
            if days_since is not None and days_since >= 10:
                raise serializers.ValidationError({
                    'group_id': f'Cannot book this group. It started {days_since} days ago (10-day limit exceeded).'
                })
        
        return attrs


class AlternativeGroupSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for suggesting alternative groups."""
    speciality_display = serializers.CharField(source='get_speciality_id_display', read_only=True)
    dates_display = serializers.CharField(source='get_dates_display', read_only=True)
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_planned = serializers.BooleanField(read_only=True)
    starting_date = serializers.DateField(read_only=True)
    
    class Meta:
        model = Group
        fields = [
            'id', 'speciality_id', 'speciality_display',
            'dates', 'dates_display', 'time', 'starting_date',
            'seats', 'available_seats', 'is_planned',
            'mentor', 'mentor_name'
        ]
