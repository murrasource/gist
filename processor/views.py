from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.request import Request

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from processor.mail_utils import get_message
from processor.tasks import process_new_message

@api_view(['POST'])
def new_message_api(request: Request):
    event = request.POST.get('event')
    if event == 'MessageNew':
        email_address = request.POST.get('to').split('<')[1].strip('>')
        user = email_address.split('@')[0]
        folder = request.POST.get('folder')
        uid = int(request.POST.get('uid'))
        uidvalidity = str(request.POST.get('uidvalidity'))
        message = get_message(user, folder, uid, uidvalidity)
        if message:
            #process_new_message(message)
            return JsonResponse({'received': True})
    return JsonResponse({'received': False})
