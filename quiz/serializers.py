from rest_framework import serializers

from .models import (
	DragAndDrop,
	FillInTheBlank,
	Listening,
	MapPointer,
	Matching,
	QuizAsset,
	QuizCategory,
	Statement,
	OpenEnded,
)


class ParsedContentMixin:
	"""Override ``to_representation`` so the raw JSON ``content`` field is
	replaced by the structured output of ``content_model.to_dict()``.

	Works for every ``AbstractQuiz`` subclass — no per-model overrides
	needed.  The mixin must come *before* ``ModelSerializer`` in the MRO."""

	def to_representation(self, instance):
		data = super().to_representation(instance)
		if hasattr(instance, "content_model"):
			data["content"] = instance.content_model.to_dict()
		return data


class QuizAssetSerializer(serializers.ModelSerializer):
	class Meta:
		model = QuizAsset
		fields = ["id", "title", "image"]


class StatementSerializer(ParsedContentMixin, serializers.ModelSerializer):
	class Meta:
		model = Statement
		fields = [
			"id",
			"category",
			"type",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]


class ListeningSerializer(serializers.ModelSerializer):
	"""Serializes a listening question and its parts.

	Deliberately *not* using ``ParsedContentMixin``: this model has no JSON
	``content`` field, so there is nothing to parse.
	"""

	audio_url = serializers.ReadOnlyField()
	parts = serializers.SerializerMethodField()

	class Meta:
		model = Listening
		fields = [
			"id",
			"category",
			"audio_url",
			"max_plays",
			"transcript",
			"parts",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_parts(self, obj):
		"""The sections the exam is split into, in order, each with its description
		and the questions that belong to it.

		Parts have no name of their own — the client labels them Α, Β, … by their
		position here, so the order matters. Parts with no questions are left out.
		Ordered explicitly rather than via a prefetch so the order holds however
		the serializer is called; a listening question has a handful of parts at
		most.
		"""
		parts = []
		for part in obj.parts.order_by("id"):
			questions = list(part.questions.order_by("order", "id"))
			if not questions:
				continue
			parts.append(
				{
					"id": part.id,
					"description": part.description,
					"questions": StatementSerializer(questions, many=True).data,
				}
			)
		return parts


class DragAndDropSerializer(ParsedContentMixin, serializers.ModelSerializer):
	class Meta:
		model = DragAndDrop
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]


class MatchingSerializer(ParsedContentMixin, serializers.ModelSerializer):
	class Meta:
		model = Matching
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]


class FillInTheBlankSerializer(ParsedContentMixin, serializers.ModelSerializer):
	class Meta:
		model = FillInTheBlank
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]


class OpenEndedSerializer(ParsedContentMixin, serializers.ModelSerializer):
	class Meta:
		model = OpenEnded
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]


class MapPointerSerializer(ParsedContentMixin, serializers.ModelSerializer):
	class Meta:
		model = MapPointer
		fields = [
			"id",
			"category",
			"level",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]


class ExerciseQuerySerializer(serializers.Serializer):
	category = serializers.CharField(default="", allow_blank=True)
	amount = serializers.ChoiceField(default=10, choices=[5, 10, 20])
	quiz_type = serializers.ChoiceField(
		default="",
		choices=[
			("", "All"),
			("Statement", "Statement"),
			("DragAndDrop", "DragAndDrop"),
			("FillInTheBlank", "FillInTheBlank"),
			("OpenEnded", "OpenEnded"),
			("Matching", "Matching"),
			("MapPointer", "MapPointer"),
			("Listening", "Listening"),
		],
	)

	def validate_category(self, value):
		if not value:
			return ""
		valid = set(QuizCategory.objects.values_list("code", flat=True))
		for cat in value.split(","):
			cat = cat.strip()
			if cat and cat not in valid:
				raise serializers.ValidationError(f"Invalid category: {cat}")
		return value
