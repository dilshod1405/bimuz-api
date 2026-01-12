from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Group, Dates, Attendance
from user.models import Speciality, Employee


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'get_speciality_display', 'get_dates_display', 'time', 'starting_date', 'get_status_display', 'price_display', 'seats', 'current_students_count_display', 'available_seats_display', 'mentor_link', 'created_at')
    list_filter = ('speciality_id', 'dates', 'starting_date', 'time', 'created_at', 'mentor__role')
    search_fields = ('speciality_id', 'mentor__full_name', 'mentor__user__email', 'mentor__user__first_name', 'mentor__user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'current_students_count_display', 'available_seats_display', 'students_list', 'mentor_link', 'get_status_display')
    ordering = ('-created_at',)
    date_hierarchy = 'starting_date'
    autocomplete_fields = ('mentor',)
    
    fieldsets = (
        (_('Group Information'), {
            'fields': ('speciality_id', 'dates', 'time', 'seats', 'price', 'starting_date')
        }),
        (_('Mentor Assignment'), {
            'fields': ('mentor', 'mentor_link')
        }),
        (_('Status'), {
            'fields': ('get_status_display',),
            'classes': ('collapse',)
        }),
        (_('Statistics'), {
            'fields': ('current_students_count_display', 'available_seats_display', 'students_list'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_display(self, obj):
        if not obj:
            return ''
        if obj.is_planned:
            return mark_safe('<span style="color: #3498db; font-weight: bold;">📅 Planned</span>')
        elif obj.is_active:
            return mark_safe('<span style="color: #2ecc71; font-weight: bold;">✅ Active</span>')
        return mark_safe('<span style="color: #95a5a6;">-</span>')
    get_status_display.short_description = 'Status'
    
    def current_students_count_display(self, obj):
        if not obj:
            return ''
        return str(obj.current_students_count)
    current_students_count_display.short_description = 'Current Students'
    
    def price_display(self, obj):
        """Display price with currency formatting."""
        if not obj:
            return ''
        formatted_price = f"{obj.price:,.2f}"
        return format_html('<strong>{} UZS</strong>', formatted_price)
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'
    
    def get_speciality_display(self, obj):
        if not obj:
            return ''
        speciality_name = dict(Speciality.choices).get(obj.speciality_id, obj.speciality_id)
        colors = {
            'revit_architecture': '#3498db',
            'revit_structure': '#e74c3c',
            'tekla_structure': '#2ecc71',
        }
        color = colors.get(obj.speciality_id, '#95a5a6')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            speciality_name
        )
    get_speciality_display.short_description = 'Speciality'
    
    def get_dates_display(self, obj):
        if not obj:
            return ''
        return dict(Dates.choices).get(obj.dates, obj.dates)
    get_dates_display.short_description = 'Schedule'
    
    def available_seats_display(self, obj):
        if not obj:
            return ''
        available = obj.available_seats
        total = obj.seats
        
        if available == 0:
            color = '#e74c3c'
            status = 'Full'
        elif available <= total * 0.2:
            color = '#f39c12'
            status = 'Almost Full'
        else:
            color = '#2ecc71'
            status = 'Available'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} / {} ({})</span>',
            color,
            available,
            total,
            status
        )
    available_seats_display.short_description = 'Available Seats'
    
    def mentor_link(self, obj):
        if not obj:
            return ''
        if obj.mentor:
            return format_html(
                '<a href="/admin/user/employee/{}/change/">{}</a>',
                obj.mentor.id,
                obj.mentor.full_name
            )
        return mark_safe('<span style="color: #999;">No mentor assigned</span>')
    mentor_link.short_description = 'Mentor'
    
    def students_list(self, obj):
        if not obj:
            return ''
        students = obj.students.all()[:10]
        if not students:
            return mark_safe('<span style="color: #999;">No students yet</span>')
        
        student_links = []
        for student in students:
            student_links.append(
                format_html(
                    '<a href="/admin/user/student/{}/change/">{}</a>',
                    student.id,
                    student.full_name
                )
            )
        
        more_count = obj.current_students_count - len(students)
        if more_count > 0:
            student_links.append(format_html('<em>... and {} more</em>', more_count))
        
        return mark_safe('<br>'.join(str(link) for link in student_links))
    students_list.short_description = 'Students'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('mentor', 'mentor__user').prefetch_related('students')
    
    def save_model(self, request, obj, form, change):
        if obj.mentor and obj.mentor.role != 'mentor':
            self.message_user(
                request,
                'Warning: Selected employee must have Mentor role.',
                level=messages.WARNING
            )
        super().save_model(request, obj, form, change)
    
    actions = ['assign_default_mentor']
    
    @admin.action(description='Assign default mentor to selected groups')
    def assign_default_mentor(self, request, queryset):
        mentor = Employee._default_manager.filter(role='mentor').first()
        if not mentor:
            self.message_user(request, 'No mentors available.', level=messages.ERROR)
            return
        
        updated = queryset.update(mentor=mentor)
        self.message_user(
            request,
            f'Successfully assigned {mentor.full_name} to {updated} group(s).',
            level=messages.SUCCESS
        )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'group_link', 'date', 'time', 'participants_count', 'mentor_link', 'created_at')
    list_filter = ('date', 'group', 'group__speciality_id', 'mentor', 'created_at')
    search_fields = ('group__speciality_id', 'mentor__full_name', 'mentor__user__email', 'participants__full_name')
    readonly_fields = ('created_at', 'updated_at', 'time', 'participants_list')
    ordering = ('-date', '-time')
    date_hierarchy = 'date'
    autocomplete_fields = ('group', 'mentor')
    filter_horizontal = ('participants',)
    
    fieldsets = (
        (_('Attendance Information'), {
            'fields': ('group', 'date', 'time', 'mentor')
        }),
        (_('Participants'), {
            'fields': ('participants', 'participants_list')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        
        base_fields = getattr(form, 'base_fields', {})
        if obj and obj.group and 'participants' in base_fields:
            base_fields['participants'].queryset = obj.group.students.all()
        elif 'participants' in base_fields:
            base_fields['participants'].queryset = base_fields['participants'].queryset.none()
        
        return form
    
    def group_link(self, obj):
        if not obj:
            return ''
        if obj.group:
            return format_html(
                '<a href="/admin/education/group/{}/change/">{}</a>',
                obj.group.id,
                str(obj.group)
            )
        return mark_safe('<span style="color: #999;">No group</span>')
    group_link.short_description = 'Group'
    
    def mentor_link(self, obj):
        if not obj:
            return ''
        if obj.mentor:
            return format_html(
                '<a href="/admin/user/employee/{}/change/">{}</a>',
                obj.mentor.id,
                obj.mentor.full_name
            )
        return mark_safe('<span style="color: #999;">No mentor assigned</span>')
    mentor_link.short_description = 'Mentor'
    
    def participants_count(self, obj):
        if not obj:
            return ''
        count = obj.participants.count() if obj.pk else 0
        total = obj.group.current_students_count if obj and obj.group else 0
        
        if count == 0:
            color = '#e74c3c'
        elif count < total * 0.5:
            color = '#f39c12'
        else:
            color = '#2ecc71'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} / {}</span>',
            color,
            count,
            total
        )
    participants_count.short_description = 'Participants'
    
    def participants_list(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span style="color: #999;">Save attendance first to see participants</span>')
        
        participants = obj.participants.all()
        if not participants:
            return mark_safe('<span style="color: #999;">No participants yet</span>')
        
        participant_links = []
        for participant in participants:
            participant_links.append(
                format_html(
                    '<a href="/admin/user/student/{}/change/">{}</a>',
                    participant.id,
                    participant.full_name
                )
            )
        
        return mark_safe('<br>'.join(str(link) for link in participant_links))
    participants_list.short_description = 'Participants List'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('group', 'group__mentor', 'group__mentor__user', 'mentor', 'mentor__user').prefetch_related('participants')
    
    def save_model(self, request, obj, form, change):
        if obj.mentor and obj.mentor.role != 'mentor':
            self.message_user(
                request,
                'Warning: Selected employee must have Mentor role.',
                level=messages.WARNING
            )
        
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        
        obj = form.instance
        if obj.pk and obj.group and hasattr(obj, 'participants'):
            group_students = obj.group.students.all()
            participants = obj.participants.all()
            invalid_participants = participants.exclude(id__in=group_students.values_list('id', flat=True))
            
            if invalid_participants.exists():
                invalid_names = ', '.join([p.full_name for p in invalid_participants])
                self.message_user(
                    request,
                    f'Warning: The following participants are not members of this group and were removed: {invalid_names}',
                    level=messages.WARNING
                )
                obj.participants.remove(*invalid_participants)
