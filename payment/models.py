from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from user.models import BaseModel
from user.models import Employee
from django.utils import timezone


class InvoiceStatus(models.TextChoices):
    CREATED = 'created', _('Yaratilgan')
    PENDING = 'pending', _('Kutilmoqda')
    PAID = 'paid', _('To\'langan')
    CANCELLED = 'cancelled', _('Bekor qilingan')


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
        help_text='Payment method used (e.g., uzcard, humo, visa, etc.)'
    )
    card_pan = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Card PAN',
        help_text='Last 4 digits of the card used for payment'
    )

    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['payment_time']),
        ]

    def __str__(self):
        return f"Invoice #{self.id} - {self.student.full_name} - {self.amount} so'm"

    @property
    def is_paid(self):
        return self.status == InvoiceStatus.PAID

    @property
    def status_display(self):
        return self.get_status_display()


class EmployeeSalary(BaseModel):
    """
    Employee salary for a specific month.
    Used for tracking salaries of non-mentor employees.
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='salaries',
        verbose_name='Employee'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Amount',
        help_text='Salary amount in UZS (sum)',
        validators=[MinValueValidator(0)]
    )
    month = models.CharField(
        max_length=7,
        verbose_name='Month',
        help_text='Month in YYYY-MM format (e.g., 2025-01)'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notes',
        help_text='Additional notes about the salary'
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name='Is Paid',
        help_text='Whether the salary has been paid'
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Payment Date',
        help_text='Date when the salary was paid'
    )

    class Meta:
        db_table = 'employee_salaries'
        verbose_name = 'Employee Salary'
        verbose_name_plural = 'Employee Salaries'
        ordering = ['-month', '-created_at']
        unique_together = [['employee', 'month']]
        indexes = [
            models.Index(fields=['month']),
            models.Index(fields=['employee', 'month']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.month} - {self.amount} so'm"


class MentorPayment(BaseModel):
    """
    Mentor payment for a specific month.
    Tracks mentor earnings payments.
    """
    mentor = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='mentor_payments',
        limit_choices_to={'role': 'mentor'},
        verbose_name='Mentor'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Amount',
        help_text='Payment amount in UZS (sum)',
        validators=[MinValueValidator(0)]
    )
    month = models.CharField(
        max_length=7,
        verbose_name='Month',
        help_text='Month in YYYY-MM format (e.g., 2025-01)'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notes',
        help_text='Additional notes about the payment'
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name='Is Paid',
        help_text='Whether the payment has been made'
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Payment Date',
        help_text='Date when the payment was made'
    )

    class Meta:
        db_table = 'mentor_payments'
        verbose_name = 'Mentor Payment'
        verbose_name_plural = 'Mentor Payments'
        ordering = ['-month', '-created_at']
        unique_together = [['mentor', 'month']]
        indexes = [
            models.Index(fields=['month']),
            models.Index(fields=['mentor', 'month']),
        ]

    def __str__(self):
        return f"{self.mentor.full_name} - {self.month} - {self.amount} so'm"
