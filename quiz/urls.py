from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .viewsets import StatementViewSet, ExamSessionViewSet, FillInTheBlankViewSet, MatchingViewSet, \
	DragAndDropViewSet

router = DefaultRouter()
router.register(r"exam-sessions", ExamSessionViewSet, basename="exam-session")
router.register(r"statements", StatementViewSet, basename="statement")
router.register(r"fill-in-blanks", FillInTheBlankViewSet, basename="fill-in-blank")
router.register(r"matching", MatchingViewSet, basename="matching")
router.register(r"drag-and-drop", DragAndDropViewSet, basename="drag-and-drop")

urlpatterns = [
	path("", views.RandomQuizView.as_view(), name="random-quiz"),
	path("statements/types/", views.statement_types, name="statement-types"),
	path("categories/", views.quiz_categories, name="quiz-categories"),
	path("", include(router.urls)),
]
