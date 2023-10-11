from django.contrib import admin
from processor.models import Email, EmailGist, EmailGistReport

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['id', 'smtp_to', 'smtp_from', 'location', 'received', 'processed']

@admin.register(EmailGist)
class EmailGistAdmin(admin.ModelAdmin):
    list_display = ['id', 'action', 'category', 'sender', 'gist']

@admin.register(EmailGistReport)
class EmailGistReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'smtp_to', 'location', 'generated', 'sent']
