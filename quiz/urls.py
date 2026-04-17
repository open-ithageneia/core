from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

app_name = "quiz"

urlpatterns = [
	path("training", views.training, name="training"),
	path("playground", views.playground, name="playground"),
	path("dnd-playground", views.dnd_playground, name="dnd_playground"),
	path(
		"open-ended-playground",
		views.open_ended_playground,
		name="open_ended_playground",
	),
	path(
		"multiple-choice-playground",
		views.multiple_choice_playground,
		name="multiple_choice_playground",
	),
]
