from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

urlpatterns = [
    path("", views.random_quiz_view, name="random-quiz"),
    path("training", views.training, name="training"),
]
