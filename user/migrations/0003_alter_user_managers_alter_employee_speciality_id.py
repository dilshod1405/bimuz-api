
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_remove_user_username_alter_user_email'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
            ],
        ),
        migrations.AlterField(
            model_name='employee',
            name='speciality_id',
            field=models.CharField(blank=True, choices=[('revit_architecture', 'Revit Architecture'), ('revit_structure', 'Revit Structure'), ('tekla_structure', 'Tekla Structure')], help_text='Required only for Mentors', max_length=50, null=True, verbose_name='Speciality'),
        ),
    ]
