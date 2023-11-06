from django.urls import path
from processor import views

url_patterns = [
    path('new-message', views.new_message_api, name='new_message'),
]