import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0001_initial'),
        ('students', '0003_guardian_mobile_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='smslog', name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sms_logs', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(model_name='smslog', name='delivered_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='smslog', name='last_attempted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='smslog', name='updated_at', field=models.DateTimeField(auto_now=True)),
        migrations.AlterField(
            model_name='smslog', name='category',
            field=models.CharField(choices=[('GENERAL', 'General notice'), ('ATTENDANCE', 'Attendance notice'), ('MEETING', 'Meeting notice'), ('HOME_VISIT', 'Home visit notice')], max_length=50),
        ),
        migrations.AlterField(
            model_name='smslog', name='status',
            field=models.CharField(choices=[('QUEUED', 'Queued'), ('SENDING', 'Sending'), ('SENT', 'Sent'), ('DELIVERED', 'Delivered'), ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled')], default='QUEUED', max_length=15),
        ),
        migrations.AlterModelOptions(name='smslog', options={'ordering': ('-queued_at',)}),
    ]
