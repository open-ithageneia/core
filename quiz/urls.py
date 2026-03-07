from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

urlpatterns = [
	path("", views.random_quiz_view, name="random-quiz"),
]
