# apps/circles/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('',                      api_views.all_circles,       name='api_all_circles'),
    path('my/',                   api_views.my_membership,     name='api_my_membership'),
    path('available/',            api_views.available_circles, name='api_available_circles'),
    path('<int:circle_id>/join/', api_views.join_circle,       name='api_join_circle'),
    path('<int:circle_id>/leave/', api_views.leave_circle,     name='api_leave_circle'),
]
