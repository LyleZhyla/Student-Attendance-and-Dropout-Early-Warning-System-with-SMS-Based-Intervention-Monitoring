from datetime import date

from django.db import transaction
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAttendanceEncoder
from academics.models import ClassSchedule
from audit_logs.models import AuditLog
from students.models import Enrollment

from .models import AttendanceRecord
from .serializers import AttendanceEntrySerializer, AttendanceRecordSerializer


def encoder_schedules(user):
    schedules = ClassSchedule.objects.select_related(
        'section__grade_level', 'section__school_year', 'subject', 'teacher'
    )
    if user.is_superuser or user.role == user.Role.ADMIN:
        return schedules
    return schedules.filter(teacher=user)


def visible_records(user):
    records = AttendanceRecord.objects.select_related(
        'student', 'class_schedule__section__grade_level', 'class_schedule__subject', 'encoded_by'
    )
    if user.is_superuser or user.role == user.Role.ADMIN:
        return records
    if user.role == user.Role.TEACHER:
        return records.filter(class_schedule__teacher=user)
    if user.role == user.Role.STUDENT:
        profile = getattr(user, 'student_profile', None)
        return records.filter(student=profile) if profile else records.none()
    if user.role == user.Role.PARENT:
        guardian = getattr(user, 'guardian_profile', None)
        return records.filter(student__guardians=guardian).distinct() if guardian else records.none()
    return records.none()


def requested_date(raw_value):
    try:
        return date.fromisoformat(str(raw_value))
    except (TypeError, ValueError):
        return None


def schedule_for_encoder(request, schedule_id):
    return encoder_schedules(request.user).filter(pk=schedule_id).first()


def schedule_payload(item):
    return {
        'id': item.pk,
        'name': str(item),
        'section': str(item.section),
        'subject': str(item.subject),
        'teacher': str(item.teacher),
        'weekday': item.weekday,
        'weekday_label': item.get_weekday_display(),
        'starts_at': item.starts_at,
        'ends_at': item.ends_at,
        'school_year': item.section.school_year.name,
    }


def validate_session_date(schedule, attendance_date):
    if attendance_date is None:
        return 'Use a valid attendance date.'
    from django.utils import timezone

    if attendance_date > timezone.localdate():
        return 'Attendance cannot be recorded for a future date.'
    school_year = schedule.section.school_year
    if not school_year.starts_on <= attendance_date <= school_year.ends_on:
        return 'Attendance date must be within the schedule school year.'
    if attendance_date.isoweekday() != schedule.weekday:
        return f'This class is scheduled on {schedule.get_weekday_display()}.'
    return None


@api_view(['GET'])
@permission_classes([IsAttendanceEncoder])
def attendance_options_api(request):
    schedules = encoder_schedules(request.user).order_by(
        '-section__school_year__starts_on', 'weekday', 'starts_at', 'subject__code'
    )
    return Response({
        'success': True,
        'schedules': [schedule_payload(item) for item in schedules],
        'statuses': [{'value': value, 'label': label} for value, label in AttendanceRecord.Status.choices],
    })


@api_view(['GET'])
@permission_classes([IsAttendanceEncoder])
def attendance_roster_api(request):
    schedule = schedule_for_encoder(request, request.query_params.get('schedule'))
    if not schedule:
        return Response({'message': 'Schedule not found or is outside your assignment.'}, status=404)
    attendance_date = requested_date(request.query_params.get('date'))
    error = validate_session_date(schedule, attendance_date)
    if error:
        return Response({'message': error}, status=400)

    enrollments = Enrollment.objects.filter(
        section=schedule.section,
        status=Enrollment.Status.ENROLLED,
        enrolled_on__lte=attendance_date,
        student__is_active=True,
    ).select_related('student').order_by('student__last_name', 'student__first_name')
    existing = {
        record.student_id: record
        for record in AttendanceRecord.objects.filter(class_schedule=schedule, date=attendance_date)
    }
    roster = []
    for enrollment in enrollments:
        record = existing.get(enrollment.student_id)
        roster.append({
            'student': enrollment.student_id,
            'student_name': str(enrollment.student),
            'learner_reference_number': enrollment.student.learner_reference_number,
            'record_id': record.pk if record else None,
            'status': record.status if record else AttendanceRecord.Status.NOT_RECORDED,
            'time_in': record.time_in if record else None,
            'excuse_reason': record.excuse_reason if record else '',
            'updated_at': record.updated_at if record else None,
        })
    return Response({
        'success': True,
        'schedule': schedule_payload(schedule),
        'date': attendance_date,
        'roster': roster,
    })


