import html2text
import mailbox
from enum import Enum
from django.conf import settings

# ex: 'sample@gist.email' -> 'sample'
def get_user_from_address(address: str):
    return address.split('@')[0]

# ex: '/var/vmail/gist.email/user/Maildir' or '/var/vmail/gist.email/user/Maildir/INBOX.Marketing/cur/1696304003.M382939P108930.gist,S=350,W=362'
def get_maildir_path(user: str, folder: str = None, subdir: str = None, filename: str = None):
    if not folder:
        return f'{settings.MAILDIR_PREFIX}/{user}/{settings.MAILDIR_NAME}'
    if folder and not (subdir and filename):
        return f'{settings.MAILDIR_PREFIX}/{user}/{settings.MAILDIR_NAME}/{folder}'
    if user and folder and subdir and filename:
        return f'{settings.MAILDIR_PREFIX}/{user}/{settings.MAILDIR_NAME}/{folder}/{subdir}/{filename}'

# Convert HTML email into plaintext to save on OpenAI tokens
def extract_text(content):
    converter = html2text.HTML2Text()
    converter.ignore_tables     = True
    converter.ignore_links      = True
    converter.ignore_images     = True
    converter.ignore_emphasis   = True
    return converter.handle(content)

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
        self.content = extract_text(self.message.get_payload())

    def get_maildir(self, **kwargs):
        user = kwargs.get('user', self.user)
        folder = kwargs.get('folder', self.folder)
        return mailbox.Maildir(get_maildir_path(user, folder))

    def get_path(self):
        return get_maildir_path(self.user, self.folder, self.message.get_subdir(), self.filename)

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

# Utility to explore and manipulate Maildir
class Maildir:
    def __init__(self, user: str):
        try:
            self.user = user
            self.path = get_maildir_path(user)
            self.maildir = mailbox.Maildir(self.path, create=True)
            self.current_folder = self.maildir
        except:
            print(f'There is no email registered to "{user}".')

    def get_folders(self):
        return self.maildir.list_folders()

    def set_folder(self, foldername=None):
        if foldername in self.get_folders():
            self.path = get_maildir_path(self.user, foldername)
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

    def set_user(self, user):
        self = self.__init__(user)

    def get_messages(self):
        foldername = self.path.split('/')[-1]
        return [Message(self.user, foldername, message[0], message[1]) for message in self.current_folder.items()]
