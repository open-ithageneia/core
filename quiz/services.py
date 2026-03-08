import random

from django.db.models import CharField, Value

from .filters import (
    DragAndDropFilter,
    FillInTheBlankFilter,
    MatchingFilter,
    StatementFilter,
)
from .models import (
    AbstractQuiz,
    DragAndDrop,
    ExamSession,
    FillInTheBlank,
    Matching,
    Statement,
)
from .serializers import (
    DragAndDropSerializer,
    ExamSessionSerializer,
    FillInTheBlankSerializer,
    MatchingSerializer,
    StatementSerializer,
)

QUIZ_MODELS = [
    Statement,
    Matching,
    DragAndDrop,
    FillInTheBlank,
]


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
        }

    @staticmethod
    def get_by_category(category: str, amount: int):
        items = []

        for model in QUIZ_MODELS:
            # This increases the probability that each model contributes at least one item,
            # compared to queryset = model.objects.filter(category=category), but did it for performance reasons
            queryset = (
                model.objects.filter(
                    category=category,
                    exam_sessions=ExamSession.objects.first(),  # no need to add latest() in managers.py since we have ordering = ["-year", "-month"] in model Meta
                )
                .annotate(quiz_type=Value(model.__name__, output_field=CharField()))
                .values("id", "category", "content", "quiz_type")
                .distinct()
                .order_by("?")[:amount]
            )

            for instance in queryset:
                items.append(instance)

        random.shuffle(items)

        return items[:amount]
