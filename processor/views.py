from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.request import Request

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from processor.mail_utils import get_message, Message
from processor.tasks import process_new_message

@api_view(['POST'])
def new_message_api(request: Request):
    data = request.data
    if data.get('event') == 'MessageNew':
        email_address: str = data.get('user')
        user: str = email_address.split('@')[0]
        folder: str = data.get('folder')
        uid: int = int(data.get('uid'))
        uidvalidity: str = str(data.get('uidvalidity'))
        print(f'Queueing new message -- user: {user}, folder: {folder}, uid: {uid}, uidvalidity: {uidvalidity}')
        process_new_message.apply_async(args=(user, folder, uid, uidvalidity), countdown=30)
        return JsonResponse({'received': True})
    return JsonResponse({'received': False})
