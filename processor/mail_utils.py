import html2text
import mailbox
from enum import Enum
from django.conf import settings
import os
import base64
from mailserver.models import VirtualUser


# Custom exception
class InvalidMailPathException(Exception):
    pass

# Make sure the path is valid
def validate_mail_path(path: str):
    if not (os.path.exists(path) and path.startswith(settings.MAILDIR_PREFIX)):
        return InvalidMailPathException

# ex: 'sample@gist.email' -> 'sample'
def get_username_from_address(address: str):
    return address.split('@')[0]

# ex: 'sample@gist.email' -> <mailserver.models.VirtualUser>
def get_virtual_user_from_address(address: str):
    return VirtualUser.objects.get(email=address)

# ex: '/var/vmail/gist.email/user/Maildir' or '/var/vmail/gist.email/user/Maildir/INBOX.Marketing/cur/1696304003.M382939P108930.gist,S=350,W=362'
def get_maildir_path(user: str, folders: [str] = [], subdir: str = None, filename: str = None):
    base = f'{settings.MAILDIR_PREFIX}/{user}/{settings.MAILDIR_NAME}/'
    for i in range(0, len(folders)):
        base += f'.{".".join(folders[0:i+1])}/'
    if subdir:
        base += f'{subdir}/'
    if filename:
        base += f'{filename}'
    if os.path.exists(base):
        return base
    else:
        raise Exception

# Flags for messages (standard + GISTED & DELTE)
class Flags(Enum):
    DRAFT   = 'D'
    FLAGGED = 'F'
    PASSED  = 'P'
    REPLIED = 'R'
    SEEN    = 'S'
    TRASHED = 'T'
    GISTED  = 'G'
    DELETE  = 'X'

# Utility to explore and manipulate messages
class Message:
    def __init__(self, user: str, folder: str, filename: str, message: mailbox.MaildirMessage):
        self.user = user
        self.folder = folder
        self.filename = filename
        self.message = message
        self.maildir = self.get_maildir()
        self.to = self.message.get('To')
        self.sender = self.message.get('From')
        self.subject = self.message.get('Subject')
        self.content = self.extract_text()

    def get_maildir(self, **kwargs):
        user = kwargs.get('user', self.user)
        folder = kwargs.get('folder', self.folder)
        return mailbox.Maildir(get_maildir_path(user, [folder]))

    def get_path(self):
        return get_maildir_path(self.user, [self.folder], self.message.get_subdir(), self.filename)

    def get_flags(self):
        return self.message.get_flags()

    def has_flag(self, flag: Flags):
        return flag.value in self.get_flags()

    def set_flags(self, *flags: Flags, **kwargs):
        flags = [flag.value for flag in flags if type(flag) == Flags]
        updated_message = self.message
        if kwargs.get('override', False):
            flags = ''.join(flags)
            updated_message.set_flags(flags)
        else:
            for flag in flags:
                updated_message.add_flag(flag)
        self.maildir.update([(self.filename, updated_message)])
        self.message = updated_message
        self.maildir = self.get_maildir()

    def mark_as_processed(self, **kwargs: str):
        folder = kwargs.get('folder', self.folder)
        if folder != self.folder:
            old_maildir = self.get_maildir()
            new_maildir = self.get_maildir(folder=folder)
            new_message = new_maildir.add(self.message)
            new_maildir.update([(self.filename, new_message)])
            old_maildir.remove(self.message)
            self = self.__init__(self.user, folder, self.filename, new_message)
        new_message = self.message
        new_message.set_subdir('cur')
        self.maildir.update([(self.filename, new_message)])
        self.message = new_message
        self.maildir = self.get_maildir()
        self.set_flags(Flags.GISTED)

    # Convert HTML email into plaintext to save on OpenAI tokens
    def extract_text(self):
        converter = html2text.HTML2Text()
        converter.ignore_links      = True
        converter.ignore_images     = True
        message = self.message if not self.message.is_multipart() else self.message.get_payload(i=0)
        payload = message.get_payload()
        if message.get('Content-Transfer-Encoding') == 'base64':
            payload = base64.b64decode(payload).decode()
        return converter.handle(payload)

# Utility to explore and manipulate Maildir
class Maildir:
    def __init__(self, user: str):
        try:
            self.user: str = user
            self.root: str = get_maildir_path(user)
            self.path: str = self.root
            self.foldername: str = self.path.removeprefix(self.root)
            self.maildir: mailbox.Maildir = mailbox.Maildir(self.path)
            self.current_folder = self.maildir
            self.uidvalidity: str = self.get_uidvailidity()
        except InvalidMailPathException:
            print(f'Could not find a mailbox for user "{user}".')

    def get_uidvailidity(self):
        if os.path.exists(self.path + 'dovecot-uidlist'):
            return self.read_uidlist().get('uidvalidity')
        else:
            return None

    def get_folders(self):
        return self.maildir.list_folders()

    def set_folder(self, foldername=None):
        if foldername in self.get_folders():
            self.path = get_maildir_path(self.user, [foldername])
            self.current_folder = self.maildir.get_folder(foldername)
        elif foldername is None:
            self.path = get_maildir_path(self.user)
            self.current_folder = self.maildir
        else:
            print(f'No folder "{foldername}" exists for {self.user}.')

    def add_folders(self, *folders):
        for folder in folders:
            if folder not in self.get_folders():
                self.current_folder.add_folder(folder)
                print(folder, end='')

    def read_uidlist(self):
        messages = {}
        with open(self.path + 'dovecot-uidlist', 'r') as uidlist:
            uids = uidlist.readlines()
            header = uids[0]
            entries = uids[1:]
            uidlist.close()
        messages.update({'uidvalidity': str(header.split(' ')[1][1:])})
        for entry in entries:
            messages.update({int(entry.split(' ')[0]): entry.split(':')[-1].strip('\n')})
        if messages:
            return messages
        raise InvalidMailPathException

    def get_messages(self):
        try:
            foldername = self.path.split('/')[-1]
            return [Message(self.user, foldername, message[0], message[1]) for message in self.current_folder.items()]
        except FileNotFoundError:
            return []

    def get_message(self, uid: int):
        try:
            filename = self.read_uidlist()[int(uid)]
            message = [option for option in self.get_messages() if filename in option.filename]
            if message:
                return message[0]
            else:
                print(f'No file with name {filename} exists.')
                raise InvalidMailPathException
        except:
            raise InvalidMailPathException

    def get_message_path(self, filename: str):
        paths = [f'{m[1].get_subdir()}/{m[0]}' for m in self.maildir.items()]
        for path in paths:
            if filename in path:
                return f'{self.path}/{filename}'
        raise InvalidMailPathException

# Find the message reported by `push.lua` push notification
def get_message(user: str, folder: str, uid: int, uidvalidity: str):
    mdir = Maildir(user)
    mdir.set_folder(folder)
    if mdir.get_uidvailidity() == uidvalidity:
        return mdir.get_message(uid)
    else:
        raise InvalidMailPathException