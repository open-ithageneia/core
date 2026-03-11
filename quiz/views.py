from django.http import JsonResponse
from inertia import render

from quiz.services import QuizService

from .serializers import ExerciseQuerySerializer


def random_quiz_view(request):
    return render(
        request, "Exam", props={"exam": QuizService.random_quiz(request.GET.dict())}
    )


def training(request):
    query_serializer = ExerciseQuerySerializer(data=request.GET)

    if not query_serializer.is_valid():
        return JsonResponse({"errors": query_serializer.errors}, status=400)

    validated_data = query_serializer.validated_data

    data_by_category = QuizService.get_by_category(
        category=validated_data["category"],
        amount=validated_data["amount"],
    )

    return render(request, "Training", props={"data": data_by_category})
