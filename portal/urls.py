from django.urls import path
from portal import views

url_patterns = [
    path('gist-report/<uuid:report_uuid>', views.gist_report, name='gist_report'),
    path('toggle-completion/<uuid:report_uuid>/<uuid:gist_uuid>', views.toggle_completion_api, name='toggle_completion'),
]