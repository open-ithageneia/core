import logging

from django.http import JsonResponse
from inertia import render

from quiz.services import QuizService

from .serializers import ExerciseQuerySerializer

logger = logging.getLogger(__name__)


def playground(request):
	return render(
		request,
		"Playground",
		props={"exam": QuizService.random_quiz(request.GET.dict())},
	)


def training(request):
	query_serializer = ExerciseQuerySerializer(data=request.GET)

	if not query_serializer.is_valid():
		logger.warning("Training query validation failed: %s", query_serializer.errors)
		return JsonResponse({"errors": query_serializer.errors}, status=400)

	validated_data = query_serializer.validated_data

	logger.debug(
		"Training request: category=%s amount=%s",
		validated_data["category"],
		validated_data["amount"],
	)

	data_by_category = QuizService.get_by_category(
		category=validated_data["category"],
		amount=validated_data["amount"],
	)

	return render(request, "Training", props={"data": data_by_category})
