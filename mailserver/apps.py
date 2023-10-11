from django.apps import AppConfig


class MailserverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mailserver'

    def ready(self):
        import mailserver.django_dovecot