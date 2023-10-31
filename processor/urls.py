from django.urls import path
from processor import views

url_patterns = [
    path('new-message', views.new_message_api, name='new_message'),
    path('gist-report/<uuid:report_uuid>', views.gist_report, name='gist_report'),
    path('toggle-completion/<uuid:report_uuid>/<uuid:gist_uuid>', views.toggle_completion_api, name='toggle_completion'),
]