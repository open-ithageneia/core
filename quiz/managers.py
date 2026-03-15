from django.db import models


class ExamSessionQuerySet(models.QuerySet):
	def for_year(self, year):
		return self.filter(year=year)

	def for_month(self, month):
		return self.filter(month=month)


ExamSessionManager = models.Manager.from_queryset(ExamSessionQuerySet)


class AbstractQuizQuerySet(models.QuerySet):
	def active(self):
		return self.filter(is_active=True)

	def inactive(self):
		return self.filter(is_active=False)

	def for_category(self, category):
		return self.filter(category=category)

	def for_session(self, exam_session):
		return self.filter(exam_sessions=exam_session)

	def for_session_id(self, exam_session_id):
		return self.filter(exam_sessions__id=exam_session_id)

	def for_year(self, year):
		return self.filter(exam_sessions__year=year)

	def for_month(self, month):
		return self.filter(exam_sessions__month=month)

	def geography(self):
		return self.for_category("GEOGRAPHY")

	def civics(self):
		return self.for_category("CIVICS")

	def history(self):
		return self.for_category("HISTORY")

	def culture(self):
		return self.for_category("CULTURE")

	def with_exam_sessions(self):
		return self.prefetch_related("exam_sessions")


AbstractQuizManager = models.Manager.from_queryset(AbstractQuizQuerySet)


class StatementQuerySet(AbstractQuizQuerySet):
	def true_false(self):
		return self.filter(type="TRUE_FALSE")

	def multiple_choice(self):
		return self.filter(type="MULTIPLE_CHOICE")

	def with_assets(self):
		return self.prefetch_related("exam_sessions")


StatementManager = models.Manager.from_queryset(StatementQuerySet)
