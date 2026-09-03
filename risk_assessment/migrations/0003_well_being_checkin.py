import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('risk_assessment', '0002_explainable_review_workflow'),
    ]

    operations = [
        migrations.CreateModel(
            name='WellBeingCheckIn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conducted_on', models.DateField(db_index=True)),
                ('questionnaire_version', models.CharField(default='support-check-in-v1-draft', max_length=50)),
                ('privacy_notice_version', models.CharField(max_length=50)),
                ('consent_confirmed', models.BooleanField(default=False)),
                ('responses', models.JSONField(help_text='Restricted support check-in responses; excluded from automated scoring.')),
                ('support_priority', models.CharField(choices=[('ROUTINE', 'Routine support'), ('PROMPT', 'Prompt follow-up'), ('URGENT', 'Urgent human follow-up')], db_index=True, default='ROUTINE', max_length=15)),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('ACTION_PLANNED', 'Action planned'), ('CLOSED', 'Closed')], db_index=True, default='OPEN', max_length=20)),
                ('private_notes', models.TextField(blank=True)),
                ('recommended_actions', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('conducted_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='conducted_well_being_checkins', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reviewed_well_being_checkins', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='well_being_checkins', to='students.student')),
            ],
            options={
                'ordering': ('-conducted_on', '-created_at'),
                'constraints': [models.UniqueConstraint(fields=('student', 'conducted_on'), name='unique_student_well_being_checkin_day')],
            },
        ),
    ]
