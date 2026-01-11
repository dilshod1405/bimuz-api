
import education.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0003_attendance'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='starting_date',
            field=models.DateField(blank=True, help_text='Date when the group course starts (for planned groups)', null=True, verbose_name='Starting Date'),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='date',
            field=models.DateField(default=education.models.default_attendance_date, verbose_name='Attendance Date'),
        ),
        migrations.AlterField(
            model_name='group',
            name='time',
            field=models.TimeField(help_text='Daily lesson time (e.g., 14:00)', verbose_name='Lesson Time'),
        ),
    ]
