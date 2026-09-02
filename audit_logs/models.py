from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events')
    action = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-occurred_at',)

# Create your models here.
