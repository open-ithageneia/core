from django.db import models


class AbstractQuizQuerySet(models.QuerySet):
	def active(self):
		return self.filter(is_active=True)

	def inactive(self):
		return self.filter(is_active=False)

	def for_category(self, category):
		return self.filter(category=category)

	def geography(self):
		return self.for_category("GEOGRAPHY")

	def civics(self):
		return self.for_category("CIVICS")

	def history(self):
		return self.for_category("HISTORY")

	def culture(self):
		return self.for_category("CULTURE")


AbstractQuizManager = models.Manager.from_queryset(AbstractQuizQuerySet)


class StatementQuerySet(AbstractQuizQuerySet):
	def true_false(self):
		return self.filter(type="TRUE_FALSE")

	def multiple_choice(self):
		return self.filter(type="MULTIPLE_CHOICE")


StatementManager = models.Manager.from_queryset(StatementQuerySet)
