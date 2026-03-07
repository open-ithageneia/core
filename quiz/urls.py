from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

urlpatterns = [
	path("", views.RandomQuizView.as_view(), name="random-quiz"),
]
