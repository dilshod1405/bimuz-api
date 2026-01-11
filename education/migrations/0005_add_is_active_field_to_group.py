
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0004_group_starting_date_alter_attendance_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Automatically set to True when starting_date is reached', verbose_name='Is Active'),
        ),
    ]
