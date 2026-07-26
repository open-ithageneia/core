from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

app_name = "quiz"

urlpatterns = [
	path("training", views.training, name="training"),
	path("simulation", views.simulation, name="simulation"),
	path(
		"simulation/knowledge",
		views.knowledge_simulation,
		name="knowledge_simulation",
	),
	path(
		"simulation/listening",
		views.listening_simulation,
		name="listening_simulation",
	),
]
