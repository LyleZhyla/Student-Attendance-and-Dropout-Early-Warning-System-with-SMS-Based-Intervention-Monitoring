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
    return Response({'success': True, 'token': token.key, 'user': user_payload(user)})


@api_view(['POST'])
def logout_api(request):
    if request.auth:
        request.auth.delete()
    return Response({'success': True})


@api_view(['GET'])
def me_api(request):
    return Response({'success': True, 'user': user_payload(request.user)})


@api_view(['GET'])
def dashboard_summary(request):
    today = timezone.localdate()
    today_attendance = AttendanceRecord.objects.filter(date=today)
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
    return Response({
        'success': True,
        'as_of': today,
        'user': user_payload(request.user),
        'metrics': {
            'active_students': Student.objects.filter(is_active=True).count(),
            'attendance_recorded_today': today_attendance.count(),
            'present_today': attendance_by_status.get(AttendanceRecord.Status.PRESENT, 0),
            'late_today': attendance_by_status.get(AttendanceRecord.Status.LATE, 0),
            'absent_today': (
                attendance_by_status.get(AttendanceRecord.Status.ABSENT_EXCUSED, 0)
                + attendance_by_status.get(AttendanceRecord.Status.ABSENT_UNEXCUSED, 0)
            ),
            'high_risk_records': RiskAssessment.objects.filter(level=RiskAssessment.Level.HIGH).count(),
            'open_interventions': InterventionCase.objects.filter(status__in=open_intervention_statuses).count(),
            'sms_sent': SMSLog.objects.filter(status__in=[SMSLog.Status.SENT, SMSLog.Status.DELIVERED]).count(),
        },
    })
