from django.urls import path
from . import views

urlpatterns = [
    path('calculate', views.calculate_artifact_value, name='calculate'),
]
