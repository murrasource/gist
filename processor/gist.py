from django.conf import settings
import django.utils.timezone as tz
from processor.mail_utils import Maildir, Message, get_user_from_address
from mailserver.models import VirtualUser
from processor.models import Email, EmailGist
import json
import openai

# Get the classification options based on user's inbox folders
def get_classification_options(user: str):
    maildir = Maildir(user)
    return ['.'.join(folder.split('.')[1:]) for folder in maildir.get_folders() if folder.startswith('INBOX.')]

# Create the prompts to feed to OpenAI
def get_messages_json(email: str):
    return [
        {   "role": "system",  "content": settings.OPENAI_SYSTEM_TUNER          },
        {   "role": "user",    "content": settings.OPENAI_USER_PROMPT + email   }
    ]

# Create the function structure to 
def get_functions_json(user: str):
    return [
        {
            "name": "generate_email_gist",
            "description": "Construct a summary report of an email using the content category, sender, and a few word summary",
            "parameters": {
                "type": "object",
                "required": ["category", "sender", "summary"],
                "properties": {
                    "category": {
                        "type": "boolean",
                        "description": "True if the user needs to take action on this email, else false."
                    },
                    "category": {
                        "type": "string",
                        "enum": get_classification_options(user),
                        "description": "How the email's content is classified."
                    },
                    "sender": {
                        "type": "string",
                        "description": "Display name of the sender. If there is a concern over spoofing, add ' (Suspicious)' at the end."
                    },
                    "summary": {
                        "type": "string",
                        "description": "A few word summary of the content in the email. This is NOT the subject line, but the most concise and actionable summary that can be conveyed in less than a sentence."
                    }
                }
            }
        }
    ]

# Feed OpenAI the email and function, and then generate the gist
def generate_email_gist(user: VirtualUser, message: Message):
    # Create new Email object
    email = Email.objects.get_or_create(
            account     = user.account,
            smtp_to     = user.account.get_report_destination(),
            smtp_from   = settings.GIST_REPORT_SENDER,
            location    = message.get_path()
    )

    # Set API key
    openai.api_key = settings.OPEN_AI_API_KEY

    # Have ChatGPT give output in structured manner
    response = openai.ChatCompletion.create(
        model           = settings.OPENAI_LLM,
        messages        = get_messages_json(message.content),
        functions       = get_functions_json(get_user_from_address(user.email)),
        function_call   = {"name": "generate_email_gist"},
    )

    # Get the response content
    response_message = response["choices"][0]["message"]

    # Select the arguments we need
    function_args = json.loads(response_message["function_call"]["arguments"])
    
    # Update email and message to processed state
    email.processed = tz.now()
    email.save()
    message.mark_as_processed(folder=f'INBOX.{function_args.get("category")}')

    # Use the arguments to generate our gist
    return EmailGist.objects.create(
        account=user.account,
        email=email,
        complete=(not function_args.get("action")),
        action=function_args.get("action"),
        category=function_args.get("category"),
        sender=function_args.get("sender"),
        gist=function_args.get("summary")
    )
