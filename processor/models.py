from django.db import models
from django.conf import settings
from mailserver.models import *
from processor import mail_utils
import uuid

class Email(models.Model):
    uuid        = models.UUIDField(null=False, default=uuid.uuid4, unique=True)
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="emails")
    smtp_to     = models.ForeignKey(VirtualUser, on_delete=models.CASCADE, related_name="emails")
    smtp_from   = models.CharField(max_length=100)
    location    = models.FilePathField(path=settings.MAILDIR_PREFIX, max_length=1000)
    received    = models.DateTimeField(auto_now_add=True)
    processed   = models.DateTimeField(null=True, default=None)

    def get_message(self):
        user = self.location.removeprefix(settings.MAILDIR_PREFIX).strip('/').split('/')[0]
        parts = [part.strip('.') for part in self.location.removeprefix(mail_utils.get_maildir_path(user)).strip('/').split('/')]
        folders = parts[:-2]
        filename = parts[-1].split(':')[0]
        maildir = mail_utils.Maildir(user)
        for folder in folders:
            maildir.set_folder(foldername=folder)
        return maildir.get_message(filename=filename)

    def view(self):
        message = self.get_message()
        return message.get_url_view()
    
    def reply(self):
        message = self.get_message()
        return message.get_url_reply()
        
    def replyall(self):
        message = self.get_message()
        return message.get_url_replyall()
        
    def forward(self):
        message = self.get_message()
        return message.get_url_forward()
    
class EmailGist(models.Model):
    uuid        = models.UUIDField(null=False, default=uuid.uuid4, unique=True)
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="gists")
    email       = models.OneToOneField(Email, on_delete=models.CASCADE, related_name="gist")
    complete    = models.BooleanField(default=True)
    action      = models.BooleanField(default=False)
    category    = models.CharField(max_length=50)
    sender      = models.CharField(max_length=100)
    gist        = models.TextField(max_length=500)

class EmailGistReport(models.Model):
    uuid        = models.UUIDField(null=False, default=uuid.uuid4, unique=True)
    account     = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="reports")
    smtp_to     = models.EmailField()
    subject     = models.CharField(max_length=100, blank=True, default="GIST Report")
    location    = models.FilePathField(path=settings.GIST_REPORT_PREFIX)
    emails      = models.ManyToManyField(Email, related_name='reports')
    gists       = models.ManyToManyField(EmailGist, related_name='reports')
    generated   = models.DateTimeField(auto_now_add=True)
    sent        = models.DateTimeField(null=True, default=None)