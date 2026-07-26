import logging
import random

from django.db import connection

from .filters import (
	DragAndDropFilter,
	FillInTheBlankFilter,
	MapPointerFilter,
	MatchingFilter,
	OpenEndedFilter,
	StatementFilter,
)
from .models import (
	DragAndDrop,
	FillInTheBlank,
	MapPointer,
	Matching,
	OpenEnded,
	QuizAsset,
	QuizCategory,
	Statement,
)
from .serializers import (
	DragAndDropSerializer,
	FillInTheBlankSerializer,
	MapPointerSerializer,
	MatchingSerializer,
	OpenEndedSerializer,
	StatementSerializer,
)

logger = logging.getLogger(__name__)

QUIZ_MODELS = [Statement, Matching, DragAndDrop, FillInTheBlank, OpenEnded, MapPointer]


def get_random_quiz_items_alt(category: str, amount: int):
	"""
	Return `amount` random active quiz items across all quiz models for the given
	category. All rows from the different tables are UNIONed and a random sample is
	taken from the combined result, which favors tables with larger datasets.
	"""

	union_parts = []
	params = []

	for model in QUIZ_MODELS:
		model_table = model._meta.db_table

		union_parts.append(f"""
            SELECT
                m.id,
                m.category,
                m.content,
                '{model.__name__}' AS quiz_type
            FROM {model_table} m
            WHERE m.category = %s
            AND m.is_active = TRUE
        """)

		params.append(category)

	sql = f"""
        SELECT id, category, content, quiz_type
        FROM (
            {" UNION ALL ".join(union_parts)}
        ) combined
        ORDER BY RANDOM()
        LIMIT %s
    """

	params.append(amount)

	with connection.cursor() as cursor:
		cursor.execute(sql, params)
		columns = [col[0] for col in cursor.description]
		rows = cursor.fetchall()

	logger.debug(
		"get_random_quiz_items_alt: category=%s amount=%s returned %d rows",
		category,
		amount,
		len(rows),
	)

	return [dict(zip(columns, row)) for row in rows]


def get_random_quiz_items(category: str, amount: int, quiz_type: str = ""):
	"""
	Return `amount` random active quiz items for the given category using a
	balanced sampling strategy. Each quiz table first contributes a random
	subset of rows, the results are UNIONed, shuffled, and the final `amount` items
	are returned. The Statement table uses `2 * amount` to account for its two
	question subtypes (True/False and Multiple Choice).

	If `quiz_type` is provided, only that model's table is queried.
	"""

	# Map quiz_type string to model class
	QUIZ_TYPE_MAP = {model.__name__: model for model in QUIZ_MODELS}

	if quiz_type and quiz_type in QUIZ_TYPE_MAP:
		models_to_query = [QUIZ_TYPE_MAP[quiz_type]]
	else:
		models_to_query = QUIZ_MODELS

	union_parts = []
	params = []

	for model in models_to_query:
		model_table = model._meta.db_table

		per_model_amount = amount * 2 if model is Statement else amount

		if category:
			cat_list = [c.strip() for c in category.split(",") if c.strip()]
		else:
			cat_list = []

		if cat_list:
			placeholders = ", ".join(["%s"] * len(cat_list))
			category_clause = f"AND m.category IN ({placeholders})"
		else:
			category_clause = ""

		union_parts.append(f"""
            SELECT * FROM (
                SELECT
                    m.id,
                    m.category,
                    m.content,
                    '{model.__name__}' AS quiz_type
                FROM {model_table} m
                WHERE m.is_active = TRUE
                {category_clause}
                ORDER BY RANDOM()
                LIMIT %s
            )
        """)

		if cat_list:
			params.extend(cat_list)
		params.append(per_model_amount)

	sql = f"""
        SELECT id, category, content, quiz_type
        FROM (
            {" UNION ALL ".join(union_parts)}
        ) combined
        ORDER BY RANDOM()
        LIMIT %s
    """

	params.append(amount)

	with connection.cursor() as cursor:
		cursor.execute(sql, params)
		columns = [col[0] for col in cursor.description]
		rows = cursor.fetchall()

	logger.debug(
		"get_random_quiz_items: category=%s amount=%s returned %d rows",
		category,
		amount,
		len(rows),
	)

	return [dict(zip(columns, row)) for row in rows]


class QuizService:
	@staticmethod
	def statement_types():
		return [
			{"value": choice.value, "label": choice.label}
			for choice in Statement.StatementType
		]

	@staticmethod
	def categories():
		return [
			{"value": category.code, "label": category.name}
			for category in QuizCategory.objects.all()
		]

	@staticmethod
	def _list(model, filterset_class, serializer_class, params=None):
		qs = filterset_class(params, queryset=model.objects.all()).qs
		return serializer_class(qs, many=True).data

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
			# Statements linked as a second part are only ever shown attached to
			# their first part, never standalone.
			if model is Statement:
				base_qs = base_qs.filter(first_part__isnull=True)
			qs = filterset_class(p, queryset=base_qs.distinct()).qs
			return serializer_class(qs.order_by("?")[:n], many=True).data

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

	# Category codes for each exam simulation variant's question pool.
	LISTENING_CATEGORY = "LISTENING"
	KNOWLEDGE_SIMULATION_CATEGORIES = [
		QuizCategory.GEOGRAPHY,
		QuizCategory.CIVICS,
		QuizCategory.HISTORY,
		QuizCategory.CULTURE,
	]
	LISTENING_SIMULATION_CATEGORIES = [LISTENING_CATEGORY]

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
		]

		QUIZ_TYPE_MAP = {
			model.__name__: config
			for model, *_ in QUIZ_CONFIG
			for config in [(model, *_[0:])]
		}
		# Simpler map:
		QUIZ_TYPE_MAP = {
			model.__name__: (model, filt, ser) for model, filt, ser in QUIZ_CONFIG
		}

		if quiz_type and quiz_type in QUIZ_TYPE_MAP:
			configs_to_query = [QUIZ_TYPE_MAP[quiz_type]]
		else:
			configs_to_query = QUIZ_CONFIG

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
			# Statements linked as a second part are only ever shown attached to
			# their first part, never standalone.
			if model is Statement:
				base_qs = base_qs.filter(first_part__isnull=True)
			qs = filterset_class(filter_params, queryset=base_qs.distinct()).qs
			sampled = qs.order_by("?")[:per_model_amount]
			serialized = serializer_class(sampled, many=True).data
			quiz_type_name = model.__name__
			for entry in serialized:
				entry["quiz_type"] = quiz_type_name
			items.extend(serialized)

		random.shuffle(items)
		return items[:amount]


class AssetService:
	@staticmethod
	def resolve_asset_url(asset_id):
		asset = QuizAsset.objects.filter(id=asset_id).first()
		if asset and asset.image:
			return asset.image.url
		return None

	@staticmethod
	def resolve_audio_asset_url(asset_id):
		asset = QuizAsset.objects.filter(id=asset_id).first()
		if asset and asset.audio:
			return asset.audio.url
		return None
