from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from payment.models import Invoice, InvoiceStatus


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Professional admin interface for Invoice model.
    Provides comprehensive management of student invoices and payments.
    """
    list_display = [
        'id',
        'student_link',
        'group_link',
        'amount_display',
        'status_badge',
        'is_paid_badge',
        'multicard_uuid_short',
        'payment_time',
        'created_at'
    ]
    list_filter = [
        'status',
        'created_at',
        'payment_time',
        'payment_method'
    ]
    search_fields = [
        'student__full_name',
        'student__phone',
        'group__speciality_id',
        'multicard_uuid',
        'multicard_invoice_id',
        'id'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'multicard_uuid',
        'multicard_invoice_id',
        'checkout_url_link',
        'receipt_url_link',
        'payment_time',
        'is_paid_display'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'group', 'amount', 'status', 'notes'),
            'description': 'Core invoice information including student, group, and amount.'
        }),
        ('Payment Status', {
            'fields': ('is_paid_display',),
            'description': 'Current payment status of the invoice.'
        }),
        ('Multicard Integration', {
            'fields': (
                'multicard_uuid',
                'multicard_invoice_id',
                'checkout_url_link',
                'receipt_url_link'
            ),
            'description': 'Multicard payment gateway integration details.'
        }),
        ('Payment Details', {
            'fields': (
                'payment_time',
                'payment_method',
                'card_pan'
            ),
            'description': 'Payment transaction details (populated after successful payment).'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 25
    list_max_show_all = 100
    
    actions = ['mark_as_paid', 'mark_as_cancelled', 'export_invoices']

    def student_link(self, obj):
        """Display student name as a link to student admin page."""
        if obj.student:
            url = reverse('admin:user_student_change', args=[obj.student.pk])
            return format_html('<a href="{}">{}</a>', url, obj.student.full_name)
        return '-'
    student_link.short_description = 'Student'
    student_link.admin_order_field = 'student__full_name'

    def group_link(self, obj):
        """Display group name as a link to group admin page."""
        if obj.group:
            url = reverse('admin:education_group_change', args=[obj.group.pk])
            return format_html('<a href="{}">{}</a>', url, str(obj.group))
        return '-'
    group_link.short_description = 'Group'
    group_link.admin_order_field = 'group__speciality_id'

    def amount_display(self, obj):
        """Display amount with currency formatting."""
        if not obj:
            return ''
        formatted_amount = f"{obj.amount:,.2f}"
        return format_html('<strong>{} UZS</strong>', formatted_amount)
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            InvoiceStatus.CREATED: '#6c757d',      # Gray
            InvoiceStatus.PENDING: '#ffc107',     # Yellow
            InvoiceStatus.PAID: '#28a745',        # Green
            InvoiceStatus.CANCELLED: '#dc3545',   # Red
            InvoiceStatus.REFUNDED: '#17a2b8',    # Blue
            InvoiceStatus.EXPIRED: '#6c757d',     # Gray
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def is_paid_badge(self, obj):
        """Display paid status with badge."""
        if obj.is_paid:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">✓ PAID</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">PENDING</span>'
        )
    is_paid_badge.short_description = 'Payment'
    is_paid_badge.boolean = False

    def multicard_uuid_short(self, obj):
        """Display shortened Multicard UUID."""
        if obj.multicard_uuid:
            short_uuid = str(obj.multicard_uuid)[:8] + '...'
            return format_html('<code>{}</code>', short_uuid)
        return '-'
    multicard_uuid_short.short_description = 'Multicard UUID'

    def checkout_url_link(self, obj):
        """Display checkout URL as clickable link."""
        if obj.checkout_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.checkout_url,
                'Open Payment Page'
            )
        return '-'
    checkout_url_link.short_description = 'Checkout URL'

    def receipt_url_link(self, obj):
        """Display receipt URL as clickable link."""
        if obj.receipt_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.receipt_url,
                'View Receipt'
            )
        return '-'
    receipt_url_link.short_description = 'Receipt URL'

    def is_paid_display(self, obj):
        """Display paid status in detail view."""
        return obj.is_paid
    is_paid_display.boolean = True
    is_paid_display.short_description = 'Is Paid'

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('student', 'group', 'student__user')

    def mark_as_paid(self, request, queryset):
        """Admin action to mark selected invoices as paid."""
        count = queryset.update(status=InvoiceStatus.PAID)
        self.message_user(
            request,
            f'{count} invoice(s) marked as paid.',
            level='success'
        )
    mark_as_paid.short_description = 'Mark selected invoices as paid'

    def mark_as_cancelled(self, request, queryset):
        """Admin action to cancel selected invoices."""
        count = queryset.filter(status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING]).update(
            status=InvoiceStatus.CANCELLED
        )
        self.message_user(
            request,
            f'{count} invoice(s) cancelled.',
            level='success'
        )
    mark_as_cancelled.short_description = 'Cancel selected invoices'

    def export_invoices(self, request, queryset):
        """Admin action placeholder for exporting invoices."""
        # TODO: Implement CSV/Excel export functionality
        self.message_user(
            request,
            'Export functionality will be implemented soon.',
            level='info'
        )
    export_invoices.short_description = 'Export selected invoices'

    class Media:
        """Add custom CSS for better admin interface."""
        css = {
            'all': ('admin/css/invoice_admin.css',)
        }