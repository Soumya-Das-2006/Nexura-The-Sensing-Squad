"""apps/documents/views.py"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import IncomeDNADocument

logger = logging.getLogger(__name__)
_login = login_required(login_url='accounts:login')


@_login
def income_dna(request):
    if not request.user.is_worker:
        return redirect('core:home')
    docs = IncomeDNADocument.objects.filter(worker=request.user).order_by('-created_at')[:5]
    return render(request, 'documents/income_dna.html', {'docs': docs})


@_login
def generate_income_dna(request):
    if request.method != 'POST':
        return redirect('documents:income_dna')
    if not request.user.is_worker:
        return redirect('core:home')

    period_months = int(request.POST.get('period_months', 3))
    doc = IncomeDNADocument.objects.create(
        worker=request.user, period_months=period_months, status='pending'
    )
    try:
        from .income_dna import generate_income_dna as _gen
        pdf_bytes, sig = _gen(request.user, period_months)
        doc.signature_hex = sig
        doc.status = 'ready'

        import os
        from django.core.files.base import ContentFile
        fname = f"income_dna_{request.user.mobile}_{doc.pk}.pdf"
        doc.pdf_file.save(fname, ContentFile(pdf_bytes), save=True)
        doc.save(update_fields=['status', 'signature_hex'])
        messages.success(request, 'Your IncomeDNA report is ready. Click Download to save it.')
    except Exception as e:
        logger.error("[IncomeDNA] Generation failed for %s: %s", request.user.mobile, e, exc_info=True)
        doc.status = 'failed'
        doc.failure_reason = str(e)
        doc.save(update_fields=['status', 'failure_reason'])
        messages.error(request, 'Report generation failed. Please try again.')

    return redirect('documents:income_dna')


@_login
def download_income_dna(request, doc_id):
    doc = get_object_or_404(IncomeDNADocument, pk=doc_id, worker=request.user, status='ready')
    if not doc.pdf_file:
        raise Http404
    response = HttpResponse(doc.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="nexura_income_dna_{doc.pk}.pdf"'
    return response
