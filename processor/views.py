from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.request import Request

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from processor.mail_utils import get_message, Message
from processor.tasks import process_new_message

@api_view(['POST'])
def new_message_api(request: Request):
    event = request.POST.get('event')
    if event == 'MessageNew':
        email_address: str = request.POST.get('to') if '<' not in request.POST.get('to') else request.POST.get('to').split('<')[1].strip('>')
        user: str = email_address.split('@')[0]
        folder: str = request.POST.get('folder')
        uid: int = int(request.POST.get('uid'))
        uidvalidity: str = str(request.POST.get('uidvalidity'))
        process_new_message.apply_async(args=(user, folder, uid, uidvalidity), countdown=30)
        return JsonResponse({'received': True})
    return JsonResponse({'received': False})
