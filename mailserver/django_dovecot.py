from passlib.hash import bcrypt
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from mailserver.models import User, Account, VirtualDomain, VirtualUser, VirtualAlias
from processor.mail_utils import Maildir, Flags, get_username_from_address
from django.conf import settings

# Format a bcrypt hash in the dovecot format
def password_dovecot_format(hash: str):
    dovecot_prefix = '{BLF-CRYPT}'
    if hash.startswith(dovecot_prefix):
        return hash
    else:
        parts = hash.split('$')
        named_parts = {
            'algorithm': parts[0],
            'abbreviation': parts[2],
            'iterations': parts[3],
            'hash': parts[4]
        }
        return f'{dovecot_prefix}${named_parts["abbreviation"]}${named_parts["iterations"]}${named_parts["hash"]}'

# Format a bcrypt hash in the django format
def password_django_format(hash: str):
    django_prefix = 'bcrypt'
    if hash.startswith(django_prefix):
        return hash
    else:
        parts = hash.split('$')
        named_parts = {
            'abbreviation': '2y',
            'iterations': parts[2],
            'hash': parts[3]
        }
        return f'{django_prefix}$${named_parts["abbreviation"]}${named_parts["iterations"]}${named_parts["hash"]}'

# Verify password using hash
def verify_password(password: str, hash: str):
    hash = '$' + '$'.join(hash.split('$')[-3:])
    return bcrypt.verify(password, hash)

# Create VirtualUser, VirtualAlias, and Maildir when User is created
@receiver(post_save, sender=User)
def on_user_init(sender, **kwargs):
    user = kwargs.get('instance', None)
    created = kwargs.get('created', False)
    if user and user.email and user.password:
        gist_domain = VirtualDomain.objects.get_or_create(name='gist.email')[0]
        gist_domain.save()
        jist_domain = VirtualDomain.objects.get_or_create(name='jist.email')[0]
        jist_domain.save()
        account = Account.objects.get_or_create(user=user)[0]
        account.set_report_schedule()
        account.save()
        django_password = user.password
        vu = VirtualUser.objects.create(account=account, domain=gist_domain, email=user.email, password=password_dovecot_format(django_password)) if created else VirtualUser.objects.get(account=account)
        vu.password = password_dovecot_format(django_password)
        vu.save()
        va = VirtualAlias.objects.create(account=account, domain=jist_domain, source=f'{user.email.split("@")[0]}@jist.email', destination=user.email) if created else VirtualAlias.objects.get(account=account)
        va.save()
    if created and not settings.DEBUG:
        maildir = Maildir(user.email.split('@')[0])
        maildir.add_folders(*[f'INBOX.{folder}' for folder in settings.DEFAULT_FOLDERS])

# Flag user's emails for deletion when User is deleted
@receiver(post_delete, sender=User)
def on_user_delete(sender, **kwargs):
    user = kwargs.get('instance', None)
    if user and not settings.DEBUG:
        maildir = Maildir(get_username_from_address(user.email))
        for folder in maildir.get_folders():
            maildir.set_folder(folder)
            for message in maildir.get_messages():
                message.set_flags(Flags.DELETE)

# Update password for VirtualUser when User password is updated
# @receiver(post_save, sender=User)
# def on_user_save(sender, **kwargs):
#     user = kwargs.get('instance', None)
#     created = kwargs.get('created', None)
#     if user and not created:
#         django_password = user.password
#         dovecot_password = user.account.virtual_user.password
#         if django_password != password_django_format(dovecot_password):
#             user.account.virtual_user.password = password_dovecot_format(django_password)
#             user.account.virtual_user.save()
