import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_assessment_periods(apps, schema_editor):
    RiskAssessment = apps.get_model('risk_assessment', 'RiskAssessment')
    for assessment in RiskAssessment.objects.all().iterator():
        assessment.period_end = assessment.assessed_on
        assessment.period_start = assessment.assessed_on - datetime.timedelta(days=29)
        if assessment.reviewed_by_id and assessment.reviewed_at:
            assessment.review_decision = 'CONFIRMED'
        elif assessment.reviewed_by_id or assessment.reviewed_at:
            assessment.reviewed_by_id = None
            assessment.reviewed_at = None
        assessment.save(update_fields=('period_start', 'period_end', 'review_decision', 'reviewed_by', 'reviewed_at'))


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('risk_assessment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='riskassessment', name='generated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_risk_assessments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(model_name='riskassessment', name='period_end', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='riskassessment', name='period_start', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='riskassessment', name='policy_version', field=models.CharField(default='attendance-v1-draft', max_length=50)),
        migrations.AddField(
            model_name='riskassessment', name='review_decision',
            field=models.CharField(choices=[('PENDING', 'Pending review'), ('CONFIRMED', 'Confirmed'), ('DISMISSED', 'Dismissed'), ('NEEDS_MORE_INFO', 'Needs more information')], db_index=True, default='PENDING', max_length=20),
        ),
        migrations.AddField(model_name='riskassessment', name='reviewer_notes', field=models.TextField(blank=True)),
        migrations.AddField(model_name='riskassessment', name='updated_at', field=models.DateTimeField(auto_now=True)),
        migrations.RunPython(backfill_assessment_periods, migrations.RunPython.noop),
        migrations.AlterField(model_name='riskassessment', name='period_end', field=models.DateField()),
        migrations.AlterField(model_name='riskassessment', name='period_start', field=models.DateField()),
        migrations.AlterModelOptions(name='riskassessment', options={'ordering': ('-assessed_on', '-created_at')}),
    ]
