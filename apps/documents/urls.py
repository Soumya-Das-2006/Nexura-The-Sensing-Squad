from django.urls import path

from . import views

app_name = 'documents'

urlpatterns = [
    path('documents/', views.income_dna, name='income_dna'),
    path('documents/generate/', views.generate_income_dna, name='generate_income_dna'),
    path('documents/download/<int:doc_id>/', views.download_income_dna, name='download_income_dna'),
]
