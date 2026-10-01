from django.core.exceptions import ValidationError
from django.db import models

from ..managers import StatementManager
from .assets import QuizAsset
from .base import AbstractQuiz


class Statement(AbstractQuiz):
	INSTRUCTION_TEXT = {
		"TRUE_FALSE": "Επιλέξτε τη σωστή απάντηση",
		"MULTIPLE_CHOICE_SINGLE": "Επιλέξτε τη σωστή απάντηση",
		"MULTIPLE_CHOICE_MULTI": "Επιλέξτε τις σωστές απαντήσεις",
	}

	class StatementType(models.TextChoices):
		TRUE_FALSE = "TRUE_FALSE", "True/False"
		MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"

	type = models.CharField(
		max_length=15,
		choices=StatementType,
		default=StatementType.TRUE_FALSE,
	)

	listening = models.ForeignKey(
		"Listening",
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="questions",
		help_text="Set when this statement is one part of a listening question.",
	)
	part = models.ForeignKey(
		"ListeningPart",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="questions",
		help_text=(
			"Which section of the listening question this belongs to. Must be a "
			"part of the same listening question."
		),
	)
	order = models.PositiveSmallIntegerField(
		default=0,
		help_text="Display order within its part of a listening question.",
	)

	def __str__(self):
		return f"id: {self.id}, {self.type} - {self.category}"

	def clean(self):
		super().clean()
		if self.part_id and self.part.listening_id != self.listening_id:
			raise ValidationError(
				{"part": "The part must belong to the same listening question."}
			)

	def _validate_content(self):
		if not self.pk:
			return
		if self.type == self.StatementType.MULTIPLE_CHOICE:
			if not self.choices.filter(is_correct=True).exists():
				raise ValidationError(
					"Multiple-choice questions must have at least one correct choice."
				)

	class Meta:
		ordering = ["order", "id"]
		verbose_name_plural = "Statements (True/False or Multiple choice)"

	objects = StatementManager()


class StatementChoice(models.Model):
	statement = models.ForeignKey(
		Statement,
		on_delete=models.CASCADE,
		related_name="choices",
	)
	text = models.TextField(blank=True, default="")
	image = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
	)
	is_correct = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Statement choice"
		verbose_name_plural = "Statement choices"

	def __str__(self):
		return self.text or f"choice {self.pk}"
