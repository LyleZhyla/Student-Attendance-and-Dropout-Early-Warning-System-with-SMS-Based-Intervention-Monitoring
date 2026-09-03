from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAdministrator
from audit_logs.models import AuditLog
from .models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject
from .serializers import (
    ClassScheduleSerializer, GradeLevelSerializer, SchoolYearSerializer, SectionSerializer, SubjectSerializer,
)


def audit(request, action, instance):
    AuditLog.objects.create(
        actor=request.user, action=action, object_type=instance._meta.label,
        object_id=str(instance.pk), summary=f'{action.replace("_", " ").title()}: {instance}.',
        ip_address=request.META.get('REMOTE_ADDR'),
    )


def collection(request, model, serializer_class, queryset=None):
    if request.method == 'GET':
        records = queryset if queryset is not None else model.objects.all()
        search = request.query_params.get('search', '').strip()
        if search:
            fields = {
                SchoolYear: ('name',), GradeLevel: ('name',), Subject: ('code', 'name'),
                Section: ('name', 'grade_level__name', 'school_year__name', 'adviser__first_name', 'adviser__last_name'),
                ClassSchedule: ('section__name', 'subject__code', 'subject__name', 'teacher__first_name', 'teacher__last_name'),
            }[model]
            query = Q()
            for field in fields:
                query |= Q(**{f'{field}__icontains': search})
            records = records.filter(query)
        return Response({'success': True, 'records': serializer_class(records, many=True).data})
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    audit(request, 'MASTER_DATA_CREATED', instance)
    return Response({'success': True, 'record': serializer_class(instance).data}, status=201)


def detail(request, model, serializer_class, record_id):
    try:
        instance = model.objects.get(pk=record_id)
    except model.DoesNotExist:
        return Response({'message': 'Record not found.'}, status=404)
    if request.method == 'GET':
        return Response({'success': True, 'record': serializer_class(instance).data})
    serializer = serializer_class(instance, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    audit(request, 'MASTER_DATA_UPDATED', instance)
    return Response({'success': True, 'record': serializer_class(instance).data})


@api_view(['GET'])
@permission_classes([IsAdministrator])
def academic_options_api(request):
    User = get_user_model()
    return Response({
        'success': True,
        'teachers': [
            {'id': user.pk, 'name': str(user)}
            for user in User.objects.filter(role=User.Role.TEACHER, is_active=True).order_by('last_name', 'first_name')
        ],
        'school_years': SchoolYearSerializer(SchoolYear.objects.order_by('-starts_on'), many=True).data,
        'grade_levels': GradeLevelSerializer(GradeLevel.objects.order_by('order', 'name'), many=True).data,
        'subjects': SubjectSerializer(Subject.objects.order_by('code'), many=True).data,
        'sections': SectionSerializer(
            Section.objects.select_related('grade_level', 'school_year', 'adviser').annotate(student_count=Count('enrollments')),
            many=True,
        ).data,
        'weekdays': [{'value': value, 'label': label} for value, label in ClassSchedule.Weekday.choices],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def school_years_api(request):
    return collection(request, SchoolYear, SchoolYearSerializer, SchoolYear.objects.order_by('-starts_on'))


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def school_year_detail_api(request, record_id):
    return detail(request, SchoolYear, SchoolYearSerializer, record_id)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def grade_levels_api(request):
    return collection(request, GradeLevel, GradeLevelSerializer, GradeLevel.objects.order_by('order', 'name'))


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def grade_level_detail_api(request, record_id):
    return detail(request, GradeLevel, GradeLevelSerializer, record_id)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def subjects_api(request):
    return collection(request, Subject, SubjectSerializer, Subject.objects.order_by('code'))


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def subject_detail_api(request, record_id):
    return detail(request, Subject, SubjectSerializer, record_id)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def sections_api(request):
    records = Section.objects.select_related('grade_level', 'school_year', 'adviser').annotate(student_count=Count('enrollments'))
    return collection(request, Section, SectionSerializer, records)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def section_detail_api(request, record_id):
    return detail(request, Section, SectionSerializer, record_id)


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def schedules_api(request):
    records = ClassSchedule.objects.select_related('section__grade_level', 'subject', 'teacher').order_by(
        'section__grade_level__order', 'section__name', 'weekday', 'starts_at'
    )
    return collection(request, ClassSchedule, ClassScheduleSerializer, records)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdministrator])
def schedule_detail_api(request, record_id):
    return detail(request, ClassSchedule, ClassScheduleSerializer, record_id)
