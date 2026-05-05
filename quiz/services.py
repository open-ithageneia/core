import logging

from django.db import connection

from .filters import (
	DragAndDropFilter,
	FillInTheBlankFilter,
	MatchingFilter,
	OpenEndedFilter,
	StatementFilter,
)
from .models import (
	AbstractQuiz,
	DragAndDrop,
	ExamSession,
	FillInTheBlank,
	Matching,
	OpenEnded,
	QuizAsset,
	Statement,
)
from .serializers import (
	DragAndDropSerializer,
	ExamSessionSerializer,
	FillInTheBlankSerializer,
	MatchingSerializer,
	OpenEndedSerializer,
	StatementSerializer,
)

logger = logging.getLogger(__name__)

QUIZ_MODELS = [Statement, Matching, DragAndDrop, FillInTheBlank, OpenEnded]


def get_random_quiz_items_alt(category: str, amount: int):
	"""
	Return `amount` random quiz items across all quiz models for the given category
	and the latest exam session. All rows from the different tables are UNIONed and
	a random sample is taken from the combined result, which favors tables
	with larger datasets.
	"""

	union_parts = []
	params = []

	for model in QUIZ_MODELS:
		model_table = model._meta.db_table
		through_table = model.exam_sessions.through._meta.db_table
		model_name = model.__name__.lower()

		union_parts.append(f"""
            SELECT
                m.id,
                m.category,
                m.content,
                '{model.__name__}' AS quiz_type
            FROM {model_table} m
            INNER JOIN {through_table} t
                ON t.{model_name}_id = m.id
            WHERE m.category = %s
            AND t.examsession_id = (
                SELECT id
                FROM {ExamSession._meta.db_table}
                ORDER BY year DESC, month DESC
                LIMIT 1
            )
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


def get_random_quiz_items(
	category: str, amount: int, exam_session_id: int | None = None, quiz_type: str = ""
):
	"""
	Return `amount` random quiz items for the given category and exam session
	using a balanced sampling strategy. Each quiz table first contributes a random
	subset of rows, the results are UNIONed, shuffled, and the final `amount` items
	are returned. The Statement table uses `2 * amount` to account for its two
	question subtypes (True/False and Multiple Choice).

	If `exam_session_id` is not provided, the latest exam session is used.
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
		through_table = model.exam_sessions.through._meta.db_table
		model_name = model.__name__.lower()

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

		if exam_session_id:
			session_clause = "t.examsession_id = %s"
		else:
			session_clause = f"""t.examsession_id = (
                    SELECT id
                    FROM {ExamSession._meta.db_table}
                    ORDER BY year DESC, month DESC
                    LIMIT 1
                )"""

		union_parts.append(f"""
            SELECT * FROM (
                SELECT
                    m.id,
                    m.category,
                    m.content,
                    '{model.__name__}' AS quiz_type
                FROM {model_table} m
                INNER JOIN {through_table} t
                    ON t.{model_name}_id = m.id
                WHERE {session_clause}
                {category_clause}
                ORDER BY RANDOM()
                LIMIT %s
            )
        """)

		if exam_session_id:
			params.append(exam_session_id)
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
			for choice in Statement.QuizType
		]

	@staticmethod
	def categories():
		return [
			{"value": choice.value, "label": choice.label}
			for choice in AbstractQuiz.QuizCategory
		]

	@staticmethod
	def exam_session_list():
		qs = ExamSession.objects.all()
		return ExamSessionSerializer(qs, many=True).data

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
	def random_quiz(params, n=20):
		def sample(model, filterset_class, serializer_class, extra_params=None):
			p = params.copy()
			if extra_params:
				p.update(extra_params)
			qs = filterset_class(p, queryset=model.objects.all().distinct()).qs
			return serializer_class(qs.order_by("?")[:n], many=True).data

		return {
			"true_false": sample(
				Statement,
				StatementFilter,
				StatementSerializer,
				{"type": Statement.QuizType.TRUE_FALSE},
			),
			"multiple_choice": sample(
				Statement,
				StatementFilter,
				StatementSerializer,
				{"type": Statement.QuizType.MULTIPLE_CHOICE},
			),
			"fill_in_the_blank": sample(
				FillInTheBlank, FillInTheBlankFilter, FillInTheBlankSerializer
			),
			"drag_and_drop": sample(
				DragAndDrop, DragAndDropFilter, DragAndDropSerializer
			),
			"matching": sample(Matching, MatchingFilter, MatchingSerializer),
			"open_ended": sample(OpenEnded, OpenEndedFilter, OpenEndedSerializer),
		}

	@staticmethod
	def get_by_category(
		category: str,
		amount: int,
		exam_session_id: int | None = None,
		quiz_type: str = "",
	):
		return get_random_quiz_items(category, amount, exam_session_id, quiz_type)

		# items = []

		# DB hit for every iteration
		# for model in QUIZ_MODELS:
		#     # This increases the probability that each model contributes at least one item,
		#     # compared to queryset = model.objects.filter(category=category), but did it for performance reasons
		#     queryset = (
		#         model.objects.filter(
		#             category=category,
		#             exam_sessions=ExamSession.objects.first(),  # no need to add latest() in managers.py since we have ordering = ["-year", "-month"] in model Meta
		#         )
		#         .annotate(quiz_type=Value(model.__name__, output_field=CharField()))
		#         .values("id", "category", "content", "quiz_type")
		#         .distinct()
		#         .order_by("?")[:amount]
		#     )

		#     for instance in queryset:
		#         items.append(instance)

		# random.shuffle(items)

		# return items[:amount]


class AssetService:
	@staticmethod
	def resolve_asset_url(asset_id):
		asset = QuizAsset.objects.filter(id=asset_id).first()
		if asset:
			return asset.image.url
		return None
