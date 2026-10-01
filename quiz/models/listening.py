from django.core.exceptions import ValidationError
from django.db import models

from open_ithageneia.models import TimeStampedModel

from .assets import QuizAsset
from .base import AbstractQuiz
from .statement import Statement


class ListeningPart(TimeStampedModel):
	listening = models.ForeignKey(
		"Listening",
		on_delete=models.CASCADE,
		related_name="parts",
	)
	description = models.TextField(
		blank=True,
		default="",
		help_text="Optional text introducing the part, shown above its questions.",
	)

	class Meta:
		ordering = ["id"]
		verbose_name = "Listening part"
		verbose_name_plural = "Listening parts"

	def __str__(self):
		lines = self.description.strip().splitlines()
		label = lines[0][:60] if lines else f"part {self.pk}"
		return f"{label} (listening {self.listening_id})"

	@property
	def position(self):
		ids = list(
			ListeningPart.objects.filter(listening_id=self.listening_id).values_list(
				"id", flat=True
			)
		)
		return ids.index(self.id) + 1

	@classmethod
	def at_position(cls, listening, position):
		parts = list(cls.objects.filter(listening=listening))
		created = len(parts) < position
		while len(parts) < position:
			parts.append(cls.objects.create(listening=listening))
		return parts[position - 1], created


def validate_listening_question_types(types):
	"""Enforce the exam shape of a listening question: exactly one True/False
	question (which itself holds several statements) plus one or more
	multiple-choice questions.

	Which ``ListeningPart`` each one belongs to is deliberately not checked — the
	first part is usually the true/false one and the second the multiple-choice
	ones, but that is a convention rather than a rule. Nor is having a part
	checked here: ``ListeningQuestionFormSet`` is what requires one on admin
	saves.

	*types* is an iterable of ``Statement.StatementType`` values.
	"""
	types = list(types)
	true_false = types.count(Statement.StatementType.TRUE_FALSE)
	multiple_choice = types.count(Statement.StatementType.MULTIPLE_CHOICE)

	if true_false != 1:
		raise ValidationError(
			f"A listening question needs exactly one True/False question, "
			f"found {true_false}."
		)
	if multiple_choice < 1:
		raise ValidationError(
			"A listening question needs at least one multiple-choice question."
		)


class Listening(AbstractQuiz):
	INSTRUCTION_TEXT = "Ακούστε το ηχητικό και απαντήστε στις ερωτήσεις"

	audio = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		related_name="listening_questions",
		help_text="Quiz asset holding the audio clip.",
	)
	max_plays = models.PositiveSmallIntegerField(
		default=2,
		help_text="How many times the candidate may play the clip.",
	)
	transcript = models.TextField(
		blank=True,
		default="",
		help_text="Optional text of the clip, for review after answering.",
	)

	class Meta:
		verbose_name_plural = "Listening"

	def __str__(self):
		return f"id: {self.id} - {self.category} (listening)"

	@property
	def audio_url(self):
		return self.audio.audio.url if self.audio_id and self.audio.audio else None

	def clean(self):
		super().clean()
		if not self.pk:
			return
		types = list(self.questions.values_list("type", flat=True))
		if types:
			validate_listening_question_types(types)
