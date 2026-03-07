from rest_framework import viewsets

from quiz.filters import StatementFilter, DragAndDropFilter, MatchingFilter, FillInTheBlankFilter
from quiz.models import Statement, ExamSession, DragAndDrop, Matching, FillInTheBlank
from quiz.serializers import StatementSerializer, DragAndDropSerializer, MatchingSerializer, FillInTheBlankSerializer, \
	ExamSessionSerializer


class ExamSessionViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = ExamSession.objects.get_queryset()
	serializer_class = ExamSessionSerializer


class StatementViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Statement.objects.get_queryset()
	serializer_class = StatementSerializer
	filterset_class = StatementFilter


class FillInTheBlankViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = FillInTheBlank.objects.get_queryset()
	serializer_class = FillInTheBlankSerializer
	filterset_class = FillInTheBlankFilter


class DragAndDropViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = DragAndDrop.objects.get_queryset()
	serializer_class = DragAndDropSerializer
	filterset_class = DragAndDropFilter


class MatchingViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Matching.objects.get_queryset()
	serializer_class = MatchingSerializer
	filterset_class = MatchingFilter
