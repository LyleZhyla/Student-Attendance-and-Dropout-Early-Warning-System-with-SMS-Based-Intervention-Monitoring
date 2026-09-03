from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsWellBeingStaff
from audit_logs.models import AuditLog
from students.models import Student

from .models import WellBeingCheckIn
from .well_being import PRIVACY_NOTICE_VERSION, QUESTIONS, QUESTIONNAIRE_VERSION
from .well_being_serializers import (
    WellBeingCreateSerializer, WellBeingDetailSerializer, WellBeingSummarySerializer, WellBeingUpdateSerializer,
)


def queryset():
    return WellBeingCheckIn.objects.select_related('student', 'conducted_by', 'reviewed_by')


def audit(request, action, check_in, summary):
    AuditLog.objects.create(
        actor=request.user, action=action, object_type=check_in._meta.label, object_id=str(check_in.pk),
        summary=summary,
        metadata={
            'student_id': check_in.student_id,
            'conducted_on': str(check_in.conducted_on),
            'status': check_in.status,
            'questionnaire_version': check_in.questionnaire_version,
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )


@api_view(['GET'])
@permission_classes([IsWellBeingStaff])
def well_being_options_api(request):
    students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')
    return Response({
        'success': True,
        'students': [{'id': item.pk, 'name': str(item), 'lrn': item.learner_reference_number} for item in students],
        'questions': QUESTIONS,
        'questionnaire_version': QUESTIONNAIRE_VERSION,
        'privacy_notice_version': PRIVACY_NOTICE_VERSION,
        'priorities': [{'value': value, 'label': label} for value, label in WellBeingCheckIn.SupportPriority.choices],
        'statuses': [{'value': value, 'label': label} for value, label in WellBeingCheckIn.Status.choices],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsWellBeingStaff])
def well_being_checkins_api(request):
    if request.method == 'POST':
        serializer = WellBeingCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                check_in = serializer.save(
                    questionnaire_version=QUESTIONNAIRE_VERSION,
                    status=WellBeingCheckIn.Status.OPEN,
                    conducted_by=request.user,
                )
                audit(request, 'WELL_BEING_CHECKIN_CREATED', check_in, f'Recorded restricted check-in for {check_in.student}.')
        except IntegrityError:
            return Response({'message': 'A check-in already exists for this student and date.'}, status=409)
        return Response({'success': True, 'record': WellBeingDetailSerializer(check_in).data}, status=201)

    records = queryset()
    search = request.query_params.get('search', '').strip()
    status_filter = request.query_params.get('status', '').strip()
    priority = request.query_params.get('priority', '').strip()
    if status_filter:
        if status_filter not in WellBeingCheckIn.Status.values:
            return Response({'message': 'Choose a valid check-in status.'}, status=400)
        records = records.filter(status=status_filter)
    if priority:
        if priority not in WellBeingCheckIn.SupportPriority.values:
            return Response({'message': 'Choose a valid support priority.'}, status=400)
        records = records.filter(support_priority=priority)
    if search:
        records = records.filter(
            Q(student__first_name__icontains=search) | Q(student__last_name__icontains=search)
            | Q(student__learner_reference_number__icontains=search)
        )
    all_records = queryset()
    status_totals = {row['status']: row['total'] for row in all_records.values('status').annotate(total=Count('id'))}
    priority_totals = {row['support_priority']: row['total'] for row in all_records.values('support_priority').annotate(total=Count('id'))}
    return Response({
        'success': True,
        'records': WellBeingSummarySerializer(records[:500], many=True).data,
        'summary': {
            'total': all_records.count(),
            **{value: status_totals.get(value, 0) for value, _ in WellBeingCheckIn.Status.choices},
            **{value: priority_totals.get(value, 0) for value, _ in WellBeingCheckIn.SupportPriority.choices},
        },
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsWellBeingStaff])
def well_being_checkin_detail_api(request, record_id):
    check_in = queryset().filter(pk=record_id).first()
    if not check_in:
        return Response({'message': 'Well-being check-in not found.'}, status=404)
    if request.method == 'GET':
        return Response({'success': True, 'record': WellBeingDetailSerializer(check_in).data})
    immutable = {'student', 'conducted_on', 'responses', 'consent_confirmed', 'privacy_notice_version', 'questionnaire_version'}
    attempted = immutable.intersection(request.data.keys())
    if attempted:
        return Response({'message': f'Submitted check-in fields are immutable: {", ".join(sorted(attempted))}.'}, status=400)
    serializer = WellBeingUpdateSerializer(data=request.data, context={'request': request, 'instance': check_in})
    serializer.is_valid(raise_exception=True)
    for field, value in serializer.validated_data.items():
        setattr(check_in, field, value)
    if check_in.status != WellBeingCheckIn.Status.OPEN:
        check_in.reviewed_by = request.user
        check_in.reviewed_at = timezone.now()
    check_in.full_clean()
    check_in.save()
    audit(request, 'WELL_BEING_CHECKIN_UPDATED', check_in, f'Updated restricted check-in workflow for {check_in.student}.')
    return Response({'success': True, 'record': WellBeingDetailSerializer(check_in).data})
