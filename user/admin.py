from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _

from .models import User, Employee, Student, Speciality, Role, Source


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    
    list_display = ('full_name', 'user', 'get_role_display', 'get_speciality_display_conditional', 'avatar_preview', 'created_at')
    list_filter = ('role', 'speciality_id', 'created_at', 'updated_at')
    search_fields = ('full_name', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'avatar_preview')
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'full_name', 'avatar', 'avatar_preview')
        }),
        (_('Professional Information'), {
            'fields': ('role', 'speciality_id')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if obj and obj.role != 'mentor':
            for fieldset in fieldsets:
                if fieldset[0] == _('Professional Information'):
                    fields = list(fieldset[1]['fields'])
                    if 'speciality_id' in fields:
                        fields.remove('speciality_id')
                    fieldset[1]['fields'] = tuple(fields)
        
        return fieldsets
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        if 'speciality_id' in form.base_fields:
            form.base_fields['speciality_id'].help_text = 'Required only for Mentors'
            form.base_fields['speciality_id'].required = False
        
        return form
    
    class Media:
        js = ('admin/js/employee_admin.js',)
    
    def avatar_preview(self, obj):
        if not obj:
            return '-'
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url
            )
        return mark_safe('<span style="color: #999;">No avatar</span>')
    avatar_preview.short_description = 'Avatar Preview'  # type: ignore
    
    def get_role_display(self, obj):
        if not obj:
            return ''
        return dict(Role.choices).get(obj.role, obj.role)
    get_role_display.short_description = 'Role'  # type: ignore
    
    def get_speciality_display(self, obj):
        if not obj:
            return ''
        return dict(Speciality.choices).get(obj.speciality_id, obj.speciality_id)
    get_speciality_display.short_description = 'Speciality'  # type: ignore
    
    def get_speciality_display_conditional(self, obj):
        if not obj:
            return ''
        if obj.role != 'mentor':
            return mark_safe('<span style="color: #999;">-</span>')
        if obj.speciality_id:
            return dict(Speciality.choices).get(obj.speciality_id, obj.speciality_id)
        return mark_safe('<span style="color: #e74c3c;">Required</span>')
    get_speciality_display_conditional.short_description = 'Speciality'  # type: ignore


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    
    list_display = ('full_name', 'phone', 'passport_serial_number', 'birth_date', 'get_source_display', 'group_link', 'certificate_link', 'created_at')
    list_filter = ('source', 'birth_date', 'created_at', 'updated_at', 'group')
    search_fields = ('full_name', 'phone', 'passport_serial_number')
    readonly_fields = ('created_at', 'updated_at', 'certificate_link')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('group',)
    
    fieldsets = (
        (_('Personal Information'), {
            'fields': ('full_name', 'phone', 'passport_serial_number', 'birth_date')
        }),
        (_('Academic Information'), {
            'fields': ('group', 'certificate', 'certificate_link', 'source')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_source_display(self, obj):
        if not obj:
            return ''
        return dict(Source.choices).get(obj.source, obj.source)
    get_source_display.short_description = 'Source'  # type: ignore
    
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
    group_link.short_description = 'Group'  # type: ignore
    
    def certificate_link(self, obj):
        if not obj:
            return ''
        if obj.certificate:
            return format_html(
                '<a href="{}" target="_blank">Download Certificate</a>',
                obj.certificate.url
            )
        return mark_safe('<span style="color: #999;">No certificate</span>')
    certificate_link.short_description = 'Certificate'  # type: ignore
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('group')
