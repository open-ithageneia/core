from abc import ABCMeta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase

from open_ithageneia.models import ActivatableModel, TimeStampedModel

from ..managers import AbstractQuizManager
from .assets import QuizAsset, QuizCategory


class ModelABCMeta(ModelBase, ABCMeta):
	pass


class AbstractQuiz(TimeStampedModel, ActivatableModel, metaclass=ModelABCMeta):
	category = models.ForeignKey(
		QuizCategory,
		db_column="category",
		on_delete=models.PROTECT,
		default=QuizCategory.GEOGRAPHY,
		related_name="%(class)ss",
	)

	test_number = models.SmallIntegerField(
		blank=True,
		default=0,
	)

	question_number = models.SmallIntegerField(
		blank=True,
		default=0,
	)

	prompt_text = models.TextField(blank=True, default="")
	prompt_image = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
		help_text="Image shown with the question.",
	)
	prompt_audio = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
		help_text="Audio clip played with the question.",
	)

	def clean(self):
		super().clean()
		self._validate_content()

	def _validate_content(self):
		"""Business rules spanning the question's child rows.

		A rule that counts child rows has to guard on ``self.pk``: the admin
		saves the parent before its inlines, so a question being created has no
		children yet and would fail a rule it satisfies a moment later. Such a
		rule therefore lives in two places — here for programmatic saves, and in
		the inline's formset for admin ones. ``Statement`` and ``Listening`` both
		show the pattern.
		"""

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"id: {self.id} - {self.category}"

	class Meta:
		abstract = True

	objects = AbstractQuizManager()


class MinCorrectAnswersMixin(models.Model):
	min_correct_answers = models.PositiveSmallIntegerField(default=1)

	class Meta:
		abstract = True

	def _validate_min_correct_answers(self):
		if self.min_correct_answers < 1:
			raise ValidationError("min_correct_answers must be at least 1.")
		if not self.pk:
			return
		available = self.answers.count()
		if available and self.min_correct_answers > available:
			raise ValidationError(
				f"min_correct_answers ({self.min_correct_answers}) cannot exceed "
				f"the number of available answers ({available})."
			)
