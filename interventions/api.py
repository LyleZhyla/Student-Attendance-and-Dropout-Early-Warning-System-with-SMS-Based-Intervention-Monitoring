from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsInterventionStaff
from audit_logs.models import AuditLog
from students.models import Guardian, Student

from .models import InterventionActivity, InterventionCase
from .serializers import InterventionActivitySerializer, InterventionCaseSerializer


def visible_cases(user):
    cases = InterventionCase.objects.select_related('student', 'assigned_to', 'created_by')
    if user.is_superuser or user.role in (user.Role.ADMIN, user.Role.GUIDANCE):
        return cases
    return cases.filter(
        Q(assigned_to=user) | Q(
            student__enrollments__status='ENROLLED',
            student__enrollments__section__schedules__teacher=user,
        )
    ).distinct()


def visible_students(user):
    students = Student.objects.filter(is_active=True)
    if user.is_superuser or user.role in (user.Role.ADMIN, user.Role.GUIDANCE):
        return students
    return students.filter(
        enrollments__status='ENROLLED', enrollments__section__schedules__teacher=user
    ).distinct()


def can_manage_case(user, case):
    return bool(user.is_superuser or user.role in (user.Role.ADMIN, user.Role.GUIDANCE) or case.assigned_to_id == user.pk)


def audit(request, action, case, summary, metadata=None):
    AuditLog.objects.create(
        actor=request.user, action=action, object_type=case._meta.label, object_id=str(case.pk),
        summary=summary, metadata=metadata or {}, ip_address=request.META.get('REMOTE_ADDR'),
    )


def system_activity(case, user, notes):
    return InterventionActivity.objects.create(
        case=case, activity_type=InterventionActivity.Type.STATUS_CHANGE,
        notes=notes, occurred_at=case.updated_at, recorded_by=user,
    )


@api_view(['GET'])
@permission_classes([IsInterventionStaff])
def intervention_options_api(request):
    User = get_user_model()
    personnel = User.objects.filter(
        is_active=True, role__in=(User.Role.ADMIN, User.Role.TEACHER, User.Role.GUIDANCE)
    ).order_by('last_name', 'first_name', 'username')
    if request.user.role == User.Role.TEACHER and not request.user.is_superuser:
        personnel = personnel.filter(pk=request.user.pk)
    students = visible_students(request.user).order_by('last_name', 'first_name')
    guardians = Guardian.objects.filter(students__in=students).distinct().order_by('full_name')
    return Response({
        'success': True,
        'students': [{'id': item.pk, 'name': str(item), 'lrn': item.learner_reference_number} for item in students],
        'personnel': [{'id': item.pk, 'name': str(item), 'role': item.get_role_display()} for item in personnel],
        'guardians': [{'id': item.pk, 'name': item.full_name} for item in guardians],
        'statuses': [{'value': value, 'label': label} for value, label in InterventionCase.Status.choices],
        'activity_types': [{'value': value, 'label': label} for value, label in InterventionActivity.Type.choices if value != InterventionActivity.Type.STATUS_CHANGE],
        'channels': [{'value': value, 'label': label} for value, label in InterventionActivity.Channel.choices],
        'outcomes': [{'value': value, 'label': label} for value, label in InterventionActivity.Outcome.choices],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsInterventionStaff])
def intervention_cases_api(request):
    if request.method == 'POST':
        data = request.data.copy()
        if request.user.role == request.user.Role.TEACHER and not request.user.is_superuser:
            data['assigned_to'] = request.user.pk
        serializer = InterventionCaseSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        if not visible_students(request.user).filter(pk=serializer.validated_data['student'].pk).exists():
            return Response({'message': 'Student not found or is outside your access.'}, status=404)
        with transaction.atomic():
            case = serializer.save(created_by=request.user, status=InterventionCase.Status.FOR_REVIEW)
            system_activity(case, request.user, 'Case created with status For Review.')
            audit(request, 'INTERVENTION_CREATED', case, f'Created intervention case for {case.student}.')
        return Response({'success': True, 'record': InterventionCaseSerializer(case).data}, status=201)

    cases = visible_cases(request.user).annotate(
        activity_count=Count('activities', distinct=True), last_activity_at=Max('activities__occurred_at')
    )
    status_filter = request.query_params.get('status', '').strip()
    search = request.query_params.get('search', '').strip()
    if status_filter:
        if status_filter not in InterventionCase.Status.values:
            return Response({'message': 'Choose a valid case status.'}, status=400)
        cases = cases.filter(status=status_filter)
    if search:
        cases = cases.filter(
            Q(student__first_name__icontains=search) | Q(student__last_name__icontains=search)
            | Q(student__learner_reference_number__icontains=search) | Q(reason__icontains=search)
        )
    scoped = visible_cases(request.user)
    totals = {row['status']: row['total'] for row in scoped.values('status').annotate(total=Count('id'))}
    return Response({
        'success': True,
        'records': InterventionCaseSerializer(cases[:500], many=True).data,
        'summary': {'total': sum(totals.values()), **{value: totals.get(value, 0) for value, _ in InterventionCase.Status.choices}},
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsInterventionStaff])
def intervention_case_detail_api(request, record_id):
    case = visible_cases(request.user).annotate(
        activity_count=Count('activities', distinct=True), last_activity_at=Max('activities__occurred_at')
    ).filter(pk=record_id).first()
    if not case:
        return Response({'message': 'Intervention case not found or is outside your access.'}, status=404)
    if request.method == 'GET':
        return Response({'success': True, 'record': InterventionCaseSerializer(case).data})
    if not can_manage_case(request.user, case):
        return Response({'message': 'Only the assigned case owner can update this case.'}, status=403)
    data = request.data.copy()
    if request.user.role == request.user.Role.TEACHER and not request.user.is_superuser:
        data['assigned_to'] = request.user.pk
    previous_status = case.status
    serializer = InterventionCaseSerializer(case, data=data, partial=True, context={'request': request})
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        case = serializer.save()
        metadata = {'from_status': previous_status, 'to_status': case.status}
        if case.status != previous_status:
            system_activity(
                case, request.user,
                f'Status changed from {dict(InterventionCase.Status.choices)[previous_status]} to {case.get_status_display()}.',
            )
        audit(request, 'INTERVENTION_UPDATED', case, f'Updated intervention case for {case.student}.', metadata)
    return Response({'success': True, 'record': InterventionCaseSerializer(case).data})


@api_view(['GET', 'POST'])
@permission_classes([IsInterventionStaff])
def intervention_activities_api(request, record_id):
    case = visible_cases(request.user).filter(pk=record_id).first()
    if not case:
        return Response({'message': 'Intervention case not found or is outside your access.'}, status=404)
    if request.method == 'GET':
        activities = case.activities.select_related('guardian', 'recorded_by')
        return Response({'success': True, 'records': InterventionActivitySerializer(activities, many=True).data})
    if not can_manage_case(request.user, case):
        return Response({'message': 'Only the assigned case owner can add case activities.'}, status=403)
    serializer = InterventionActivitySerializer(data=request.data, context={'request': request, 'case': case})
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        activity = serializer.save(case=case, recorded_by=request.user)
        audit(
            request, 'INTERVENTION_ACTIVITY_ADDED', case,
            f'Added {activity.get_activity_type_display()} to the case for {case.student}.',
            {'activity_id': activity.pk, 'activity_type': activity.activity_type},
        )
    return Response({'success': True, 'record': InterventionActivitySerializer(activity).data}, status=201)
