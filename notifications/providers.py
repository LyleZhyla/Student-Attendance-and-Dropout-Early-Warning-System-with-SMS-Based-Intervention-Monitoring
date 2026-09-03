import uuid


class ConsoleSMSProvider:
    """Safe local provider that records a simulated provider acceptance."""

    def send(self, recipient, message):
        return {'reference': f'local-{uuid.uuid4().hex}', 'delivered': False}


def get_provider():
    from django.conf import settings
    from django.utils.module_loading import import_string

    provider_class = import_string(
        getattr(settings, 'SMS_PROVIDER_CLASS', 'notifications.providers.ConsoleSMSProvider')
    )
    return provider_class()
