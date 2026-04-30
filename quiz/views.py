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

	# No query params → show setup form
	if not request.GET.get("category") and not request.GET.get("amount"):
		return render(
			request,
			"Training",
			props={"categories": categories, "data": None},
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
			"data": data_by_category,
		},
	)


def dnd_playground(request):
	return render(
		request,
		"DndPlayground",
		props={"dnd_list": QuizService.drag_and_drop_list()},
	)


def open_ended_playground(request):
	return render(
		request,
		"OpenEndedPlayground",
		props={"open_ended_list": QuizService.open_ended_list()},
	)


def multiple_choice_playground(request):
	return render(
		request,
		"MultipleChoicePlayground",
		props={
			"multiple_choice_list": QuizService.statement_list(
				{"type": "MULTIPLE_CHOICE"}
			)
		},
	)


def true_false_playground(request):
	return render(
		request,
		"TrueFalsePlayground",
		props={"true_false_list": QuizService.statement_list({"type": "TRUE_FALSE"})},
	)


def fill_in_the_blank_playground(request):
	return render(
		request,
		"FillInTheBlankPlayground",
		props={"fill_in_the_blank_list": QuizService.fill_in_the_blank_list()},
	)
