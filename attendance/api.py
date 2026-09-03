from calendar import monthrange
from datetime import date

from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAttendanceEncoder, IsAttendanceViewer
from academics.models import ClassSchedule
from audit_logs.models import AuditLog
from students.models import Enrollment, Student

from .models import AttendanceRecord
from .serializers import AttendanceEntrySerializer, AttendanceRecordSerializer
from notifications.services import queue_attendance_notifications


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


def requested_month(raw_value):
    try:
        parsed = date.fromisoformat(f'{raw_value}-01')
    except (TypeError, ValueError):
        return None
    return parsed if parsed <= timezone.localdate().replace(day=1) else None


def shift_month(value, offset):
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_end(value):
    return value.replace(day=monthrange(value.year, value.month)[1])


def status_count_payload(records):
    totals = {
        row['status']: row['total']
        for row in records.values('status').annotate(total=Count('id'))
    }
    return {value: totals.get(value, 0) for value, _ in AttendanceRecord.Status.choices}


def attendance_rates(counts):
    recorded = sum(counts.values()) - counts[AttendanceRecord.Status.NOT_RECORDED]
    attended = (
        counts[AttendanceRecord.Status.PRESENT]
        + counts[AttendanceRecord.Status.LATE]
        + counts[AttendanceRecord.Status.SCHOOL_ACTIVITY]
    )
    absences = counts[AttendanceRecord.Status.ABSENT_EXCUSED] + counts[AttendanceRecord.Status.ABSENT_UNEXCUSED]
    punctual_sessions = counts[AttendanceRecord.Status.PRESENT] + counts[AttendanceRecord.Status.LATE]
    return {
        'recorded': recorded,
        'attended': attended,
        'absences': absences,
        'attendance_rate': round(attended * 100 / recorded, 1) if recorded else 0,
        'absence_rate': round(absences * 100 / recorded, 1) if recorded else 0,
        'punctuality_rate': round(counts[AttendanceRecord.Status.PRESENT] * 100 / punctual_sessions, 1)
        if punctual_sessions else 0,
    }


def analytics_schedules(user):
    schedules = ClassSchedule.objects.select_related(
        'section__grade_level', 'section__school_year', 'subject', 'teacher'
    )
    if user.is_superuser or user.role == user.Role.ADMIN:
        return schedules
    if user.role == user.Role.TEACHER:
        return schedules.filter(teacher=user)
    if user.role == user.Role.STUDENT:
        profile = getattr(user, 'student_profile', None)
        return schedules.filter(section__enrollments__student=profile).distinct() if profile else schedules.none()
    guardian = getattr(user, 'guardian_profile', None)
    return schedules.filter(section__enrollments__student__guardians=guardian).distinct() if guardian else schedules.none()


