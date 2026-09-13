import logging
import random

from .filters import (
	DragAndDropFilter,
	FillInTheBlankFilter,
	ListeningFilter,
	MapPointerFilter,
	MatchingFilter,
	OpenEndedFilter,
	StatementFilter,
)
from .models import (
	DragAndDrop,
	FillInTheBlank,
	Listening,
	MapPointer,
	Matching,
	OpenEnded,
	QuizCategory,
	Statement,
)
from .serializers import (
	DragAndDropSerializer,
	FillInTheBlankSerializer,
	ListeningSerializer,
	MapPointerSerializer,
	MatchingSerializer,
	OpenEndedSerializer,
	StatementSerializer,
)

logger = logging.getLogger(__name__)


class QuizService:
	@staticmethod
	def with_content(queryset, serializer_class):
		"""Apply the prefetches the serializer's ``to_dict()`` will walk.

		Content used to be one JSON column, so a list cost one query. It is rows
		now, which is only as cheap if the relations are fetched up front — hence
		``content_prefetch`` on each serializer, applied here rather than repeated
		at each call site.
		"""
		prefetch = getattr(serializer_class, "content_prefetch", ())
		return queryset.prefetch_related(*prefetch) if prefetch else queryset

	@staticmethod
	def statement_types():
		return [
			{"value": choice.value, "label": choice.label}
			for choice in Statement.StatementType
		]

	@staticmethod
	def categories():
		"""Every category as a ``{value, label}`` option, in display order. The
		label is the Greek name held on the row, so the client never has to know
		what a category code is called."""
		return [
			{"value": category.code, "label": category.label}
			for category in QuizCategory.objects.all()
		]

	@staticmethod
	def category_labels():
		"""Category code → the Greek name to display, for the whole table.

		Quiz items travel to the client carrying only their category code, so the
		client needs the mapping to name the category on a question card.
		"""
		return {
			category.code: category.label for category in QuizCategory.objects.all()
		}

	@staticmethod
	def _list(model, filterset_class, serializer_class, params=None):
		qs = filterset_class(params, queryset=model.objects.all()).qs
		return serializer_class(
			QuizService.with_content(qs, serializer_class), many=True
		).data

	@staticmethod
	def statement_list(params=None):
		return QuizService._list(
			Statement, StatementFilter, StatementSerializer, params
		)

	@staticmethod
	def fill_in_the_blank_list(params=None):
		return QuizService._list(
			FillInTheBlank, FillInTheBlankFilter, FillInTheBlankSerializer, params
		)

	@staticmethod
	def drag_and_drop_list(params=None):
		return QuizService._list(
			DragAndDrop, DragAndDropFilter, DragAndDropSerializer, params
		)

	@staticmethod
	def matching_list(params=None):
		return QuizService._list(Matching, MatchingFilter, MatchingSerializer, params)

	@staticmethod
	def open_ended_list(params=None):
		return QuizService._list(
			OpenEnded, OpenEndedFilter, OpenEndedSerializer, params
		)

	@staticmethod
	def map_pointer_list(params=None):
		return QuizService._list(
			MapPointer, MapPointerFilter, MapPointerSerializer, params
		)

	@staticmethod
	def random_quiz(params, n=20):
		def sample(model, filterset_class, serializer_class, extra_params=None):
			p = params.copy()
			if extra_params:
				p.update(extra_params)
			base_qs = model.objects.active()
			# Statements belonging to a listening question are only ever shown
			# inside that question, never standalone.
			if model is Statement:
				base_qs = base_qs.filter(listening__isnull=True)
			qs = filterset_class(p, queryset=base_qs.distinct()).qs
			# Slice first, then prefetch: prefetching the whole filtered table to
			# keep n rows would fetch every child row in it.
			sampled = QuizService.with_content(
				model.objects.filter(
					pk__in=list(qs.order_by("?").values_list("pk", flat=True)[:n])
				),
				serializer_class,
			)
			return serializer_class(sampled, many=True).data

		return {
			"true_false": sample(
				Statement,
				StatementFilter,
				StatementSerializer,
				{"type": Statement.StatementType.TRUE_FALSE},
			),
			"multiple_choice": sample(
				Statement,
				StatementFilter,
				StatementSerializer,
				{"type": Statement.StatementType.MULTIPLE_CHOICE},
			),
			"fill_in_the_blank": sample(
				FillInTheBlank, FillInTheBlankFilter, FillInTheBlankSerializer
			),
			"drag_and_drop": sample(
				DragAndDrop, DragAndDropFilter, DragAndDropSerializer
			),
			"matching": sample(Matching, MatchingFilter, MatchingSerializer),
			"open_ended": sample(OpenEnded, OpenEndedFilter, OpenEndedSerializer),
			"map_pointer": sample(MapPointer, MapPointerFilter, MapPointerSerializer),
		}

	# Question pool for the knowledge exam simulation.
	KNOWLEDGE_SIMULATION_CATEGORIES = [
		QuizCategory.GEOGRAPHY,
		QuizCategory.CIVICS,
		QuizCategory.HISTORY,
		QuizCategory.CULTURE,
	]
	# The listening exam is its own section, selected by quiz type rather than by
	# category, so a clip can still be tagged with the subject it covers.
	LISTENING_QUIZ_TYPE = Listening.__name__

	@staticmethod
	def get_by_category(
		category: str,
		amount: int,
		quiz_type: str = "",
		categories: list | None = None,
	):
		"""
		Return `amount` random serialized active quiz items for the given
		category, using ORM queries and DRF serializers.

		When `categories` is given, only questions in those categories are
		included (used by the exam simulation).
		"""
		QUIZ_CONFIG = [
			(Statement, StatementFilter, StatementSerializer),
			(Matching, MatchingFilter, MatchingSerializer),
			(DragAndDrop, DragAndDropFilter, DragAndDropSerializer),
			(FillInTheBlank, FillInTheBlankFilter, FillInTheBlankSerializer),
			(OpenEnded, OpenEndedFilter, OpenEndedSerializer),
			(MapPointer, MapPointerFilter, MapPointerSerializer),
			(Listening, ListeningFilter, ListeningSerializer),
		]

		QUIZ_TYPE_MAP = {
			model.__name__: (model, filt, ser) for model, filt, ser in QUIZ_CONFIG
		}

		if quiz_type and quiz_type in QUIZ_TYPE_MAP:
			configs_to_query = [QUIZ_TYPE_MAP[quiz_type]]
		else:
			# Listening is a separate exam section: it is only ever sampled when
			# asked for by name, never mixed into the general pool.
			configs_to_query = [c for c in QUIZ_CONFIG if c[0] is not Listening]

		# Build filter params
		filter_params = {}
		if category:
			filter_params["category"] = category

		items = []
		for model, filterset_class, serializer_class in configs_to_query:
			per_model_amount = amount * 2 if model is Statement else amount
			base_qs = model.objects.active()
			if categories:
				base_qs = base_qs.filter(category__in=categories)
			# Statements belonging to a listening question are only ever shown
			# inside that question, never standalone.
			if model is Statement:
				base_qs = base_qs.filter(listening__isnull=True)
			if model is Listening:
				base_qs = base_qs.select_related("audio")
			qs = filterset_class(filter_params, queryset=base_qs.distinct()).qs
			# Pick the ids first so the prefetch only loads the children of the
			# rows actually being served.
			sampled_ids = list(
				qs.order_by("?").values_list("pk", flat=True)[:per_model_amount]
			)
			sampled = QuizService.with_content(
				model.objects.filter(pk__in=sampled_ids), serializer_class
			)
			if model is Listening:
				sampled = sampled.select_related("audio")
			serialized = serializer_class(sampled, many=True).data
			quiz_type_name = model.__name__
			for entry in serialized:
				entry["quiz_type"] = quiz_type_name
			items.extend(serialized)

		random.shuffle(items)
		return items[:amount]
