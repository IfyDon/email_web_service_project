from django.urls import path
from tracking import views

urlpatterns = [
    path('o/<str:token>/', views.track_open, name='open'),
    path('c/<str:token>/<str:encoded>/', views.track_click, name='click'),
    path('u/<str:token>/', views.unsubscribe, name='unsubscribe'),
]