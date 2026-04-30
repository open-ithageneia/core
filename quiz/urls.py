from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

app_name = "quiz"

urlpatterns = [
	path("training", views.training, name="training"),
	path("dnd-playground", views.dnd_playground, name="dnd_playground"),
	path(
		"open-ended-playground",
		views.open_ended_playground,
		name="open_ended_playground",
	),
	path(
		"true-false-playground",
		views.true_false_playground,
		name="true_false_playground",
	),
	path(
		"multiple-choice-playground",
		views.multiple_choice_playground,
		name="multiple_choice_playground",
	),
	path(
		"fill-in-the-blank-playground",
		views.fill_in_the_blank_playground,
		name="fill_in_the_blank_playground",
	),
]
