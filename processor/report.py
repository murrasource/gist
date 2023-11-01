from django.conf import settings
from django.core.mail import send_mail
import django.utils.timezone as tz
from processor.mail_utils import get_username_from_address
from mailserver.models import Account
from processor.models import EmailGist, EmailGistReport
from pathlib import Path
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def get_report_path(report: EmailGistReport):
    path = Path(f'{settings.GIST_REPORT_PREFIX}/{get_username_from_address(report.smtp_to)}/{settings.GIST_REPORT_FOLDER}/{report.uuid}')
    path.parent.mkdir(parents=True, exist_ok=True)
    return f'{settings.GIST_REPORT_PREFIX}/{get_username_from_address(report.smtp_to)}/{settings.GIST_REPORT_FOLDER}/{report.uuid}'

def write_report_email(report: EmailGistReport):
    html = render_to_string('report.html', {'gists': report.gists.all().order_by('complete')})
    with open(report.location, 'a+') as content:
        content.write(html)
        content.close()

def create_report_email(account: Account, gists: [EmailGist]):
    report = EmailGistReport.objects.create(
        account=account,
        smtp_to=account.report_email,
        location=settings.GIST_REPORT_PREFIX,
    )
    for gist in gists:
        report.gists.add(gist)
        report.emails.add(gist.email)
    report.location = get_report_path(report)
    report.save()
    write_report_email(report)
    return report

def send_report_email(report: EmailGistReport):
    with open(report.location, 'r') as content:
        subject = f'GIST Report for {tz.now().date()}' if len(report.gists.all()) > 1 else report.gists.first().gist
        html_content = content.read()
        text_content = strip_tags(html_content)
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [report.smtp_to, ]
        send_mail( subject, text_content, email_from, recipient_list, html_message=html_content )
        content.close()
        report.sent = tz.now()
        report.save()

def report(account: Account, gists: [EmailGist]):
    if account.report_email:
        report = create_report_email(account, gists)
        send_report_email(report)