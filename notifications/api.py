from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsAdministrator
from audit_logs.models import AuditLog
from students.models import StudentGuardian

from .models import SMSLog
from .serializers import SMSCreateSerializer, SMSLogSerializer
from .services import queue_sms, send_sms


def audit(request, action, log, summary):
    AuditLog.objects.create(
        actor=request.user,
        action=action,
        object_type=log._meta.label,
        object_id=str(log.pk),
        summary=summary,
        metadata={'event_key': log.event_key, 'status': log.status, 'student_id': log.student_id},
        ip_address=request.META.get('REMOTE_ADDR'),
    )


@api_view(['GET'])
@permission_classes([IsAdministrator])
def sms_options_api(request):
    links = StudentGuardian.objects.select_related('student', 'guardian').filter(
        student__is_active=True
    ).order_by('student__last_name', 'student__first_name', '-is_primary', 'guardian__full_name')
    recipients = []
    for link in links:
        reasons = []
        if not link.guardian.mobile_verified:
            reasons.append('Mobile number is not verified')
        if not link.guardian.sms_consent:
            reasons.append('SMS consent is not recorded')
        recipients.append({
            'student': link.student_id,
            'student_name': str(link.student),
            'guardian': link.guardian_id,
            'guardian_name': link.guardian.full_name,
            'is_primary': link.is_primary,
            'eligible': not reasons,
            'ineligible_reason': '; '.join(reasons),
        })
    return Response({
        'success': True,
        'recipients': recipients,
        'categories': [{'value': value, 'label': label} for value, label in SMSLog.Category.choices],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAdministrator])
def sms_logs_api(request):
    if request.method == 'POST':
        serializer = SMSCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        link = StudentGuardian.objects.select_related('student', 'guardian').filter(
            student_id=values['student'], guardian_id=values['guardian'], student__is_active=True
        ).first()
        if not link:
            return Response({'message': 'Guardian and active student are not linked.'}, status=400)
        try:
            with transaction.atomic():
                log = queue_sms(
                    student=link.student, guardian=link.guardian, category=values['category'],
                    message=values['message'], event_key=values['event_key'], created_by=request.user,
                )
        except IntegrityError:
            return Response({'message': 'A notification with this event key already exists.'}, status=409)
        except ValidationError as error:
            if 'event_key' in getattr(error, 'message_dict', {}):
                return Response({'message': 'A notification with this event key already exists.'}, status=409)
            messages = getattr(error, 'message_dict', {})
            return Response({'message': ' '.join(item for values in messages.values() for item in values)}, status=400)
        audit(request, 'SMS_QUEUED', log, f'Queued {log.get_category_display()} SMS for {log.student}.')
        return Response({'success': True, 'record': SMSLogSerializer(log).data}, status=201)

    logs = SMSLog.objects.select_related('student', 'guardian', 'created_by')
    status_filter = request.query_params.get('status', '').strip()
    search = request.query_params.get('search', '').strip()
    if status_filter:
        if status_filter not in SMSLog.Status.values:
            return Response({'message': 'Choose a valid SMS status.'}, status=400)
        logs = logs.filter(status=status_filter)
    if search:
        logs = logs.filter(
            Q(student__first_name__icontains=search) | Q(student__last_name__icontains=search)
            | Q(guardian__full_name__icontains=search) | Q(event_key__icontains=search)
        )
    totals = {row['status']: row['total'] for row in SMSLog.objects.values('status').annotate(total=Count('id'))}
    return Response({
        'success': True,
        'records': SMSLogSerializer(logs[:500], many=True).data,
        'summary': {'total': sum(totals.values()), **{value: totals.get(value, 0) for value, _ in SMSLog.Status.choices}},
        'statuses': [{'value': value, 'label': label} for value, label in SMSLog.Status.choices],
    })


@api_view(['POST'])
@permission_classes([IsAdministrator])
def sms_send_api(request, record_id):
    log = SMSLog.objects.filter(pk=record_id).first()
    if not log:
        return Response({'message': 'SMS notification not found.'}, status=404)
    if log.status in (SMSLog.Status.SENT, SMSLog.Status.DELIVERED):
        return Response({'message': 'This notification has already been sent.'}, status=409)
    from django.conf import settings
    if log.status == SMSLog.Status.FAILED and log.retry_count >= int(getattr(settings, 'SMS_MAX_RETRIES', 3)):
        return Response({'message': 'Maximum retry attempts have been reached.'}, status=409)
    log = send_sms(log.pk)
    action = 'SMS_SEND_FAILED' if log.status == SMSLog.Status.FAILED else 'SMS_SENT'
    if log.status == SMSLog.Status.CANCELLED:
        action = 'SMS_CANCELLED'
    audit(request, action, log, f'SMS for {log.student} changed to {log.get_status_display()}.')
    response_status = 502 if log.status == SMSLog.Status.FAILED else 409 if log.status == SMSLog.Status.CANCELLED else 200
    return Response({
        'success': log.status in (SMSLog.Status.SENT, SMSLog.Status.DELIVERED),
        'message': log.error_message or None,
        'record': SMSLogSerializer(log).data,
    }, status=response_status)
