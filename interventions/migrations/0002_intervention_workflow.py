import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def backfill_case_creators(apps, schema_editor):
    InterventionCase = apps.get_model('interventions', 'InterventionCase')
    for case in InterventionCase.objects.filter(created_by__isnull=True).iterator():
        case.created_by_id = case.assigned_to_id
        case.save(update_fields=('created_by',))


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('interventions', '0001_initial'),
        ('students', '0003_guardian_mobile_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='interventioncase', name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='created_interventions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='InterventionActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('NOTE', 'Case note'), ('PARENT_CONTACT', 'Parent contact attempt'), ('MEETING', 'Meeting'), ('HOME_VISIT', 'Home visit'), ('FOLLOW_UP', 'Follow-up'), ('STATUS_CHANGE', 'Status change')], max_length=30)),
                ('channel', models.CharField(blank=True, choices=[('PHONE', 'Phone call'), ('SMS', 'SMS'), ('IN_PERSON', 'In person'), ('OTHER', 'Other')], max_length=20)),
                ('outcome', models.CharField(blank=True, choices=[('REACHED', 'Reached guardian'), ('NO_ANSWER', 'No answer'), ('INVALID_CONTACT', 'Invalid contact details'), ('RESCHEDULED', 'Rescheduled'), ('COMPLETED', 'Completed'), ('REFERRED', 'Referred for further support')], max_length=30)),
                ('notes', models.TextField()),
                ('occurred_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('next_action_on', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='interventions.interventioncase')),
                ('guardian', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='intervention_activities', to='students.guardian')),
                ('recorded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='recorded_intervention_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-occurred_at', '-created_at')},
        ),
        migrations.AlterModelOptions(name='interventioncase', options={'ordering': ('-updated_at',)}),
        migrations.RunPython(backfill_case_creators, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='interventioncase', name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_interventions', to=settings.AUTH_USER_MODEL),
        ),
    ]
