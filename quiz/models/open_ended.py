from django.db import models

from .base import AbstractQuiz, MinCorrectAnswersMixin


class OpenEnded(MinCorrectAnswersMixin, AbstractQuiz):
	class Meta:
		verbose_name_plural = "Open Ended"

	def _validate_content(self):
		self._validate_min_correct_answers()


class OpenEndedAnswer(models.Model):
	"""One thing the candidate could correctly write. Its ``alternatives`` are
	the spellings and phrasings that all count as that same answer."""

	question = models.ForeignKey(
		OpenEnded,
		on_delete=models.CASCADE,
		related_name="answers",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Open ended answer"
		verbose_name_plural = "Open ended answers"

	def __str__(self):
		first = self.alternatives.first()
		return first.text if first else f"answer {self.pk}"


class OpenEndedAlternative(models.Model):
	answer = models.ForeignKey(
		OpenEndedAnswer,
		on_delete=models.CASCADE,
		related_name="alternatives",
	)
	text = models.CharField(max_length=255)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Open ended alternative"
		verbose_name_plural = "Open ended alternatives"

	def __str__(self):
		return self.text
