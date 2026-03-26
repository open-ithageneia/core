import django_filters
from .models import (
	Statement,
	DragAndDrop,
	Matching,
	FillInTheBlank,
	OpenEnded,
	ExamSession,
	AbstractQuiz,
)


class AbstractQuizFilter(django_filters.FilterSet):
	category = django_filters.ChoiceFilter(
		choices=AbstractQuiz.QuizCategory.choices,
	)
	exam_session_id = django_filters.ModelChoiceFilter(
		queryset=ExamSession.objects.all(),
		field_name="exam_sessions",
	)
	year = django_filters.NumberFilter(field_name="exam_sessions__year")
	month = django_filters.NumberFilter(field_name="exam_sessions__month")
	is_active = django_filters.BooleanFilter()


class StatementFilter(AbstractQuizFilter):
	type = django_filters.ChoiceFilter(
		choices=Statement.QuizType.choices,
	)

	class Meta:
		model = Statement
		fields = ["category", "exam_session_id", "year", "month", "is_active", "type"]


class DragAndDropFilter(AbstractQuizFilter):
	class Meta:
		model = DragAndDrop
		fields = ["category", "exam_session_id", "year", "month", "is_active"]


class MatchingFilter(AbstractQuizFilter):
	class Meta:
		model = Matching
		fields = ["category", "exam_session_id", "year", "month", "is_active"]


class FillInTheBlankFilter(AbstractQuizFilter):
	class Meta:
		model = FillInTheBlank
		fields = ["category", "exam_session_id", "year", "month", "is_active"]


class OpenEndedFilter(AbstractQuizFilter):
	class Meta:
		model = OpenEnded
		fields = ["category", "exam_session_id", "year", "month", "is_active"]
