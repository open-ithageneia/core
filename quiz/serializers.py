from rest_framework import serializers
from .models import (
	ExamSession,
	QuizAsset,
	Statement,
	DragAndDrop,
	Matching,
	FillInTheBlank,
)


class ExamSessionSerializer(serializers.ModelSerializer):
	month_display = serializers.CharField(source="get_month_display", read_only=True)

	class Meta:
		model = ExamSession
		fields = ["id", "year", "month", "month_display"]


class QuizAssetSerializer(serializers.ModelSerializer):
	class Meta:
		model = QuizAsset
		fields = ["id", "title", "image"]


class StatementSerializer(serializers.ModelSerializer):
	exam_sessions = ExamSessionSerializer(many=True, read_only=True)
	exam_session_ids = serializers.PrimaryKeyRelatedField(
		queryset=ExamSession.objects.all(),
		many=True,
		write_only=True,
		source="exam_sessions",
	)

	class Meta:
		model = Statement
		fields = [
			"id",
			"category",
			"type",
			"content",
			"is_active",
			"exam_sessions",
			"exam_session_ids",
			"created_at",
			"updated_at",
		]

	def validate_content(self, value):
		from .schemas import TRUE_FALSE_MULTIPLE_CHOICE_QUIZ_SCHEMA
		import jsonschema

		try:
			jsonschema.validate(instance=value, schema=TRUE_FALSE_MULTIPLE_CHOICE_QUIZ_SCHEMA)
		except jsonschema.ValidationError as e:
			raise serializers.ValidationError(f"Invalid content structure: {e.message}")
		return value


class DragAndDropSerializer(serializers.ModelSerializer):
	exam_sessions = ExamSessionSerializer(many=True, read_only=True)
	exam_session_ids = serializers.PrimaryKeyRelatedField(
		queryset=ExamSession.objects.all(),
		many=True,
		write_only=True,
		source="exam_sessions",
	)

	class Meta:
		model = DragAndDrop
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"exam_sessions",
			"exam_session_ids",
			"created_at",
			"updated_at",
		]

	def validate_content(self, value):
		from .schemas import DRAG_AND_DROP_QUIZ_SCHEMA
		import jsonschema

		try:
			jsonschema.validate(instance=value, schema=DRAG_AND_DROP_QUIZ_SCHEMA)
		except jsonschema.ValidationError as e:
			raise serializers.ValidationError(f"Invalid content structure: {e.message}")
		return value


class MatchingSerializer(serializers.ModelSerializer):
	exam_sessions = ExamSessionSerializer(many=True, read_only=True)
	exam_session_ids = serializers.PrimaryKeyRelatedField(
		queryset=ExamSession.objects.all(),
		many=True,
		write_only=True,
		source="exam_sessions",
	)

	class Meta:
		model = Matching
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"exam_sessions",
			"exam_session_ids",
			"created_at",
			"updated_at",
		]

	def validate_content(self, value):
		from .schemas import MATCHING_QUIZ_SCHEMA
		import jsonschema

		try:
			jsonschema.validate(instance=value, schema=MATCHING_QUIZ_SCHEMA)
		except jsonschema.ValidationError as e:
			raise serializers.ValidationError(f"Invalid content structure: {e.message}")
		return value


class FillInTheBlankSerializer(serializers.ModelSerializer):
	exam_sessions = ExamSessionSerializer(many=True, read_only=True)
	exam_session_ids = serializers.PrimaryKeyRelatedField(
		queryset=ExamSession.objects.all(),
		many=True,
		write_only=True,
		source="exam_sessions",
	)

	class Meta:
		model = FillInTheBlank
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"exam_sessions",
			"exam_session_ids",
			"created_at",
			"updated_at",
		]

	def validate_content(self, value):
		from .schemas import FILL_IN_THE_BLANK_QUIZ_SCHEMA
		import jsonschema

		try:
			jsonschema.validate(instance=value, schema=FILL_IN_THE_BLANK_QUIZ_SCHEMA)
		except jsonschema.ValidationError as e:
			raise serializers.ValidationError(f"Invalid content structure: {e.message}")
		return value
