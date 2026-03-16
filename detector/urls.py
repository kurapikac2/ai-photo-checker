from django.urls import path
from . import views

app_name = 'detector'

urlpatterns = [
    path('', views.home, name='home'),
    path('check/', views.check_image, name='check'),
    path('result/<int:pk>/', views.result_view, name='result'),
    path('history/', views.history_view, name='history'),
]
