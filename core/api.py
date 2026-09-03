from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from attendance.models import AttendanceRecord
from interventions.models import InterventionCase
from notifications.models import SMSLog
from risk_assessment.models import RiskAssessment
from students.models import Student
from audit_logs.models import AuditLog


def user_payload(user):
    return {
        'id': user.pk,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name() or user.username,
        'role': user.role,
        'role_label': user.get_role_display(),
        'is_active': user.is_active,
        'must_change_password': user.must_change_password,
        'is_superuser': user.is_superuser,
        'last_login': user.last_login,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    identifier = str(request.data.get('identifier', '')).strip()
    password = request.data.get('password', '')
    if not identifier or not password:
        return Response({'success': False, 'message': 'Username/email and password are required.'}, status=400)

    User = get_user_model()
    matched_user = User.objects.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True
    ).first()
    user = authenticate(request, username=matched_user.username if matched_user else identifier, password=password)
    if user is None:
        return Response({'success': False, 'message': 'Invalid username/email or password.'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    AuditLog.objects.create(
        actor=user, action='LOGIN', object_type='accounts.User', object_id=str(user.pk),
        summary=f'Account {user.username} signed in.',
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    return Response({'success': True, 'token': token.key, 'user': user_payload(user)})


@api_view(['POST'])
def logout_api(request):
    AuditLog.objects.create(
        actor=request.user, action='LOGOUT', object_type='accounts.User', object_id=str(request.user.pk),
        summary=f'Account {request.user.username} signed out.',
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    if request.auth:
        request.auth.delete()
    return Response({'success': True})


@api_view(['GET'])
def me_api(request):
    return Response({'success': True, 'user': user_payload(request.user)})


@api_view(['GET'])
def dashboard_summary(request):
    today = timezone.localdate()
    user = request.user
    students = Student.objects.filter(is_active=True)
    attendance = AttendanceRecord.objects.all()
    risk_assessments = RiskAssessment.objects.all()
    interventions = InterventionCase.objects.all()
    sms_logs = SMSLog.objects.all()

    if user.role == user.Role.TEACHER:
        students = students.filter(enrollments__section__schedules__teacher=user).distinct()
        attendance = attendance.filter(class_schedule__teacher=user)
        risk_assessments = risk_assessments.filter(student__in=students)
        interventions = interventions.filter(student__in=students)
        sms_logs = sms_logs.filter(student__in=students)
    elif user.role == user.Role.STUDENT:
        profile = getattr(user, 'student_profile', None)
        students = students.filter(pk=profile.pk) if profile else students.none()
        attendance = attendance.filter(student__in=students)
        risk_assessments = risk_assessments.filter(
            student__in=students, review_decision=RiskAssessment.ReviewDecision.CONFIRMED
        )
        interventions = interventions.filter(student__in=students)
        sms_logs = sms_logs.filter(student__in=students)
    elif user.role == user.Role.PARENT:
        guardian = getattr(user, 'guardian_profile', None)
        students = students.filter(guardians=guardian).distinct() if guardian else students.none()
        attendance = attendance.filter(student__in=students)
        risk_assessments = risk_assessments.filter(
            student__in=students, review_decision=RiskAssessment.ReviewDecision.CONFIRMED
        )
        interventions = interventions.filter(student__in=students)
        sms_logs = sms_logs.filter(guardian=guardian) if guardian else sms_logs.none()
    elif user.role not in (user.Role.ADMIN, user.Role.GUIDANCE) and not user.is_superuser:
        students = students.none()
        attendance = attendance.none()
        risk_assessments = risk_assessments.none()
        interventions = interventions.none()
        sms_logs = sms_logs.none()

    today_attendance = attendance.filter(date=today)
    open_intervention_statuses = [
        InterventionCase.Status.FOR_REVIEW,
        InterventionCase.Status.CONTACTING_PARENT,
        InterventionCase.Status.MEETING_SCHEDULED,
        InterventionCase.Status.HOME_VISIT_SCHEDULED,
        InterventionCase.Status.UNDER_INTERVENTION,
        InterventionCase.Status.FOR_FOLLOW_UP,
    ]
    attendance_by_status = {
        row['status']: row['total']
        for row in today_attendance.values('status').annotate(total=Count('id'))
    }
    month_attendance = attendance.filter(date__range=(today.replace(day=1), today))
    month_by_status = {
        row['status']: row['total']
        for row in month_attendance.values('status').annotate(total=Count('id'))
    }
    month_recorded = month_attendance.exclude(status=AttendanceRecord.Status.NOT_RECORDED).count()
    month_attended = sum(month_by_status.get(status, 0) for status in (
        AttendanceRecord.Status.PRESENT,
        AttendanceRecord.Status.LATE,
        AttendanceRecord.Status.SCHOOL_ACTIVITY,
    ))
    month_absences = sum(month_by_status.get(status, 0) for status in (
        AttendanceRecord.Status.ABSENT_EXCUSED,
        AttendanceRecord.Status.ABSENT_UNEXCUSED,
    ))
    seven_day_start = today - timedelta(days=6)
    daily_rows = attendance.filter(date__range=(seven_day_start, today)).values('date', 'status').annotate(total=Count('id'))
    daily_lookup = {}
    for row in daily_rows:
        daily_lookup.setdefault(row['date'], {})[row['status']] = row['total']
    seven_day_trend = []
    for offset in range(7):
        day = seven_day_start + timedelta(days=offset)
        counts = daily_lookup.get(day, {})
        seven_day_trend.append({
            'date': day,
            'label': day.strftime('%a'),
            'present': counts.get(AttendanceRecord.Status.PRESENT, 0),
            'late': counts.get(AttendanceRecord.Status.LATE, 0),
            'absent': counts.get(AttendanceRecord.Status.ABSENT_EXCUSED, 0)
            + counts.get(AttendanceRecord.Status.ABSENT_UNEXCUSED, 0),
            'school_activity': counts.get(AttendanceRecord.Status.SCHOOL_ACTIVITY, 0),
        })
    metrics = {
        'active_students': students.count(),
        'attendance_recorded_today': today_attendance.count(),
        'present_today': attendance_by_status.get(AttendanceRecord.Status.PRESENT, 0),
        'late_today': attendance_by_status.get(AttendanceRecord.Status.LATE, 0),
        'absent_today': (
            attendance_by_status.get(AttendanceRecord.Status.ABSENT_EXCUSED, 0)
            + attendance_by_status.get(AttendanceRecord.Status.ABSENT_UNEXCUSED, 0)
        ),
        'month_attendance_rate': round(month_attended * 100 / month_recorded, 1) if month_recorded else 0,
        'month_absences': month_absences,
        'high_risk_records': risk_assessments.filter(
            level=RiskAssessment.Level.HIGH,
            review_decision=RiskAssessment.ReviewDecision.CONFIRMED,
        ).count(),
        'pending_risk_reviews': risk_assessments.filter(
            review_decision=RiskAssessment.ReviewDecision.PENDING
        ).count(),
        'open_interventions': interventions.filter(status__in=open_intervention_statuses).count(),
        'sms_sent': sms_logs.filter(status__in=[SMSLog.Status.SENT, SMSLog.Status.DELIVERED]).count(),
        'active_accounts': get_user_model().objects.filter(is_active=True).count()
        if user.role == user.Role.ADMIN or user.is_superuser else None,
    }
    cards_by_role = {
        user.Role.ADMIN: [
            ('active_accounts', 'Active Accounts', 'Users allowed to sign in', '#5e35b1'),
            ('active_students', 'Active Students', 'Student profiles under monitoring', '#3949ab'),
            ('month_attendance_rate', 'Monthly Attendance', 'Recorded attendance rate this month', '#1e88e5'),
            ('high_risk_records', 'Confirmed High Priority', 'Human-reviewed support indicators', '#d81b60'),
            ('pending_risk_reviews', 'Pending Risk Reviews', 'Draft scores awaiting validation', '#8e24aa'),
            ('open_interventions', 'Open Interventions', 'Active support cases', '#00897b'),
            ('sms_sent', 'SMS Sent', 'Sent or delivered messages', '#6d4c41'),
        ],
        user.Role.TEACHER: [
            ('active_students', 'Assigned Students', 'Students in your scheduled classes', '#5e35b1'),
            ('month_attendance_rate', 'Monthly Attendance', 'Assigned-class attendance rate', '#1e88e5'),
            ('late_today', 'Late Today', 'Assigned students marked late', '#fb8c00'),
            ('absent_today', 'Absent Today', 'Assigned students marked absent', '#e53935'),
            ('high_risk_records', 'Confirmed High Priority', 'Reviewed indicators for assigned students', '#d81b60'),
            ('open_interventions', 'Open Interventions', 'Support cases for assigned students', '#00897b'),
        ],
        user.Role.STUDENT: [
            ('month_attendance_rate', 'Monthly Attendance', 'Your recorded attendance rate', '#1e88e5'),
            ('present_today', 'Present Today', 'Classes marked present', '#43a047'),
            ('late_today', 'Late Today', 'Classes marked late', '#fb8c00'),
            ('absent_today', 'Absent Today', 'Excused and unexcused records', '#e53935'),
            ('high_risk_records', 'Support Indicators', 'Your reviewed high-priority records', '#d81b60'),
            ('open_interventions', 'Support Cases', 'Your active intervention cases', '#00897b'),
        ],
        user.Role.PARENT: [
            ('active_students', 'Linked Children', 'Students linked to your account', '#5e35b1'),
            ('month_attendance_rate', 'Monthly Attendance', 'Linked students’ attendance rate', '#1e88e5'),
            ('late_today', 'Late Today', 'Linked students marked late', '#fb8c00'),
            ('absent_today', 'Absent Today', 'Linked students marked absent', '#e53935'),
            ('open_interventions', 'Support Cases', 'Active cases involving linked students', '#00897b'),
            ('sms_sent', 'SMS Sent', 'Notifications recorded for linked students', '#6d4c41'),
        ],
        user.Role.GUIDANCE: [
            ('active_students', 'Students Monitored', 'Active student population', '#5e35b1'),
            ('high_risk_records', 'Confirmed High Priority', 'Human-reviewed support indicators', '#d81b60'),
            ('pending_risk_reviews', 'Pending Risk Reviews', 'Draft scores awaiting validation', '#8e24aa'),
            ('open_interventions', 'Open Interventions', 'Active support cases', '#00897b'),
            ('month_attendance_rate', 'Monthly Attendance', 'Recorded student attendance rate', '#1e88e5'),
            ('late_today', 'Late Today', 'Students marked late', '#fb8c00'),
            ('absent_today', 'Absent Today', 'Students marked absent', '#e53935'),
        ],
    }
    card_definitions = cards_by_role[user.Role.ADMIN] if user.is_superuser else cards_by_role.get(
        user.role, cards_by_role[user.Role.STUDENT]
    )

    return Response({
        'success': True,
        'as_of': today,
        'user': user_payload(request.user),
        'metrics': metrics,
        'metric_cards': [
            {
                'key': key, 'label': label, 'note': note, 'color': color, 'value': metrics[key],
                'format': 'percent' if key.endswith('_rate') else 'number',
            }
            for key, label, note, color in card_definitions
        ],
        'attendance_overview': {
            'month': today.strftime('%Y-%m'),
            'month_label': today.strftime('%B %Y'),
            'recorded': month_recorded,
            'attended': month_attended,
            'absences': month_absences,
            'attendance_rate': metrics['month_attendance_rate'],
            'seven_day_trend': seven_day_trend,
        },
        'capabilities': {
            'manage_users': user.role == user.Role.ADMIN or user.is_superuser,
            'encode_attendance': user.role in (user.Role.ADMIN, user.Role.TEACHER),
            'review_sensitive_risk': user.role in (user.Role.ADMIN, user.Role.GUIDANCE),
        },
    })
