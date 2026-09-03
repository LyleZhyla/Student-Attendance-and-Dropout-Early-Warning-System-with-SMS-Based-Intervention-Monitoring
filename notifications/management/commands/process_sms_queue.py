from django.core.management.base import BaseCommand

from notifications.models import SMSLog
from notifications.services import send_sms


class Command(BaseCommand):
    help = 'Send queued SMS notifications and retry eligible failed messages.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        from django.conf import settings

        max_retries = int(getattr(settings, 'SMS_MAX_RETRIES', 3))
        ids = list(SMSLog.objects.filter(status=SMSLog.Status.QUEUED).values_list('pk', flat=True)[:options['limit']])
        remaining = max(0, options['limit'] - len(ids))
        if remaining:
            ids.extend(SMSLog.objects.filter(
                status=SMSLog.Status.FAILED, retry_count__lt=max_retries
            ).values_list('pk', flat=True)[:remaining])
        sent = failed = 0
        for log_id in ids:
            log = send_sms(log_id)
            if log.status == SMSLog.Status.FAILED:
                failed += 1
            elif log.status in (SMSLog.Status.SENT, SMSLog.Status.DELIVERED):
                sent += 1
        self.stdout.write(self.style.SUCCESS(f'Processed {len(ids)} notification(s): {sent} sent, {failed} failed.'))
