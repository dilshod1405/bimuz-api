from rest_framework import serializers
from education.models import Group, Attendance, Dates
from user.models import Speciality, Employee, Student


class GroupSerializer(serializers.ModelSerializer):
    speciality_display = serializers.CharField(source='get_speciality_id_display', read_only=True)
    dates_display = serializers.CharField(source='get_dates_display', read_only=True)
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    current_students_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_planned = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Group
        fields = [
            'id', 'speciality_id', 'speciality_display',
            'dates', 'dates_display', 'time', 'starting_date',
            'seats', 'current_students_count', 'available_seats',
            'is_planned', 'is_active',
            'mentor', 'mentor_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_mentor(self, value):
        if value and value.role != 'mentor':
            raise serializers.ValidationError('Selected employee must have Mentor role.')
        return value


class GroupCreateSerializer(GroupSerializer):
    class Meta(GroupSerializer.Meta):
        pass


class GroupUpdateSerializer(GroupSerializer):
    class Meta(GroupSerializer.Meta):
        pass


class AttendanceParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'full_name', 'phone']


class AttendanceSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.__str__', read_only=True)
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    participants_count = serializers.SerializerMethodField()
    participants_list = AttendanceParticipantSerializer(source='participants', many=True, read_only=True)
    participants = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Student._default_manager.all(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'group', 'group_name', 'date', 'time',
            'mentor', 'mentor_name', 'participants',
            'participants_count', 'participants_list',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'time', 'created_at', 'updated_at']
    
    def get_participants_count(self, obj):
        if obj.pk and hasattr(obj, 'participants'):
            return obj.participants.count()
        return 0
    
    def validate_mentor(self, value):
        if value and value.role != 'mentor':
            raise serializers.ValidationError('Selected employee must have Mentor role.')
        return value
    
    def validate(self, attrs):
        group = attrs.get('group') or (self.instance.group if self.instance else None)
        participants = attrs.get('participants', [])
        
        if group and participants:
            group_students = group.students.all()
            group_student_ids = set(group_students.values_list('id', flat=True))
            participant_ids = {p.id if hasattr(p, 'id') else p for p in participants}
            
            invalid_participants = participant_ids - group_student_ids
            if invalid_participants:
                raise serializers.ValidationError({
                    'participants': 'All participants must be members of the selected group.'
                })
        
        return attrs
    
    def create(self, validated_data):
        participants = validated_data.pop('participants', [])
        attendance = Attendance._default_manager.create(**validated_data)
        
        if participants:
            attendance.participants.set(participants)
        
        return attendance
    
    def update(self, instance, validated_data):
        participants = validated_data.pop('participants', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        if participants is not None:
            instance.participants.set(participants)
        
        return instance
