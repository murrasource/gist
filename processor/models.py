from django.db import models
from django.conf import settings
from mailserver.models import *

class Email(models.Model):
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="emails")
    smtp_to     = models.ForeignKey(VirtualUser, on_delete=models.CASCADE, related_name="emails")
    smtp_from   = models.CharField(max_length=100)
    location    = models.FilePathField(path=settings.MAILDIR_PREFIX, max_length=1000)
    received    = models.DateTimeField(auto_now_add=True)
    processed   = models.DateTimeField(null=True, default=None)
    
class EmailGist(models.Model):
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="gists")
    email       = models.OneToOneField(Email, on_delete=models.CASCADE, related_name="gist")
    complete    = models.BooleanField(default=True)
    action      = models.BooleanField(default=False)
    category    = models.CharField(max_length=50)
    sender      = models.CharField(max_length=100)
    gist        = models.TextField(max_length=500)

class EmailGistReport(models.Model):
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="reports")
    smtp_to     = models.EmailField()
    location    = models.FilePathField(path=settings.GIST_REPORT_PREFIX)
    emails      = models.ManyToManyField(Email, related_name='reports')
    gists       = models.ManyToManyField(EmailGist, related_name='reports')
    generated   = models.DateTimeField(auto_now_add=True)
    sent        = models.DateTimeField(null=True, default=None)