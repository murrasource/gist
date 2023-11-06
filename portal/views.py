from uuid import UUID
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from rest_framework.request import Request
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from processor.models import EmailGist, EmailGistReport

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
    return render(request, 'report.html', {'report': report, 'folders': list(set([gist.category for gist in report.gists.all()]))})