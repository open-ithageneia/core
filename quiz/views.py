from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import MatchingFilter, DragAndDropFilter, FillInTheBlankFilter, StatementFilter
from .models import Statement, AbstractQuiz, FillInTheBlank, DragAndDrop, Matching
from .serializers import StatementSerializer, FillInTheBlankSerializer, DragAndDropSerializer, MatchingSerializer


@api_view(["GET"])
def statement_types(request):
    types = [
        {"value": choice.value, "label": choice.label}
        for choice in Statement.QuizType
    ]
    return Response(types)


@api_view(["GET"])
def quiz_categories(request):
    categories = [
        {"value": choice.value, "label": choice.label}
        for choice in AbstractQuiz.QuizCategory
    ]
    return Response(categories)


class RandomQuizView(APIView):
    def get(self, request):
        n = request.query_params.get("n", 20)
        try:
            n = int(n)
            if n < 1:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"n": "Must be a positive integer."}, status=400)

        def sample(model, filterset_class, serializer_class, extra_params=None):
            params = request.GET.copy()
            if extra_params:
                params.update(extra_params)

            qs = model.objects.all().distinct()
            filtered = filterset_class(params, queryset=qs).qs
            return serializer_class(filtered.order_by("?")[:n], many=True).data

        return Response({
            "true_false": sample(Statement, StatementFilter, StatementSerializer, {"type": Statement.QuizType.TRUE_FALSE}),
            "multiple_choice": sample(Statement, StatementFilter, StatementSerializer, {"type": Statement.QuizType.MULTIPLE_CHOICE}),
            "fill_in_the_blank": sample(FillInTheBlank, FillInTheBlankFilter, FillInTheBlankSerializer),
            "drag_and_drop": sample(DragAndDrop, DragAndDropFilter, DragAndDropSerializer),
            "matching": sample(Matching, MatchingFilter, MatchingSerializer),
        })
