from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

urlpatterns = [
	path("training", views.training, name="training"),
	path("playground", views.playground, name="playground"),
]
