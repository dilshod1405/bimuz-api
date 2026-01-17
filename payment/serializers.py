from rest_framework import serializers
from payment.models import Invoice, InvoiceStatus


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_phone = serializers.CharField(source='student.phone', read_only=True)
    group_name = serializers.CharField(source='group.__str__', read_only=True)
    status_display = serializers.SerializerMethodField()
    is_paid = serializers.BooleanField(read_only=True)
    
    def get_status_display(self, obj):
        """Return Uzbek translation for status"""
        status_map = {
            'created': 'Yaratilgan',
            'pending': 'To\'lov kutilmoqda',
            'paid': 'To\'langan',
            'cancelled': 'Bekor qilingan',
            'refunded': 'Qaytarilgan',
            'expired': 'Muddati o\'tgan',
        }
        return status_map.get(obj.status, obj.status)

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
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'multicard_uuid',
            'multicard_invoice_id',
            'checkout_url',
            'receipt_url',
            'payment_time',
            'payment_method',
            'card_pan',
            'created_at',
            'updated_at'
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating payment link"""
    invoice_id = serializers.IntegerField(help_text='Invoice ID to pay')
    return_url = serializers.URLField(required=False, help_text='URL to redirect after payment')
    return_error_url = serializers.URLField(required=False, help_text='URL to redirect after error')
    lang = serializers.ChoiceField(
        choices=['ru', 'uz', 'en'],
        default='uz',
        help_text='Payment page language'
    )
    send_sms = serializers.BooleanField(
        default=False,
        help_text='Send invoice link via SMS to student'
    )


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer for Multicard payment callback"""
    store_id = serializers.IntegerField()
    amount = serializers.IntegerField()
    invoice_id = serializers.CharField()
    billing_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_time = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_pan = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ps = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_token = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    uuid = serializers.CharField()
    receipt_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    sign = serializers.CharField()
