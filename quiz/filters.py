import django_filters
from django_filters.widgets import CSVWidget

from .models import (
	Statement,
	DragAndDrop,
	Listening,
	Matching,
	FillInTheBlank,
	OpenEnded,
	MapPointer,
	QuizCategory,
)


class AbstractQuizFilter(django_filters.FilterSet):
	category = django_filters.ModelMultipleChoiceFilter(
		queryset=QuizCategory.objects.all(),
		to_field_name="code",
		widget=CSVWidget,
	)
	is_active = django_filters.BooleanFilter()


class StatementFilter(AbstractQuizFilter):
	type = django_filters.ChoiceFilter(
		choices=Statement.StatementType.choices,
	)

	class Meta:
		model = Statement
		fields = ["category", "is_active", "type"]


class ListeningFilter(AbstractQuizFilter):
	class Meta:
		model = Listening
		fields = ["category", "is_active"]


class DragAndDropFilter(AbstractQuizFilter):
	class Meta:
		model = DragAndDrop
		fields = ["category", "is_active"]


class MatchingFilter(AbstractQuizFilter):
	class Meta:
		model = Matching
		fields = ["category", "is_active"]


class FillInTheBlankFilter(AbstractQuizFilter):
	class Meta:
		model = FillInTheBlank
		fields = ["category", "is_active"]


class OpenEndedFilter(AbstractQuizFilter):
	class Meta:
		model = OpenEnded
		fields = ["category", "is_active"]


class MapPointerFilter(AbstractQuizFilter):
	class Meta:
		model = MapPointer
		fields = ["category", "is_active"]
