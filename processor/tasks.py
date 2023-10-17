from celery import shared_task
from django.conf import settings
from mailserver.models import Account, VirtualUser
from processor import mail_utils
from processor.gist import generate_email_gist
from processor.report import report

@shared_task
def process_new_message(message: mail_utils.Message):
    user: VirtualUser = mail_utils.get_virtual_user_from_address(message.to)
    if not message.has_flag(mail_utils.Flags.GISTED) and not settings.DEBUG:
        gist = generate_email_gist(user, message)
        if gist:
            message.mark_as_processed()
            if gist.category == "MFA & Security Alerts" and gist.account.report_email:
                report(gist.account, [gist])

@shared_task
def send_daily_gist_report(account: Account):
    if account.report_email and not settings.DEBUG:
        gists = [gist for gist in account.gists if gist.reports.count < 1 or not gist.complete]
        report(account, gists)

