from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _

from .models import User, Employee, Student, Role, Source


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    
    list_display = ('id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
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
    
    list_display = ('id', 'full_name', 'user', 'get_role_display', 'professionality', 'avatar_preview', 'created_at')
    list_filter = ('role', 'professionality', 'created_at', 'updated_at')
    search_fields = ('full_name', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'avatar_preview')
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'full_name', 'avatar', 'avatar_preview')
        }),
        (_('Professional Information'), {
            'fields': ('role', 'professionality')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def avatar_preview(self, obj):
        if not obj:
            return '-'
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url
            )
        return mark_safe('<span style="color: #999;">No avatar</span>')
    avatar_preview.short_description = 'Avatar Preview'
    
    def get_role_display(self, obj):
        if not obj:
            return ''
        return dict(Role.choices).get(obj.role, obj.role)
    get_role_display.short_description = 'Role'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """
    Professional admin interface for Student model.
    Manages student information, bookings (group assignments), contracts, and certificates.
    """
    list_display = (
        'id',
        'full_name',
        'phone',
        'passport_serial_number',
        'birth_date',
        'address',
        'inn',
        'pinfl',
        'get_source_display',
        'group_link',
        'contract_status',
        'certificate_link',
        'created_at'
    )
    list_filter = (
        'source',
        'birth_date',
        'created_at',
        'updated_at',
        'group',
        'contract_signed'
    )
    search_fields = ('full_name', 'phone', 'passport_serial_number', 'inn', 'pinfl', 'address')
    readonly_fields = (
        'created_at',
        'updated_at',
        'certificate_link',
        'contract_link',
        'booking_status'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('group',)
    
    fieldsets = (
        (_('Personal Information'), {
            'fields': ('full_name', 'phone', 'passport_serial_number', 'birth_date', 'source')
        }),
        (_('Address and Requisites'), {
            'fields': ('address', 'inn', 'pinfl'),
            'description': 'Student address and identification numbers required for contract generation.'
        }),
        (_('Booking Information'), {
            'fields': ('group', 'booking_status'),
            'description': 'Group assignment represents the student\'s booking. When a student is assigned to a group, an invoice is automatically generated.'
        }),
        (_('Contract Information'), {
            'fields': ('contract', 'contract_link', 'contract_signed'),
            'description': 'Contract PDF file and signing status. Contract is generated when student books a group.'
        }),
        (_('Certificate Information'), {
            'fields': ('certificate', 'certificate_link'),
            'description': 'Student certificate file (uploaded after course completion).'
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
    get_source_display.short_description = 'Source'
    
    def group_link(self, obj):
        """Display group as a clickable link (represents booking)."""
        if not obj:
            return ''
        if obj.group:
            return format_html(
                '<a href="/admin/education/group/{}/change/">{}</a>',
                obj.group.id,
                str(obj.group)
            )
        return mark_safe('<span style="color: #999;">No booking</span>')
    group_link.short_description = 'Booking (Group)'
    
    def booking_status(self, obj):
        """Display booking status with visual indicator."""
        if not obj:
            return ''
        if obj.group:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">✓ BOOKED</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">NOT BOOKED</span>'
        )
    booking_status.short_description = 'Booking Status'
    booking_status.boolean = False
    
    def contract_status(self, obj):
        """Display contract status in list view."""
        if not obj:
            return ''
        if obj.contract_signed:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">✓ SIGNED</span>'
            )
        elif obj.contract:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">PENDING</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">NO CONTRACT</span>'
        )
    contract_status.short_description = 'Contract'
    contract_status.boolean = False
    
    def contract_link(self, obj):
        """Display contract PDF as clickable link."""
        if not obj:
            return ''
        if obj.contract:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">📄 View Contract PDF</a>',
                obj.contract.url
            )
        return mark_safe('<span style="color: #999;">No contract uploaded</span>')
    contract_link.short_description = 'Contract File'
    
    def certificate_link(self, obj):
        """Display certificate as clickable link."""
        if not obj:
            return ''
        if obj.certificate:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">📜 Download Certificate</a>',
                obj.certificate.url
            )
        return mark_safe('<span style="color: #999;">No certificate uploaded</span>')
    certificate_link.short_description = 'Certificate File'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('group', 'user')
