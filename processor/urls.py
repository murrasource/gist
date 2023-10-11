from django.urls import path
from processor.views import NewMessageAPI

url_patterns = [
    path('new-message', NewMessageAPI.as_view(), name='new_message'),
]