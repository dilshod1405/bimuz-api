from typing import TYPE_CHECKING
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import date, timedelta
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
    is_active = models.BooleanField(
        default=True,  # type: ignore
        verbose_name='Is Active',
        help_text='Automatically set to True when starting_date is reached'
    )
    seats = models.PositiveIntegerField(
        verbose_name='Maximum Students'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Price',
        help_text='Group price in UZS (sum)',
        default=0.00
    )
    total_lessons = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Total Lessons',
        help_text='Total number of lessons in this group (e.g., 72 lessons). Used for lesson-based payment milestones.',
        validators=[MinValueValidator(1)]
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
                'mentor': 'Tanlangan xodim Mentor roliga ega bo\'lishi kerak.'
            })

    def calculate_finish_date(self) -> date | None:
        """
        Calculate finish date based on starting_date, total_lessons, and lesson schedule.
        Returns None if starting_date or total_lessons is not set.
        
        The calculation counts forward from starting_date, only counting days that match
        the lesson schedule (e.g., Mon/Wed/Fri or Tue/Thu/Sat).
        """
        if not self.starting_date or not self.total_lessons:
            return None
        
        # Determine lesson weekdays based on schedule
        if self.dates == Dates.MON_WED_FRI:
            lesson_weekdays = [0, 2, 4]  # Monday, Wednesday, Friday
        elif self.dates == Dates.TUE_THU_SAT:
            lesson_weekdays = [1, 3, 5]  # Tuesday, Thursday, Saturday
        else:
            return None
        
        # Start from starting_date
        current_date = self.starting_date
        lessons_counted = 1  # Starting date is the first lesson
        
        # Count forward until we reach total_lessons
        while lessons_counted < self.total_lessons:
            # Move to next day
            current_date += timedelta(days=1)
            
            # Check if this day is a lesson day
            if current_date.weekday() in lesson_weekdays:
                lessons_counted += 1
        
        return current_date
    
    @property
    def finish_date(self) -> date | None:
        """Get the calculated finish date for the group."""
        return self.calculate_finish_date()
    
    def save(self, *args, **kwargs):
        if self.starting_date:
            from django.utils import timezone
            if self.starting_date <= timezone.now().date():
                self.is_active = True
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
    
    def can_accept_bookings(self) -> bool:
        """
        Check if group can accept new bookings based on 10-day rule.
        - If group hasn't started (planned): can accept bookings
        - If group has started: can accept only if less than 10 days have passed
        - If no starting_date: can accept bookings
        """
        if not self.starting_date:
            return True
        
        today = timezone.now().date()
        
        if self.starting_date > today:
            return True
        
        days_since_start = (today - self.starting_date).days  # type: ignore
        return days_since_start < 10
    
    def days_since_start(self) -> int | None:
        """Return number of days since group started, or None if not started yet."""
        if not self.starting_date:
            return None
        
        today = timezone.now().date()
        if self.starting_date > today:
            return None
        
        return (today - self.starting_date).days  # type: ignore
    
    def get_current_lesson_number(self) -> int:
        """
        Get the current lesson number based on attendance records.
        Each attendance record represents one lesson.
        Returns 0 if no lessons have been conducted yet.
        """
        if not self.pk:
            return 0
        return self.attendances.count()  # type: ignore
    
    def get_midpoint_lesson(self) -> int | None:
        """
        Get the midpoint lesson number (where first installment payment is required).
        Returns None if total_lessons is not set.
        """
        if not self.total_lessons:
            return None
        return self.total_lessons // 2
    
    def get_final_lesson(self) -> int | None:
        """
        Get the final lesson number (where second installment payment is required).
        Returns None if total_lessons is not set.
        """
        return self.total_lessons


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
                'mentor': 'Tanlangan xodim Mentor roliga ega bo\'lishi kerak.'
            })
        
        if self.pk and hasattr(self, 'participants'):
            participants = self.participants.all()  # type: ignore
            if hasattr(self.group, 'students'):
                group_students = self.group.students.all()  # type: ignore
                invalid_participants = participants.exclude(id__in=group_students.values_list('id', flat=True))
                if invalid_participants.exists():
                    raise ValidationError({
                        'participants': 'Barcha ishtirokchilar tanlangan guruhning a\'zosi bo\'lishi kerak.'
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