def analytics_students(user):
    students = Student.objects.filter(is_active=True)
    if user.is_superuser or user.role == user.Role.ADMIN:
        return students
    if user.role == user.Role.TEACHER:
        return students.filter(enrollments__section__schedules__teacher=user).distinct()
    if user.role == user.Role.STUDENT:
        profile = getattr(user, 'student_profile', None)
        return students.filter(pk=profile.pk) if profile else students.none()
    guardian = getattr(user, 'guardian_profile', None)
    return students.filter(guardians=guardian).distinct() if guardian else students.none()


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
    notification_count = 0
    with transaction.atomic():
        for entry in serializer.validated_data:
            defaults = {
                'status': entry['status'],
                'time_in': entry.get('time_in'),
                'excuse_reason': entry.get('excuse_reason', ''),
                'encoded_by': request.user,
            }
            record, created = AttendanceRecord.objects.update_or_create(
                student_id=entry['student'], class_schedule=schedule, date=attendance_date, defaults=defaults
            )
            created_count += int(created)
            updated_count += int(not created)
            notification_count += len(queue_attendance_notifications(record, created_by=request.user))
        AuditLog.objects.create(
            actor=request.user,
            action='ATTENDANCE_BULK_ENCODED',
            object_type='academics.ClassSchedule',
            object_id=str(schedule.pk),
            summary=f'Saved {len(entries)} attendance entries for {schedule} on {attendance_date}.',
            metadata={
                'date': str(attendance_date), 'created': created_count,
                'updated': updated_count, 'student_ids': student_ids,
                'notifications_queued': notification_count,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    return Response({
        'success': True,
        'message': f'Attendance saved for {len(entries)} students.',
        'created': created_count,
        'updated': updated_count,
        'notifications_queued': notification_count,
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


@api_view(['GET'])
@permission_classes([IsAttendanceViewer])
def attendance_analytics_api(request):
    selected_month = requested_month(request.query_params.get('month') or timezone.localdate().strftime('%Y-%m'))
    if not selected_month:
        return Response({'message': 'Use a valid current or past month in YYYY-MM format.'}, status=400)

    allowed_schedules = analytics_schedules(request.user).order_by(
        '-section__school_year__starts_on', 'weekday', 'starts_at', 'subject__code'
    )
    allowed_students = analytics_students(request.user).order_by('last_name', 'first_name')
    records = visible_records(request.user)
    schedule_id = request.query_params.get('schedule', '').strip()
    student_id = request.query_params.get('student', '').strip()
    if schedule_id:
        if not schedule_id.isdigit() or not allowed_schedules.filter(pk=schedule_id).exists():
            return Response({'message': 'Schedule not found or is outside your access.'}, status=404)
        records = records.filter(class_schedule_id=schedule_id)
    if student_id:
        if not student_id.isdigit() or not allowed_students.filter(pk=student_id).exists():
            return Response({'message': 'Student not found or is outside your access.'}, status=404)
        records = records.filter(student_id=student_id)

    end = month_end(selected_month)
    period_records = records.filter(date__range=(selected_month, end))
    counts = status_count_payload(period_records)
    rates = attendance_rates(counts)

    daily_rows = period_records.values('date', 'status').annotate(total=Count('id')).order_by('date')
    daily_map = {}
    for row in daily_rows:
        day = str(row['date'])
        daily_map.setdefault(day, {value: 0 for value, _ in AttendanceRecord.Status.choices})
        daily_map[day][row['status']] = row['total']
    daily_trend = []
    for day, day_counts in daily_map.items():
        daily_trend.append({'date': day, **day_counts, **attendance_rates(day_counts)})

    trend_start = shift_month(selected_month, -5)
    monthly_rows = records.filter(date__range=(trend_start, end)).annotate(
        month=TruncMonth('date')
    ).values('month', 'status').annotate(total=Count('id')).order_by('month')
    monthly_map = {
        shift_month(trend_start, offset): {value: 0 for value, _ in AttendanceRecord.Status.choices}
        for offset in range(6)
    }
    for row in monthly_rows:
        month_key = row['month'].date() if hasattr(row['month'], 'date') else row['month']
        monthly_map[month_key][row['status']] = row['total']
    monthly_trend = [
        {
            'month': month_key.strftime('%Y-%m'),
            'label': month_key.strftime('%b %Y'),
            **attendance_rates(month_counts),
        }
        for month_key, month_counts in monthly_map.items()
    ]

    breakdown = period_records.values(
        'student_id', 'student__first_name', 'student__last_name', 'student__learner_reference_number'
    ).annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status=AttendanceRecord.Status.PRESENT)),
        late=Count('id', filter=Q(status=AttendanceRecord.Status.LATE)),
        excused=Count('id', filter=Q(status=AttendanceRecord.Status.ABSENT_EXCUSED)),
        unexcused=Count('id', filter=Q(status=AttendanceRecord.Status.ABSENT_UNEXCUSED)),
        school_activity=Count('id', filter=Q(status=AttendanceRecord.Status.SCHOOL_ACTIVITY)),
        not_recorded=Count('id', filter=Q(status=AttendanceRecord.Status.NOT_RECORDED)),
    )
    student_breakdown = []
    for row in breakdown:
        student_counts = {
            AttendanceRecord.Status.PRESENT.value: row['present'],
            AttendanceRecord.Status.LATE.value: row['late'],
            AttendanceRecord.Status.ABSENT_EXCUSED.value: row['excused'],
            AttendanceRecord.Status.ABSENT_UNEXCUSED.value: row['unexcused'],
            AttendanceRecord.Status.SCHOOL_ACTIVITY.value: row['school_activity'],
            AttendanceRecord.Status.NOT_RECORDED.value: row['not_recorded'],
        }
        student_breakdown.append({
            'student': row['student_id'],
            'student_name': f"{row['student__last_name']}, {row['student__first_name']}",
            'learner_reference_number': row['student__learner_reference_number'],
            **student_counts,
            **attendance_rates(student_counts),
            'monitoring_events': row['late'] + row['excused'] + row['unexcused'],
        })
    student_breakdown.sort(
        key=lambda item: (
            item[AttendanceRecord.Status.ABSENT_UNEXCUSED.value],
            item['absences'],
            item[AttendanceRecord.Status.LATE.value],
        ),
        reverse=True,
    )

    return Response({
        'success': True,
        'period': {
            'month': selected_month.strftime('%Y-%m'), 'label': selected_month.strftime('%B %Y'),
            'starts_on': selected_month, 'ends_on': end,
        },
        'filters': {'schedule': int(schedule_id) if schedule_id else None, 'student': int(student_id) if student_id else None},
        'filter_options': {
            'schedules': [schedule_payload(item) for item in allowed_schedules],
            'students': [
                {'id': item.pk, 'name': str(item), 'learner_reference_number': item.learner_reference_number}
                for item in allowed_students
            ],
        },
        'summary': {**counts, **rates, 'total': sum(counts.values())},
        'daily_trend': daily_trend,
        'monthly_trend': monthly_trend,
        'student_breakdown': student_breakdown,
        'methodology': {
            'attendance_rate': 'Present, Late, and School Activity divided by recorded sessions; Not Recorded is excluded.',
            'absence_rate': 'Excused and Unexcused Absence divided by recorded sessions.',
            'monitoring': 'The table ranks attendance events only and does not assign a risk or disciplinary label.',
        },
    })
