from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from user.models import BaseModel


class InvoiceStatus(models.TextChoices):
    CREATED = ('created', 'Created')
    PENDING = ('pending', 'Pending Payment')
    PAID = ('paid', 'Paid')
    CANCELLED = ('cancelled', 'Cancelled')
    REFUNDED = ('refunded', 'Refunded')
    EXPIRED = ('expired', 'Expired')


class Invoice(BaseModel):
    """
    Invoice model for student group payments.
    Automatically generated when student books a group.
    """
    student = models.ForeignKey(
        'user.Student',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name='Student'
    )
    group = models.ForeignKey(
        'education.Group',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name='Group'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Amount',
        help_text='Invoice amount in UZS (sum)',
        validators=[MinValueValidator(0.01)]
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.CREATED,
        verbose_name='Status'
    )
    
    # Multicard integration fields
    multicard_uuid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Multicard UUID',
        help_text='Unique transaction ID from Multicard'
    )
    multicard_invoice_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Multicard Invoice ID',
        help_text='Invoice ID sent to Multicard'
    )
    checkout_url = models.URLField(
        null=True,
        blank=True,
        verbose_name='Checkout URL',
        help_text='Payment page URL from Multicard'
    )
    receipt_url = models.URLField(
        null=True,
        blank=True,
        verbose_name='Receipt URL',
        help_text='Payment receipt URL from Multicard'
    )
    
    # Payment details
    payment_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Payment Time',
        help_text='When the payment was completed'
    )
    payment_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Payment Method',
        help_text='Payment system used (uzcard, humo, visa, etc.)'
    )
    card_pan = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='Card PAN',
        help_text='Masked card number'
    )
    
    # Metadata
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name='Notes',
        help_text='Additional notes about the invoice'
    )

    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['group', 'status']),
            models.Index(fields=['multicard_uuid']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Invoice #{self.id} - {self.student.full_name} - {self.amount} UZS"

    @property
    def is_paid(self) -> bool:
        """Check if invoice is paid"""
        return self.status == InvoiceStatus.PAID

    @property
    def can_be_updated(self) -> bool:
        """Check if invoice amount can be updated (only if not paid)"""
        return self.status in [InvoiceStatus.CREATED, InvoiceStatus.PENDING]

    def update_amount(self, new_amount: float) -> bool:
        """
        Update invoice amount if allowed.
        Returns True if updated, False otherwise.
        """
        if not self.can_be_updated:
            return False
        
        self.amount = new_amount
        self.save(update_fields=['amount', 'updated_at'])
        return True
