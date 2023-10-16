from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.request import Request

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from mail_utils import get_message

@api_view(['POST'])
def new_message_api(request: Request):
    event = request.POST.get('event')
    if event == 'MessageNew':
        email_address = request.POST.get('to')
        user = email_address.split('@')[0]
        folder = request.POST.get('folder')
        uid = request.POST.get('uid')
        uidvalidity = request.POST.get('uidvalidity')
        message = get_message(user, folder, uid, uidvalidity)
        if message:
            return JsonResponse({'received': True})
        else:
            return JsonResponse({'received': False})
    return JsonResponse({'received': False})
