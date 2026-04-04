# apps/claims/urls.py
from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    path('claims/',          views.my_claims,     name='my_claims'),
    path('claims/<int:pk>/', views.claim_detail,  name='claim_detail'),
]
