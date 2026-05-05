import json
import logging

from inertia import render

from quiz.models import AbstractQuiz
from quiz.schemas import (
	DragAndDropContent,
	FillInTheBlankContent,
	MatchingContent,
	OpenEndedContent,
	StatementChoiceContent,
)
from quiz.services import QuizService

from .serializers import ExerciseQuerySerializer

logger = logging.getLogger(__name__)


def training(request):
	categories = [
		{"value": c.value, "label": c.label} for c in AbstractQuiz.QuizCategory
	]
	exam_sessions = QuizService.exam_session_list()

	# No query params → show setup form
	if not request.GET.get("amount"):
		return render(
			request,
			"Training",
			props={
				"categories": categories,
				"exam_sessions": exam_sessions,
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
				"exam_sessions": exam_sessions,
				"data": None,
				"errors": query_serializer.errors,
			},
		)

	validated_data = query_serializer.validated_data

	logger.debug(
		"Training request: category=%s amount=%s exam_session=%s",
		validated_data["category"],
		validated_data["amount"],
		validated_data.get("exam_session"),
	)

	data_by_category = QuizService.get_by_category(
		category=validated_data["category"],
		amount=int(validated_data["amount"]),
		exam_session_id=validated_data.get("exam_session"),
		quiz_type=validated_data.get("quiz_type", ""),
	)

	CONTENT_PARSERS = {
		"Statement": StatementChoiceContent,
		"DragAndDrop": DragAndDropContent,
		"Matching": MatchingContent,
		"FillInTheBlank": FillInTheBlankContent,
		"OpenEnded": OpenEndedContent,
	}

	# content comes as JSON string from raw SQL — parse and normalize
	# through schema dataclasses so output matches serializer format
	for item in data_by_category:
		if isinstance(item["content"], str):
			item["content"] = json.loads(item["content"])
		parser = CONTENT_PARSERS.get(item["quiz_type"])
		if parser:
			item["content"] = parser.from_json(item["content"]).to_dict()

	return render(
		request,
		"Training",
		props={
			"categories": categories,
			"exam_sessions": exam_sessions,
			"data": data_by_category,
		},
	)


def simulation(request):
	# No "start" param → show start screen
	if not request.GET.get("start"):
		return render(
			request,
			"Simulation",
			props={"data": None},
		)

	data_by_category = QuizService.get_by_category(
		category="",
		amount=20,
	)

	CONTENT_PARSERS = {
		"Statement": StatementChoiceContent,
		"DragAndDrop": DragAndDropContent,
		"Matching": MatchingContent,
		"FillInTheBlank": FillInTheBlankContent,
		"OpenEnded": OpenEndedContent,
	}

	for item in data_by_category:
		if isinstance(item["content"], str):
			item["content"] = json.loads(item["content"])
		parser = CONTENT_PARSERS.get(item["quiz_type"])
		if parser:
			item["content"] = parser.from_json(item["content"]).to_dict()

	return render(
		request,
		"Simulation",
		props={"data": data_by_category},
	)