@api_view(['POST'])
@permission_classes([IsAttendanceEncoder])
def attendance_bulk_api(request):
    schedule = schedule_for_encoder(request, request.data.get('schedule'))
    if not schedule:
        return Response({'message': 'Schedule not found or is outside your assignment.'}, status=404)
    attendance_date = requested_date(request.data.get('date'))
    error = validate_session_date(schedule, attendance_date)
    if error:
        return Response({'message': error}, status=400)
    entries = request.data.get('records')
    if not isinstance(entries, list) or not entries:
        return Response({'message': 'At least one attendance record is required.'}, status=400)

    serializer = AttendanceEntrySerializer(data=entries, many=True)
    serializer.is_valid(raise_exception=True)
    student_ids = [entry['student'] for entry in serializer.validated_data]
    if len(student_ids) != len(set(student_ids)):
        return Response({'message': 'Each student may appear only once in a bulk submission.'}, status=400)
    eligible_ids = set(Enrollment.objects.filter(
        student_id__in=student_ids,
        section=schedule.section,
        status=Enrollment.Status.ENROLLED,
        enrolled_on__lte=attendance_date,
        student__is_active=True,
    ).values_list('student_id', flat=True))
    invalid_ids = sorted(set(student_ids) - eligible_ids)
    if invalid_ids:
        return Response({
            'message': 'One or more students are not actively enrolled in this section on the selected date.',
            'student_ids': invalid_ids,
        }, status=400)

    created_count = 0
    updated_count = 0
    with transaction.atomic():
        for entry in serializer.validated_data:
            defaults = {
                'status': entry['status'],
                'time_in': entry.get('time_in'),
                'excuse_reason': entry.get('excuse_reason', ''),
                'encoded_by': request.user,
            }
            _, created = AttendanceRecord.objects.update_or_create(
                student_id=entry['student'], class_schedule=schedule, date=attendance_date, defaults=defaults
            )
            created_count += int(created)
            updated_count += int(not created)
        AuditLog.objects.create(
            actor=request.user,
            action='ATTENDANCE_BULK_ENCODED',
            object_type='academics.ClassSchedule',
            object_id=str(schedule.pk),
            summary=f'Saved {len(entries)} attendance entries for {schedule} on {attendance_date}.',
            metadata={
                'date': str(attendance_date), 'created': created_count,
                'updated': updated_count, 'student_ids': student_ids,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    return Response({
        'success': True,
        'message': f'Attendance saved for {len(entries)} students.',
        'created': created_count,
        'updated': updated_count,
    })


@api_view(['GET'])
def attendance_records_api(request):
    records = visible_records(request.user)
    if request.query_params.get('schedule'):
        records = records.filter(class_schedule_id=request.query_params['schedule'])
    if request.query_params.get('date'):
        attendance_date = requested_date(request.query_params['date'])
        if not attendance_date:
            return Response({'message': 'Use a valid attendance date.'}, status=400)
        records = records.filter(date=attendance_date)
    if request.query_params.get('student'):
        records = records.filter(student_id=request.query_params['student'])
    status_totals = {
        row['status']: row['total'] for row in records.values('status').annotate(total=Count('id'))
    }
    return Response({
        'success': True,
        'records': AttendanceRecordSerializer(records.order_by('-date', 'student__last_name'), many=True).data,
        'summary': {
            'total': sum(status_totals.values()),
            **{value: status_totals.get(value, 0) for value, _ in AttendanceRecord.Status.choices},
        },
    })
