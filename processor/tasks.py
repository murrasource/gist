from celery import shared_task
from django.conf import settings
from mailserver.models import Account, VirtualUser
from processor import mail_utils
from processor.gist import generate_email_gist
from processor.report import report

@shared_task
def process_new_message(user: str, folder: str, uid: int, uidvalidity: str):
    print(f'Processing new message -- user: {user}, folder: {folder}, uid: {uid}, uidvalidity: {uidvalidity}')
    message = mail_utils.get_message(user, folder, uid, uidvalidity)
    user: VirtualUser = VirtualUser.objects.get(email=user)
    if message.has_flag(mail_utils.Flags.GISTED):
        print(f'Message with uid {uid} for user {user} already processed.')
        return
    if settings.DEBUG:
        print(f'Not processing message with uid {uid} for user {user} because DEBUG=TRUE')
        return
    gist = generate_email_gist(user, message)
    if gist:
        message.mark_as_processed()
        if gist.category == "Security" and gist.account.report_email:
            report(gist.account, [gist])

@shared_task
def send_gist_report(account_id):
    account = Account.objects.get(id=account_id)
    if account.report_email and not settings.DEBUG:
        gists = [gist for gist in account.gists.all() if gist.reports.count() < 1 or not gist.complete]
        report(account, gists)

@shared_task
def process_ungisted_emails():
    for account in Account.objects.all():
        user = mail_utils.get_username_from_address(account.virtual_user.email)
        maildir = mail_utils.Maildir(user)
        maildir.set_folder('INBOX')
        messages = [message for message in maildir.get_messages() if not message.has_flag(mail_utils.Flags.GISTED)]
        for message in messages:
            folder = 'INBOX'
            uid = message.maildir.get_uid(message.filename)
            uidvalidity = message.maildir.get_uidvailidity()
            print(f'Queueing new message -- user: {account.virtual_user.email}, folder: {folder}, uid: {uid}, uidvalidity: {uidvalidity}')
            process_new_message.apply_async(args=(account.virtual_user.email, folder, uid, uidvalidity), countdown=60)