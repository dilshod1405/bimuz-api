
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0002_initial'),
        ('user', '0003_alter_user_managers_alter_employee_speciality_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='Attendance Date')),
                ('time', models.TimeField(auto_now_add=True, verbose_name='Recorded Time')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='education.group', verbose_name='Group')),
                ('mentor', models.ForeignKey(blank=True, limit_choices_to={'role': 'mentor'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendances', to='user.employee', verbose_name='Mentor')),
                ('participants', models.ManyToManyField(blank=True, related_name='attendances', to='user.student', verbose_name='Participants')),
            ],
            options={
                'verbose_name': 'Attendance',
                'verbose_name_plural': 'Attendances',
                'db_table': 'attendances',
                'ordering': ['-date', '-time'],
                'unique_together': {('group', 'date')},
            },
        ),
    ]
