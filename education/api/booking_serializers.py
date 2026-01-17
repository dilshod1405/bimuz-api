from rest_framework import serializers
from education.models import Group
from user.models import Student, Speciality


class GroupBookingSerializer(serializers.ModelSerializer):
    """Serializer for group booking with availability info."""
    speciality_display = serializers.SerializerMethodField()
    dates_display = serializers.SerializerMethodField()
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    current_students_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_planned = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    can_accept_bookings = serializers.BooleanField(read_only=True)
    days_since_start = serializers.IntegerField(read_only=True, allow_null=True)
    
    def get_speciality_display(self, obj):
        """Return Uzbek translation for speciality"""
        speciality_map = {
            'revit_architecture': 'Revit Architecture',
            'revit_structure': 'Revit Structure',
            'tekla_structure': 'Tekla Structure',
        }
        return speciality_map.get(obj.speciality_id, obj.speciality_id)
    
    def get_dates_display(self, obj):
        """Return Uzbek translation for dates"""
        dates_map = {
            'mon_wed_fri': 'Dushanba - Chorshanba - Juma',
            'tue_thu_sat': 'Seshanba - Payshanba - Shanba',
        }
        return dates_map.get(obj.dates, obj.dates)
    
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
            raise serializers.ValidationError('Talaba topilmadi.')
        return value
    
    def validate_group_id(self, value):
        try:
            group = Group._default_manager.get(id=value)
        except Group.DoesNotExist:
            raise serializers.ValidationError('Guruh topilmadi.')
        return value
    
    def validate(self, attrs):
        student_id = attrs.get('student_id')
        group_id = attrs.get('group_id')
        
        student = Student._default_manager.get(id=student_id)
        group = Group._default_manager.get(id=group_id)
        
        if student.group and student.group.id == group_id:
            raise serializers.ValidationError({
                'group_id': 'Talaba allaqachon bu guruhga yozilgan.'
            })
        
        if student.group:
            raise serializers.ValidationError({
                'student_id': 'Talaba boshqa guruhga yozilgan. Avval mavjud yozilishni bekor qiling.'
            })
        
        if group.available_seats <= 0:
            raise serializers.ValidationError({
                'group_id': 'Bu guruhda bo\'sh o\'rin yo\'q.'
            })
        
        if not group.can_accept_bookings():
            days_since = group.days_since_start()
            if days_since is not None and days_since >= 10:
                raise serializers.ValidationError({
                    'group_id': f'Bu guruhga yozilish mumkin emas. Guruh {days_since} kun oldin boshlangan (10 kunlik cheklov oshib ketgan).'
                })
        
        return attrs


class AlternativeGroupSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for suggesting alternative groups."""
    speciality_display = serializers.SerializerMethodField()
    dates_display = serializers.SerializerMethodField()
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_planned = serializers.BooleanField(read_only=True)
    starting_date = serializers.DateField(read_only=True)
    
    def get_speciality_display(self, obj):
        """Return Uzbek translation for speciality"""
        speciality_map = {
            'revit_architecture': 'Revit Architecture',
            'revit_structure': 'Revit Structure',
            'tekla_structure': 'Tekla Structure',
        }
        return speciality_map.get(obj.speciality_id, obj.speciality_id)
    
    def get_dates_display(self, obj):
        """Return Uzbek translation for dates"""
        dates_map = {
            'mon_wed_fri': 'Dushanba - Chorshanba - Juma',
            'tue_thu_sat': 'Seshanba - Payshanba - Shanba',
        }
        return dates_map.get(obj.dates, obj.dates)
    
    class Meta:
        model = Group
        fields = [
            'id', 'speciality_id', 'speciality_display',
            'dates', 'dates_display', 'time', 'starting_date',
            'seats', 'available_seats', 'is_planned',
            'mentor', 'mentor_name'
        ]
