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
def get_maildir_path(user: str, folders: [str] = [], subdir: str = None, filename: str = None, info: str = None):
    base = f'{settings.MAILDIR_PREFIX}/{user}/{settings.MAILDIR_NAME}/'
    if folders:
        for i in range(0, len(folders)):
            base += f'.{folders[i]}/'
    if subdir:
        base += f'{subdir}/'
    if filename:
        base += f'{filename}'
    if info:
        base += f':{info}'
    if os.path.exists(base):
        return base
    else:
        print(f'File does not exist: "{base}"')
        raise InvalidMailPathException


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
    def __init__(self, user: str, folder: list, filename: str, message: mailbox.MaildirMessage):
        self.user = user
        self.folder = folder
        self.filename = filename
        self.message = message
        self.maildir = self.get_maildir(*folder)
        self.to: str = self.message.get('Delivered-To')
        self.sender: str = self.message.get('From') if '<' not in self.message.get('From') else self.message.get('From').split('<')[1].strip('>')
        self.subject = self.message.get('Subject')
        self.content = self.extract_text()

    def get_maildir(self, *folders):
        maildir = Maildir(self.user)
        folders = [*folders] if folders else self.folder
        for folder in folders:
            maildir.set_folder(folder)
        return maildir

    def get_path(self):
        return get_maildir_path(self.user, self.folder, self.message.get_subdir(), self.filename, self.message.get_info())

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
        self.maildir.current_folder.update([(self.filename, updated_message)])
        self.message = updated_message
        self.maildir = self.get_maildir()

    def mark_as_processed(self, **kwargs: str):
        folder = kwargs.get('folder', self.folder)
        get_maildir_path(self.user, folders=folder)
        if folder != self.folder:
            old_maildir = self.get_maildir()
            old_maildir.current_folder.remove(self.filename)
            new_maildir = self.get_maildir(*folder)
            filename = new_maildir.current_folder.add(self.message)
            self.filename = filename
            self.maildir = new_maildir
            self.folder = folder
        new_message = self.message
        new_message.set_subdir('cur')
        self.maildir.current_folder.update([(self.filename, new_message)])
        self.message = new_message
        self.set_flags(Flags.GISTED)

    # Convert HTML email into plaintext to save on OpenAI tokens
    def extract_text(self):
        converter = html2text.HTML2Text()
        converter.ignore_links      = True
        converter.ignore_images     = True
        message = self.message if not self.message.is_multipart() else self.message.get_payload(i=0)
        while message.is_multipart():
            message = message if not message.is_multipart() else message.get_payload(i=0)
        payload = message.get_payload()
        if message.get('Content-Transfer-Encoding') == 'base64':
            payload = base64.b64decode(payload).decode()
        return converter.handle(payload)

    def get_url_view(self):
        uid = self.maildir.get_uid(self.filename)
        folders = '%2F'.join(self.folder)
        return f'https://my.gist.email/?_task=mail&_action=show&_uid={uid}&_mbox={folders}'
    
    def get_url_respond(self):
        uid = self.maildir.get_uid(self.filename)
        folders = '%2F'.join(self.folder)
        return f'https://my.gist.email/?_task=mail&_reply_uid={uid}&_mbox={folders}&_action=compose'    


# Utility to explore and manipulate Maildir
class Maildir:
    def __init__(self, user: str):
        try:
            self.user: str = user
            self.root: str = get_maildir_path(user)
            self.path: str = self.root
            self.folder: list = []
            self.foldername: str = self.get_foldername()
            self.maildir: mailbox.Maildir = mailbox.Maildir(self.path)
            self.current_folder = self.maildir
            self.uidvalidity: str = self.get_uidvailidity()
        except InvalidMailPathException:
            print(f'Could not find a mailbox for user "{user}".')

    def get_foldername(self):
        self.foldername = self.path.removeprefix(self.root).strip('/').strip('.')
        return self.foldername

    def get_uidvailidity(self):
        if os.path.exists(self.path + 'dovecot-uidlist'):
            return self.read_uidlist().get('uidvalidity')
        else:
            return None

    def get_folders(self):
        return self.current_folder.list_folders()

    def set_folder(self, foldername: str=None):
        if foldername in self.get_folders():
            self.folder += foldername
            self.current_folder = self.current_folder.get_folder(foldername)
            self.path = get_maildir_path(self.user, self.folder)
            self.get_foldername()
        elif foldername is None:
            self.folder = []
            self.path = get_maildir_path(self.user)
            self.current_folder = self.maildir
            self.get_foldername()
        else:
            print(f'No folder "{foldername}" exists for {self.user}.')

    def add_folders(self, *folders):
        for folder in folders:
            if folder not in self.get_folders():
                self.current_folder.add_folder(f'{self.foldername}.{folder}')
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
            folders = [folder.strip('.') for folder in self.path.removeprefix(self.root).strip('/').split('/')]
            return [Message(self.user, folders, message[0], message[1]) for message in self.current_folder.items()]
        except FileNotFoundError:
            return []

    def get_message(self, uid: int = None, filename: str = None):
        try:
            filename = self.read_uidlist()[int(uid)] if not filename and uid else filename
            message = [option for option in self.get_messages() if filename in option.filename]
            if message:
                return message[0]
            else:
                print(f'No file with name {filename} exists.')
                raise InvalidMailPathException
        except:
            raise InvalidMailPathException
        
    def get_uid(self, filename: str):
        try:
            uids = self.read_uidlist()
            for uid in uids.items():
                if filename in uid[1]:
                    return uid[0]
            raise InvalidMailPathException
        except:
            raise InvalidMailPathException

    def get_message_path(self, filename: str):
        paths = [f'{m[1].get_subdir()}/{m[0]}' for m in self.current_folder.items()]
        for path in paths:
            if filename in path:
                return f'{self.path}/{filename}'
        raise InvalidMailPathException


# Find the message reported by `push.lua` push notification
def get_message(user: str, folder: str, uid: int, uidvalidity: str):
    user = get_username_from_address(user)
    mdir = Maildir(user)
    mdir.set_folder(folder)
    if mdir.get_uidvailidity() == uidvalidity:
        return mdir.get_message(uid=uid)
    else:
        raise InvalidMailPathException