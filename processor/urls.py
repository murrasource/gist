from django.urls import path
from processor.views import new_message_api

url_patterns = [
    path('new-message', new_message_api, name='new_message'),
]