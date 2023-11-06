from django.conf import settings
import django.utils.timezone as tz
from processor.mail_utils import Maildir, Message, get_username_from_address
from mailserver.models import VirtualUser
from processor.models import Email, EmailGist
import json
import openai, tiktoken

# Get the classification options based on user's inbox folders
def get_classification_options(user: str):
    maildir = Maildir(user)
    maildir.set_folder(foldername='INBOX')
    return ['.'.join(folder.split('.')[1:]) for folder in maildir.get_folders() if folder.startswith('INBOX.')]

# Create the prompts to feed to OpenAI
def get_messages_json(message: Message):
    return [
        {  
            "role": "system",
            "content": settings.OPENAI_SYSTEM_TUNER
        },
        {   
            "role": "user",
            "content": \
                f"\n FROM: {message.sender} \n" + \
                f"\n SUBJECT: {message.subject} \n" + \
                condense_email_content(message.content)
        }
    ]

# Create the function structure to 
def get_functions_json(user: str):
    return [
        {
            "name": "generate_email_gist",
            "description": "Construct a summary report of an email using the content category, sender, and a few word summary",
            "parameters": {
                "type": "object",
                "required": ["action", "category", "sender", "summary"],
                "properties": {
                    "action": {
                        "type": "boolean",
                        "description": "True if the email is something a busy person would actually need to review or is worthy of their time, else false."
                    },
                    "category": {
                        "type": "string",
                        "enum": get_classification_options(user),
                        "description": "Which of these folders should the email be classified into?"
                    },
                    "sender": {
                        "type": "string",
                        "description": "Extract the name of the sender. For example, 'no-reply@fabletics.com' would be 'Fabletics'."
                    },
                    "summary": {
                        "type": "string",
                        "description": "The most concise and actionable summary of the email that is just a few words long. If there is a multi-factor auth code, make sure this is included in the summary."
                    }
                }
            }
        }
    ]

# Condense emails into the proper token limit
def condense_email_content(content: str):
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    content_tokens = tokenizer.encode(content)
    if len(content_tokens) > settings.OPENAI_TOKEN_LIMIT:
        content_tokens = content_tokens[:settings.OPENAI_TOKEN_LIMIT - 1]
        return tokenizer.decode(content_tokens)
    return content

# Feed OpenAI the email and function, and then generate the gist
def generate_email_gist(user: VirtualUser, message: Message):
    # Create new Email object
    email = Email.objects.get_or_create(
            account     = user.account,
            smtp_to     = user,
            smtp_from   = message.sender,
            location    = message.get_path()
    )[0]

    email.save()

    if settings.OPENAI_API_KEY and not settings.DEBUG:
        # Set API key
        openai.api_key = settings.OPENAI_API_KEY

        # Have ChatGPT give output in structured manner
        response = openai.ChatCompletion.create(
            model           = settings.OPENAI_LLM,
            messages        = get_messages_json(message),
            functions       = get_functions_json(get_username_from_address(user.email)),
            function_call   = {"name": "generate_email_gist"},
        )

        # Get the response content
        response_message = response["choices"][0]["message"]

        # Select the arguments we need
        function_args = json.loads(response_message["function_call"]["arguments"])
        
        print('OpenAI response: ', function_args)

        # Update email and message to processed state
        email.processed = tz.now()
        message.mark_as_processed(folder=['INBOX', f'INBOX.{function_args.get("category")}'])
        email.location = message.get_path()
        email.save()

        # Use the arguments to generate our gist
        gist = EmailGist.objects.create(
            account=user.account,
            email=email,
            complete=(not function_args.get("action")),
            action=function_args.get("action"),
            category=function_args.get("category"),
            sender=function_args.get("sender"),
            gist=function_args.get("summary")
        )

        gist.save()

        return gist