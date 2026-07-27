from rest_framework import serializers

from .models import (
	DragAndDrop,
	FillInTheBlank,
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
	second_part = serializers.SerializerMethodField()

	class Meta:
		model = Statement
		fields = [
			"id",
			"category",
			"type",
			"content",
			"second_part",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_second_part(self, obj):
		# Serialize the linked follow-up statement one level deep only. The
		# ``nested`` context flag bounds recursion so a mis-linked chain can
		# never loop.
		if obj.second_part_id and not self.context.get("nested"):
			return StatementSerializer(obj.second_part, context={"nested": True}).data
		return None


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
