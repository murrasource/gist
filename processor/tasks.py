from celery import shared_task
from mailserver.models import Account, VirtualUser
from processor.mail_utils import Message, Flags
from processor.gist import generate_email_gist
from processor.report import report

@shared_task
def process_new_message(user, message):
    # Get Virtual User
    user: VirtualUser
    # Get Message
    message: Message

    if not message.has_flag(Flags.GISTED):
        gist = generate_email_gist(user, message)
        message.mark_as_processed()
        if gist.category == "MFA & Security Alerts" and gist.account.report_email:
            report(gist.account, [gist])

@shared_task
def send_daily_gist_report(account: Account):
    if account.report_email:
        gists = [gist for gist in account.gists if gist.reports.count < 1 or not gist.complete]
        report(account, gists)

