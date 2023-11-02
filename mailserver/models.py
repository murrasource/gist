from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('You must select a GIST email address.'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Account(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account")
    dob             = models.DateField(null=True)
    report_email    = models.EmailField(blank=True, null=True)
    report_settings = models.JSONField(blank=True, null=True)
    report_schedule = models.OneToOneField(PeriodicTask, related_name='account', on_delete=models.CASCADE, blank=True, null=True)

    def set_report_schedule(self, minute: str = '0', hour: str = '12', DoW: str = '*', DoM: str = '*', MoY: str = '*'):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_week=DoW,
            day_of_month=DoM,
            month_of_year=MoY,
        )
        report_schedule, _ = PeriodicTask.objects.get_or_create(
            name=f'Gist report schedule for {self.user.email}'
        )
        report_schedule.crontab = schedule
        report_schedule.task = 'processor.tasks.send_gist_report'
        report_schedule.args = json.dumps([self.id])
        report_schedule.enabled = True
        report_schedule.save()
        self.report_schedule = report_schedule

    class Meta:
        db_table = "gist_accounts"


class VirtualDomain(models.Model):
    name        = models.CharField(max_length=50, null=False)

    class Meta:
        db_table = "virtual_domains"


class VirtualUser(models.Model):
    account     = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="virtual_user")
    domain      = models.ForeignKey(VirtualDomain, on_delete=models.CASCADE, null=False)
    email       = models.EmailField(null=False)
    password    = models.CharField(max_length=150, null=False)
    quota       = models.BigIntegerField(default=0, null=False)

    class Meta:
        db_table = "virtual_users"


class VirtualAlias(models.Model):
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="virtual_aliases")
    domain      = models.ForeignKey(VirtualDomain, on_delete=models.CASCADE, null=False)
    source      = models.CharField(max_length=100, null=False)
    destination = models.CharField(max_length=100, null=False)

    class Meta:
        db_table = "virtual_aliases"