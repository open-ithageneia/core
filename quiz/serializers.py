from rest_framework import serializers

from .models import (
	AbstractQuiz,
	DragAndDrop,
	ExamSession,
	FillInTheBlank,
	Matching,
	QuizAsset,
	Statement,
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


class ExerciseQuerySerializer(serializers.Serializer):
	category = serializers.ChoiceField(
		default="", choices=AbstractQuiz.QuizCategory.choices
	)
	amount = serializers.ChoiceField(default=10, choices=[5, 10, 20])
