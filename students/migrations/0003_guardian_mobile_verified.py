from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('students', '0002_studentguardian_unique_primary_guardian_per_student')]

    operations = [
        migrations.AddField(
            model_name='guardian',
            name='mobile_verified',
            field=models.BooleanField(default=False, help_text='Confirms that the guardian controls this mobile number.'),
        ),
    ]
