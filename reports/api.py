from datetime import timedelta

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAdministrator, IsRiskReviewer
from attendance.models import AttendanceRecord
from audit_logs.models import AuditLog
from interventions.models import InterventionCase
from risk_assessment.models import RiskAssessment
from students.models import Student


class ReportFilters(serializers.Serializer):
    kind = serializers.ChoiceField(choices=('attendance', 'interventions', 'risk'))
    start = serializers.DateField()
    end = serializers.DateField()
    student = serializers.IntegerField(min_value=1, required=False)
    page = serializers.IntegerField(min_value=1, default=1)

    def validate(self, attrs):
        if attrs['end'] < attrs['start']:
            raise serializers.ValidationError('End date must not precede start date.')
        if attrs['end'] > timezone.localdate():
            raise serializers.ValidationError('End date cannot be in the future.')
        if (attrs['end'] - attrs['start']).days > 366:
            raise serializers.ValidationError('Select a date range of at most 367 inclusive days.')
        return attrs


def report_data(filters):
    kind = filters['kind']
    start, end = filters['start'], filters['end']
    if kind == 'attendance':
        records = AttendanceRecord.objects.select_related('student', 'class_schedule__subject', 'class_schedule__section__grade_level').filter(date__range=(start, end)).order_by('date', 'pk')
        columns = ['Date', 'LRN', 'Student', 'Class', 'Status']
        make_row = lambda item: [str(item.date), item.student.learner_reference_number, str(item.student), str(item.class_schedule), item.get_status_display()]
    elif kind == 'interventions':
        records = InterventionCase.objects.select_related('student', 'assigned_to').filter(created_at__date__range=(start, end)).order_by('created_at', 'pk')
        columns = ['Case', 'Created', 'LRN', 'Student', 'Owner', 'Status', 'Schedule', 'Follow-up']
        make_row = lambda item: [str(item.pk), str(timezone.localdate(item.created_at)), item.student.learner_reference_number, str(item.student), str(item.assigned_to), item.get_status_display(), timezone.localtime(item.scheduled_for).strftime('%Y-%m-%d %H:%M') if item.scheduled_for else '', str(item.follow_up_on or '')]
    else:
        records = RiskAssessment.objects.select_related('student', 'reviewed_by').filter(assessed_on__range=(start, end), review_decision=RiskAssessment.ReviewDecision.CONFIRMED).order_by('assessed_on', 'pk')
        columns = ['Assessment date', 'LRN', 'Student', 'Score', 'Level', 'Policy', 'Reviewer']
        make_row = lambda item: [str(item.assessed_on), item.student.learner_reference_number, str(item.student), str(item.score), item.get_level_display(), item.policy_version, str(item.reviewed_by or '')]
    if filters.get('student'):
        records = records.filter(student_id=filters['student'])
    return records, columns, make_row


@never_cache
@api_view(['GET'])
@permission_classes([IsRiskReviewer])
def report_options(request):
    return Response({
        'students': [{'id': s.pk, 'name': str(s), 'lrn': s.learner_reference_number} for s in Student.objects.all()],
        'can_view_audit': request.user.is_superuser or request.user.role == request.user.Role.ADMIN,
    })


@never_cache
@api_view(['GET'])
@permission_classes([IsRiskReviewer])
def report_preview(request):
    serializer = ReportFilters(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    filters = serializer.validated_data
    records, columns, make_row = report_data(filters)
    total = records.count()
    offset = (filters['page'] - 1) * 50
    return Response({'columns': columns, 'rows': [make_row(item) for item in records[offset:offset + 50]], 'total': total, 'page': filters['page'], 'page_size': 50})


@never_cache
@api_view(['POST'])
@permission_classes([IsRiskReviewer])
def report_print(request):
    serializer = ReportFilters(data=request.data)
    serializer.is_valid(raise_exception=True)
    filters = serializer.validated_data
    records, columns, make_row = report_data(filters)
    if records.count() > 5000:
        return Response({'message': 'This report exceeds 5,000 rows. Narrow the date range or student filter.'}, status=400)
    rows = [make_row(item) for item in records[:5001]]
    if len(rows) > 5000:
        return Response({'message': 'Report grew beyond 5,000 rows. Narrow the filters and retry.'}, status=400)
    generated_at = timezone.localtime()
    html = render_to_string('reports/print.html', {
        'title': f"TardyTrack {filters['kind'].title()} Report", 'columns': columns, 'rows': rows,
        'filters': filters, 'generated_at': generated_at, 'generated_by': str(request.user),
    })
    AuditLog.objects.create(
        actor=request.user, action='REPORT_GENERATED', object_type='reports.Report',
        summary=f"Generated {filters['kind']} report ({len(rows)} rows).",
        metadata={'kind': filters['kind'], 'start': str(filters['start']), 'end': str(filters['end']), 'student_id': filters.get('student'), 'row_count': len(rows)},
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    response['Cache-Control'] = 'no-store'
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'"
    return response


class AuditFilters(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    action = serializers.CharField(required=False, max_length=50)
    actor = serializers.IntegerField(required=False, min_value=1)
    page = serializers.IntegerField(default=1, min_value=1)

    def validate(self, attrs):
        attrs.setdefault('end', timezone.localdate())
        attrs.setdefault('start', attrs['end'] - timedelta(days=29))
        if attrs['start'] > attrs['end']:
            raise serializers.ValidationError('End date must not precede start date.')
        return attrs


@never_cache
@api_view(['GET'])
@permission_classes([IsAdministrator])
def audit_log_list(request):
    serializer = AuditFilters(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    filters = serializer.validated_data
    records = AuditLog.objects.select_related('actor').filter(occurred_at__date__range=(filters['start'], filters['end'])).order_by('-occurred_at', '-pk')
    if filters.get('action'):
        records = records.filter(action=filters['action'])
    if filters.get('actor'):
        records = records.filter(actor_id=filters['actor'])
    total = records.count()
    offset = (filters['page'] - 1) * 50
    # Do not publish arbitrary metadata/summary text: older events may contain sensitive content.
    return Response({
        'columns': ['Time', 'Actor', 'Action', 'Object type', 'Object ID'],
        'rows': [[timezone.localtime(item.occurred_at).strftime('%Y-%m-%d %H:%M:%S'), str(item.actor or 'System/deleted user'), item.action, item.object_type, item.object_id] for item in records[offset:offset + 50]],
        'total': total, 'page': filters['page'], 'page_size': 50,
        'actions': list(AuditLog.objects.order_by('action').values_list('action', flat=True).distinct()),
    })
