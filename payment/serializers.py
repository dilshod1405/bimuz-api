from rest_framework import serializers
from decimal import Decimal

from payment.models import Invoice, InvoiceStatus
from user.models import Student


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Invoice model.
    """
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_phone = serializers.CharField(source='student.phone', read_only=True)
    group_name = serializers.CharField(source='group.__str__', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'student',
            'student_name',
            'student_phone',
            'group',
            'group_name',
            'amount',
            'status',
            'status_display',
            'is_paid',
            'multicard_uuid',
            'multicard_invoice_id',
            'checkout_url',
            'receipt_url',
            'payment_time',
            'payment_method',
            'card_pan',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'multicard_uuid',
            'multicard_invoice_id',
            'checkout_url',
            'receipt_url',
            'payment_time',
            'payment_method',
            'card_pan',
            'created_at',
            'updated_at',
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """
    Serializer for creating payment link.
    """
    invoice_id = serializers.IntegerField()
    lang = serializers.CharField(default='uz', required=False)
    return_url = serializers.URLField(required=False)
    return_error_url = serializers.URLField(required=False)
    send_sms = serializers.BooleanField(default=False, required=False)


class PaymentCallbackSerializer(serializers.Serializer):
    """
    Serializer for Multicard payment callback.
    """
    uuid = serializers.CharField()
    invoice_id = serializers.CharField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    payment_time = serializers.CharField(required=False)
    receipt_url = serializers.URLField(required=False)
    payment_method = serializers.CharField(required=False)
    card_pan = serializers.CharField(required=False)


class MarkInvoicesAsPaidSerializer(serializers.Serializer):
    """
    Serializer for marking invoices as paid manually by accountant.
    """
    invoice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of invoice IDs to mark as paid"
    )
    payment_time = serializers.DateTimeField(
        required=False,
        help_text="Payment time (defaults to now if not provided)"
    )
    payment_method = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Payment method (e.g., cash, bank_transfer, etc.)"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional notes about the payment"
    )

    def validate_invoice_ids(self, value):
        """Validate that invoice IDs exist and are not already paid"""
        if not value:
            raise serializers.ValidationError("At least one invoice ID is required")
        
        invoices = Invoice.objects.filter(id__in=value)
        found_ids = set(invoices.values_list('id', flat=True))
        missing_ids = set(value) - found_ids
        
        if missing_ids:
            raise serializers.ValidationError(
                f"Invoices not found: {list(missing_ids)}"
            )
        
        already_paid = invoices.filter(status=InvoiceStatus.PAID)
        if already_paid.exists():
            paid_ids = list(already_paid.values_list('id', flat=True))
            raise serializers.ValidationError(
                f"Some invoices are already paid: {paid_ids}"
            )
        
        return value
