from typing import TYPE_CHECKING
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date
from user.models import BaseModel, Speciality

if TYPE_CHECKING:
    from user.models import Employee, Student


def default_attendance_date():
    return timezone.now().date()


class Dates(models.TextChoices):
    MON_WED_FRI = ('mon_wed_fri', 'Monday - Wednesday - Friday')  # type: ignore
    TUE_THU_SAT = ('tue_thu_sat', 'Tuesday - Thursday - Saturday')  # type: ignore


class Group(BaseModel):
    speciality_id = models.CharField(
        max_length=50,
        choices=Speciality.choices,
        verbose_name='Speciality'
    )
    dates = models.CharField(
        max_length=50,
        choices=Dates.choices,
        verbose_name='Dates'
    )
    time = models.TimeField(
        verbose_name='Lesson Time',
        help_text='Daily lesson time (e.g., 14:00)'
    )
    starting_date = models.DateField(
        verbose_name='Starting Date',
        help_text='Date when the group course starts (for planned groups)',
        null=True,
        blank=True
    )
    seats = models.PositiveIntegerField(
        verbose_name='Maximum Students'
    )
    mentor = models.ForeignKey(  # type: ignore
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        limit_choices_to={'role': 'mentor'},
        verbose_name='Mentor'
    )

    class Meta:  # type: ignore
        db_table = 'groups'
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'
        ordering = ['-created_at']

    def __str__(self):
        speciality_display = getattr(self, 'get_speciality_id_display', lambda: self.speciality_id)()
        dates_display = getattr(self, 'get_dates_display', lambda: self.dates)()
        return f"{speciality_display} - {dates_display}"

    def clean(self):
        if self.mentor and hasattr(self.mentor, 'role') and self.mentor.role != 'mentor':  # type: ignore
            raise ValidationError({
                'mentor': 'Selected employee must have Mentor role.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def current_students_count(self) -> int:
        if hasattr(self, 'students'):
            return self.students.count()  # type: ignore
        return 0

    @property
    def available_seats(self) -> int:
        seats_value: int = getattr(self, 'seats', 0) or 0  # type: ignore
        return max(0, seats_value - self.current_students_count)
    
    @property
    def is_planned(self) -> bool:
        if not self.starting_date:
            return False
        from django.utils import timezone
        return self.starting_date > timezone.now().date()
    
    @property
    def is_active(self) -> bool:
        if not self.starting_date:
            return True
        from django.utils import timezone
        return self.starting_date <= timezone.now().date()


class Attendance(BaseModel):
    group = models.ForeignKey(  # type: ignore
        'education.Group',
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Group'
    )
    date = models.DateField(
        verbose_name='Attendance Date',
        default=default_attendance_date
    )
    time = models.TimeField(
        auto_now_add=True,
        verbose_name='Recorded Time'
    )
    participants = models.ManyToManyField(  # type: ignore
        'user.Student',
        related_name='attendances',
        verbose_name='Participants',
        blank=True
    )
    mentor = models.ForeignKey(  # type: ignore
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendances',
        limit_choices_to={'role': 'mentor'},
        verbose_name='Mentor'
    )

    class Meta:  # type: ignore
        db_table = 'attendances'
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'
        ordering = ['-date', '-time']
        unique_together = [['group', 'date']]

    def clean(self):
        if self.mentor and hasattr(self.mentor, 'role') and self.mentor.role != 'mentor':  # type: ignore
            raise ValidationError({
                'mentor': 'Selected employee must have Mentor role.'
            })
        
        if self.pk and hasattr(self, 'participants'):
            participants = self.participants.all()  # type: ignore
            if hasattr(self.group, 'students'):
                group_students = self.group.students.all()  # type: ignore
                invalid_participants = participants.exclude(id__in=group_students.values_list('id', flat=True))
                if invalid_participants.exists():
                    raise ValidationError({
                        'participants': 'All participants must be members of the selected group.'
                    })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        group_str = str(self.group)
        date_str = self.date.strftime('%Y-%m-%d')  # type: ignore
        if self.pk and hasattr(self, 'participants'):
            participants_count = self.participants.count()  # type: ignore
        else:
            participants_count = 0
        return f"{group_str} - {date_str} ({participants_count} participants)"
