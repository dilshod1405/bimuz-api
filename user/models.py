from typing import TYPE_CHECKING
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from education.models import Group


class UserManager(BaseUserManager):
    
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
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta(AbstractUser.Meta):
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

    class Meta:
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
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
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

    class Meta:
        db_table = 'students'
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.phone}"
