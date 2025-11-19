from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('check-username/', views.check_username, name='check_username'),

]

