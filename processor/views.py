from uuid import UUID
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from rest_framework.request import Request
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from processor.mail_utils import get_message, Message
from processor.models import EmailGist, EmailGistReport
from processor.tasks import process_new_message

@api_view(['POST'])
def new_message_api(request: Request):
    data = request.data
    if data.get('event') == 'MessageNew':
        user: str = data.get('user')
        folder: str = data.get('folder')
        uid: int = int(data.get('uid'))
        uidvalidity: str = str(data.get('uidvalidity'))
        print(f'Queueing new message -- user: {user}, folder: {folder}, uid: {uid}, uidvalidity: {uidvalidity}')
        process_new_message.apply_async(args=(user, folder, uid, uidvalidity), countdown=30)
        return JsonResponse({'received': True})
    return JsonResponse({'received': False})

@api_view(['PATCH'])
def toggle_completion_api(request: Request, report_uuid: UUID, gist_uuid: UUID):
    report = EmailGistReport.objects.get(uuid=report_uuid)
    gist = EmailGist.objects.get(uuid=gist_uuid)
    if report and gist:
        if gist in report.gists.all():
            gist.complete = not gist.complete
            gist.save()
        return JsonResponse({'message': f'Status set to {gist.complete}'})
    return JsonResponse({'message': f'Either the gist or report does not exist.'})

def gist_report(request: Request, report_uuid: UUID):
    report = EmailGistReport.objects.get(uuid=report_uuid)
    return render(request, 'report.html', {'gists': report.gists.all()})