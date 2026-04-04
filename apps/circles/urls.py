from django.urls import path
from . import views
app_name = 'circles'
urlpatterns = [
    path('circle/',                    views.my_circle,    name='my_circle'),
    path('circle/<int:circle_id>/join/', views.join_circle, name='join_circle'),
    path('circle/<int:circle_id>/leave/', views.leave_circle, name='leave_circle'),
]
