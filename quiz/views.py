from inertia import render

from quiz.services import QuizService


def random_quiz_view(request):
	return render(request, 'Exam', props=QuizService.random_quiz(request.GET.dict()))
