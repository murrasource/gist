from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from rest_framework.request import Request

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
def new_message_api(request: Request):
    print("Query Params:", request.query_params)
    print("Data:", request.data)
    return JsonResponse({'received': True})