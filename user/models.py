from typing import TYPE_CHECKING
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from education.models import Group


class UserManager(BaseUserManager):  # type: ignore
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Speciality(models.TextChoices):
    REVIT_ARCHITECTURE = ('revit_architecture', 'Revit Architecture')
    REVIT_STRUCTURE = ('revit_structure', 'Revit Structure')
    TEKLA_STRUCTURE = ('tekla_structure', 'Tekla Structure')


class Role(models.TextChoices):
    DEVELOPER = ('dasturchi', 'Dasturchi')
    DIRECTOR = ('direktor', 'Direktor')
    ADMINISTRATOR = ('administrator', 'Administrator')
    SALES_AGENT = ('sotuv_agenti', 'Sotuv agenti')
    MENTOR = ('mentor', 'Mentor')
    ASSISTANT = ('assistent', 'Assistent')


class Source(models.TextChoices):
    INSTAGRAM = ('instagram', 'Instagram')
    FACEBOOK = ('facebook', 'Facebook')
    TELEGRAM = ('telegram', 'Telegram')


class User(AbstractUser):
    username = None
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        },
    )
    
    objects = UserManager()  # type: ignore
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta(AbstractUser.Meta):  # type: ignore
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Employee(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        verbose_name='User'
    )
    professionality = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Professionality',
        help_text='Professional expertise or specialization'
    )
    full_name = models.CharField(max_length=255, verbose_name='Full Name')
    avatar = models.ImageField(
        upload_to='avatars/employees/',
        null=True,
        blank=True,
        verbose_name='Avatar'
    )
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        verbose_name='Role'
    )

    class Meta:  # type: ignore
        db_table = 'employees'
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        role_display = getattr(self, 'get_role_display', lambda: self.role)()
        return f"{self.full_name} - {role_display}"


class Student(BaseModel):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,13}$',
        message="Telefon raqami '+999999999' formatida kiritilishi kerak. Maksimal 13 raqam."
    )
    inn_regex = RegexValidator(
        regex=r'^\d{1,9}$',
        message="INN faqat raqamlardan iborat bo'lishi kerak va maksimum 9 ta belgi bo'lishi kerak."
    )
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        null=True,
        blank=True,
        verbose_name='User'
    )
    full_name = models.CharField(max_length=255, verbose_name='Full Name')
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        unique=True,
        verbose_name='Phone Number'
    )
    passport_serial_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Passport Serial Number'
    )
    birth_date = models.DateField(verbose_name='Birth Date')
    source = models.CharField(
        max_length=50,
        choices=Source.choices,
        verbose_name='Source'
    )
    group = models.ForeignKey(
        'education.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name='Group'
    )
    certificate = models.FileField(
        upload_to='certificates/',
        null=True,
        blank=True,
        verbose_name='Certificate'
    )
    contract = models.FileField(
        upload_to='contracts/',
        null=True,
        blank=True,
        verbose_name='Contract PDF'
    )
    contract_signed = models.BooleanField(
        default=False,
        verbose_name='Contract Signed',
        help_text='Whether the contract has been electronically signed'
    )
    address = models.TextField(
        null=True,
        blank=True,
        verbose_name='Address',
        help_text='Student full address (tuman, ko\'cha, uy)'
    )
    inn = models.CharField(
        max_length=9,
        null=True,
        blank=True,
        validators=[inn_regex],
        verbose_name='INN',
        help_text='Individual Taxpayer Identification Number (maksimum 9 ta raqam)'
    )
    pinfl = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        verbose_name='PINFL',
        help_text='Personal Identification Number of Physical Person'
    )
                                
    class Meta:  # type: ignore
        db_table = 'students'
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.phone}"
