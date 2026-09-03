from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAdministrator
from academics.models import Section
from audit_logs.models import AuditLog
from .models import Enrollment, Guardian, Student, StudentGuardian
from .serializers import EnrollmentSerializer, GuardianSerializer, StudentGuardianSerializer, StudentSerializer


def audit(request, action, instance):
    AuditLog.objects.create(
        actor=request.user, action=action, object_type=instance._meta.label,
        object_id=str(instance.pk), summary=f'{action.replace("_", " ").title()}: {instance}.',
        ip_address=request.META.get('REMOTE_ADDR'),
    )


def save_record(request, serializer_class, instance=None):
    serializer = serializer_class(instance, data=request.data, partial=instance is not None)
    serializer.is_valid(raise_exception=True)
    saved = serializer.save()
    audit(request, 'MASTER_DATA_UPDATED' if instance else 'MASTER_DATA_CREATED', saved)
    return Response(
        {'success': True, 'record': serializer_class(saved).data}, status=200 if instance else 201
    )


@api_view(['GET'])
@permission_classes([IsAdministrator])
def student_options_api(request):
    User = get_user_model()
    return Response({
        'success': True,
        'student_accounts': [
            {'id': user.pk, 'name': str(user)} for user in User.objects.filter(
                role=User.Role.STUDENT, is_active=True
            ).order_by('last_name', 'first_name')
        ],
        'parent_accounts': [
            {'id': user.pk, 'name': str(user)} for user in User.objects.filter(
                role=User.Role.PARENT, is_active=True
            ).order_by('last_name', 'first_name')
        ],
        'sections': [
            {'id': section.pk, 'name': str(section), 'school_year': section.school_year.name}
            for section in Section.objects.select_related('grade_level', 'school_year').order_by(
                '-school_year__starts_on', 'grade_level__order', 'name'
            )
        ],
        'statuses': [{'value': value, 'label': label} for value, label in Enrollment.Status.choices],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def students_api(request):
    if request.method == 'POST':
        return save_record(request, StudentSerializer)
    records = Student.objects.select_related('user').prefetch_related('enrollments__section', 'studentguardian_set__guardian')
    search = request.query_params.get('search', '').strip()
    active = request.query_params.get('active', '').strip().lower()
    if search:
        records = records.filter(
            Q(learner_reference_number__icontains=search) | Q(first_name__icontains=search)
            | Q(middle_name__icontains=search) | Q(last_name__icontains=search)
        )
    if active in ('true', 'false'):
        records = records.filter(is_active=active == 'true')
    return Response({'success': True, 'records': StudentSerializer(records, many=True).data})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def student_detail_api(request, record_id):
    try:
        student = Student.objects.get(pk=record_id)
    except Student.DoesNotExist:
        return Response({'message': 'Student not found.'}, status=404)
    if request.method == 'GET':
        return Response({'success': True, 'record': StudentSerializer(student).data})
    return save_record(request, StudentSerializer, student)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def guardians_api(request):
    if request.method == 'POST':
        return save_record(request, GuardianSerializer)
    records = Guardian.objects.select_related('user').annotate(student_count=Count('students')).order_by('full_name')
    search = request.query_params.get('search', '').strip()
    if search:
        records = records.filter(Q(full_name__icontains=search) | Q(mobile_number__icontains=search) | Q(email__icontains=search))
    return Response({'success': True, 'records': GuardianSerializer(records, many=True).data})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def guardian_detail_api(request, record_id):
    try:
        guardian = Guardian.objects.get(pk=record_id)
    except Guardian.DoesNotExist:
        return Response({'message': 'Guardian not found.'}, status=404)
    if request.method == 'GET':
        return Response({'success': True, 'record': GuardianSerializer(guardian).data})
    return save_record(request, GuardianSerializer, guardian)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def enrollments_api(request):
    if request.method == 'POST':
        return save_record(request, EnrollmentSerializer)
    records = Enrollment.objects.select_related('student', 'section__grade_level', 'section__school_year').order_by(
        '-section__school_year__starts_on', 'student__last_name', 'student__first_name'
    )
    return Response({'success': True, 'records': EnrollmentSerializer(records, many=True).data})


@api_view(['PATCH'])
@permission_classes([IsAdministrator])
def enrollment_detail_api(request, record_id):
    try:
        enrollment = Enrollment.objects.get(pk=record_id)
    except Enrollment.DoesNotExist:
        return Response({'message': 'Enrollment not found.'}, status=404)
    return save_record(request, EnrollmentSerializer, enrollment)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def guardian_links_api(request):
    if request.method == 'POST':
        return save_record(request, StudentGuardianSerializer)
    records = StudentGuardian.objects.select_related('student', 'guardian').order_by('student__last_name', '-is_primary')
    return Response({'success': True, 'records': StudentGuardianSerializer(records, many=True).data})


@api_view(['PATCH'])
@permission_classes([IsAdministrator])
def guardian_link_detail_api(request, record_id):
    try:
        link = StudentGuardian.objects.get(pk=record_id)
    except StudentGuardian.DoesNotExist:
        return Response({'message': 'Guardian link not found.'}, status=404)
    return save_record(request, StudentGuardianSerializer, link)
