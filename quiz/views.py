import logging

from django.shortcuts import redirect
from django.urls import reverse
from inertia import render

from quiz.services import QuizService

from .serializers import ExerciseQuerySerializer

logger = logging.getLogger(__name__)


def training(request):
	categories = QuizService.categories()

	# No query params → show setup form
	if not request.GET.get("amount"):
		return render(
			request,
			"Training",
			props={
				"categories": categories,
				"data": None,
			},
		)

	query_serializer = ExerciseQuerySerializer(data=request.GET)

	if not query_serializer.is_valid():
		logger.warning("Training query validation failed: %s", query_serializer.errors)
		return render(
			request,
			"Training",
			props={
				"categories": categories,
				"data": None,
				"errors": query_serializer.errors,
			},
		)

	validated_data = query_serializer.validated_data

	logger.debug(
		"Training request: category=%s amount=%s",
		validated_data["category"],
		validated_data["amount"],
	)

	data_by_category = QuizService.get_by_category(
		category=validated_data["category"],
		amount=int(validated_data["amount"]),
		quiz_type=validated_data.get("quiz_type", ""),
	)

	return render(
		request,
		"Training",
		props={
			"categories": categories,
			"data": data_by_category,
		},
	)


# Simulation modes offered on the hub screen, in display order.
SIMULATION_MODES = [
	("knowledge", "quiz:knowledge_simulation"),
	("listening", "quiz:listening_simulation"),
]

# How many questions each simulation variant draws. The listening exam is a
# single audio question whose sub-answers (true/false + multiple choice) carry
# the whole score, so one question is the entire test.
KNOWLEDGE_SIMULATION_QUESTIONS = 20
LISTENING_SIMULATION_QUESTIONS = 1


def simulation(request):
	# Hub screen: pick a simulation mode.
	return render(
		request,
		"SimulationMenu",
		props={
			"modes": [
				{"key": key, "href": reverse(view_name)}
				for key, view_name in SIMULATION_MODES
			]
		},
	)


def _run_simulation(request, *, variant, amount, categories=None, quiz_type=""):
	# Without an explicit start, send the user back to the mode picker.
	if not request.GET.get("start"):
		return redirect("quiz:simulation")

	data_by_category = QuizService.get_by_category(
		category="",
		amount=amount,
		categories=categories,
		quiz_type=quiz_type,
	)

	return render(
		request,
		"Simulation",
		props={"data": data_by_category, "variant": variant},
	)


def knowledge_simulation(request):
	return _run_simulation(
		request,
		variant="knowledge",
		categories=QuizService.KNOWLEDGE_SIMULATION_CATEGORIES,
		amount=KNOWLEDGE_SIMULATION_QUESTIONS,
	)


def listening_simulation(request):
	return _run_simulation(
		request,
		variant="listening",
		quiz_type=QuizService.LISTENING_QUIZ_TYPE,
		amount=LISTENING_SIMULATION_QUESTIONS,
	)
