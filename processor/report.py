from django.conf import settings
from django.core.mail import send_mail
import django.utils.timezone as tz
from processor.mail_utils import get_username_from_address
from mailserver.models import Account
from processor.models import EmailGist, EmailGistReport

def get_report_path(report: EmailGistReport):
    return f'{settings.GIST_REPORT_PREFIX}/{get_username_from_address(report.smtp_to)}/{settings.GIST_REPORT_FOLDER}/{report.generated}'

def write_report_email(report: EmailGistReport):
    done = u'\u2714'
    incomplete = "" #u'\u2716'
    gists = [
        f'''
            <tr>
                <td>{done if gist.complete else incomplete}</td>
                <td>{gist.category}</td>
                <td>{gist.sender}</td>
                <td>{gist.gist}</td>
            </tr>
        ''' for gist in report.gists
    ]
    html = f'''
        <html>
            <head>
                <title>GIST Report for {tz.now().date()}</title>
            </head>
            <body>
                <table>
                    <tr>
                        <th>Complete</th>
                        <th>Category</th>
                        <th>Sender</th>
                        <th>Gist</th>
                    </tr>
                    {"".join(gists)}
                </table>
            </body>
        </html>'''
    with open(report.location, 'w+') as content:
        content.write(html)
        content.close()

def create_report_email(account: Account, gists: [EmailGist]):
    report = EmailGistReport.objects.create(
        account=account,
        smtp_to=account.get_report_destination(),
        location=settings.GIST_REPORT_PREFIX,
        emails=gists
    )
    report.location = write_report_email(report)
    report.save()
    write_report_email(report)
    return report

def send_report_email(report: EmailGistReport):
    with open(report.location, 'r') as content:
        subject = f'GIST Report for {tz.now().date()}'
        message = content.read()
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [report.smtp_to, ]
        send_mail( subject, message, email_from, recipient_list )
    report.sent = tz.now()

def report(account: Account, gists: [EmailGist]):
    if account.report_email:
        report = create_report_email(account, gists)
        send_report_email(report)