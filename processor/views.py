from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render

class NewMessageAPI(APIView):
    def post(self, request):
        print(request.POST)
        print(request.body.decode())
        return JsonResponse({'received': True})