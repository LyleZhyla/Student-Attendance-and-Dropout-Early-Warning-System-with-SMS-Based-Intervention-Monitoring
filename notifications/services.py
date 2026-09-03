from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import SMSLog
from .providers import get_provider


def mask_mobile(number):
    compact = ''.join(character for character in str(number) if character.isdigit() or character == '+')
    if len(compact) <= 4:
        return '*' * len(compact)
    return f'{compact[:3]}{"*" * max(4, len(compact) - 7)}{compact[-4:]}'


def queue_sms(*, student, guardian, category, message, event_key, created_by=None):
    log = SMSLog(
        student=student,
        guardian=guardian,
        category=category,
        message=message.strip(),
        recipient_masked=mask_mobile(guardian.mobile_number),
        event_key=event_key,
        created_by=created_by,
    )
    log.full_clean()
    log.save()
    return log


def send_sms(log_id, provider=None):
    max_retries = int(getattr(settings, 'SMS_MAX_RETRIES', 3))
    with transaction.atomic():
        log = SMSLog.objects.select_for_update().select_related('guardian').get(pk=log_id)
        if log.status in (SMSLog.Status.SENDING, SMSLog.Status.SENT, SMSLog.Status.DELIVERED, SMSLog.Status.CANCELLED):
            return log
        if log.status == SMSLog.Status.FAILED and log.retry_count >= max_retries:
            return log
        if (
            not log.guardian.sms_consent
            or not log.guardian.mobile_verified
            or not log.guardian.students.filter(pk=log.student_id).exists()
        ):
            log.status = SMSLog.Status.CANCELLED
            log.error_message = 'Recipient is no longer eligible for SMS notifications.'
            log.save(update_fields=('status', 'error_message', 'updated_at'))
            return log
        log.status = SMSLog.Status.SENDING
        log.last_attempted_at = timezone.now()
        log.error_message = ''
        log.save(update_fields=('status', 'last_attempted_at', 'error_message', 'updated_at'))

    try:
        result = (provider or get_provider()).send(log.guardian.mobile_number, log.message)
    except Exception as error:  # provider errors must be retained for retry and audit
        log.status = SMSLog.Status.FAILED
        log.retry_count += 1
        log.error_message = str(error)[:1000]
        log.save(update_fields=('status', 'retry_count', 'error_message', 'updated_at'))
        return log

    now = timezone.now()
    log.provider_reference = str(result.get('reference', ''))[:100]
    log.sent_at = now
    if result.get('delivered'):
        log.status = SMSLog.Status.DELIVERED
        log.delivered_at = now
    else:
        log.status = SMSLog.Status.SENT
    log.save(update_fields=('provider_reference', 'sent_at', 'status', 'delivered_at', 'updated_at'))
    return log


def queue_attendance_notifications(record, created_by=None):
    if not getattr(settings, 'SMS_AUTO_ATTENDANCE_NOTIFICATIONS', False):
        return []
    event_prefix = f'attendance:{record.pk}:'
    if record.status != record.Status.ABSENT_UNEXCUSED:
        SMSLog.objects.filter(
            event_key__startswith=event_prefix,
            status__in=(SMSLog.Status.QUEUED, SMSLog.Status.FAILED),
        ).update(status=SMSLog.Status.CANCELLED, error_message='Cancelled after attendance was corrected.')
        return []
    queued = []
    links = record.student.studentguardian_set.filter(
        guardian__sms_consent=True, guardian__mobile_verified=True
    ).select_related('guardian')
    for link in links:
        event_key = f'attendance:{record.pk}:{link.guardian_id}:{record.status}'
        log, created = SMSLog.objects.get_or_create(
            event_key=event_key,
            defaults={
                'student': record.student,
                'guardian': link.guardian,
                'category': SMSLog.Category.ATTENDANCE,
                'message': (
                    f'TardyTrack attendance notice: {record.student.first_name} was marked '
                    f'unexcused absent on {record.date:%B %d, %Y}. Please contact the school for details.'
                ),
                'recipient_masked': mask_mobile(link.guardian.mobile_number),
                'created_by': created_by,
            },
        )
        if not created and log.status == SMSLog.Status.CANCELLED:
            log.status = SMSLog.Status.QUEUED
            log.error_message = ''
            log.retry_count = 0
            log.save(update_fields=('status', 'error_message', 'retry_count', 'updated_at'))
            created = True
        if created:
            queued.append(log)
    return queued
