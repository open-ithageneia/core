from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

app_name = "quiz"

urlpatterns = [
	path("training", views.training, name="training"),
	path("simulation", views.simulation, name="simulation"),
]
