import os
import uuid
from abc import abstractmethod, ABCMeta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django_jsonform.models.fields import JSONField

from open_ithageneia.models import ActivatableModel, TimeStampedModel

from .managers import AbstractQuizManager, ExamSessionManager, StatementManager
from .schemas import (
	StatementChoiceContent,
	DragAndDropContent,
	MatchingContent,
	FillInTheBlankContent,
)


class ExamSession(TimeStampedModel):
	class Month(models.IntegerChoices):
		JAN = 1, "January"
		FEB = 2, "February"
		MAR = 3, "March"
		APR = 4, "April"
		MAY = 5, "May"
		JUN = 6, "June"
		JUL = 7, "July"
		AUG = 8, "August"
		SEP = 9, "September"
		OCT = 10, "October"
		NOV = 11, "November"
		DEC = 12, "December"

	year = models.PositiveSmallIntegerField(
		validators=[MinValueValidator(2000), MaxValueValidator(2100)]
	)
	month = models.PositiveSmallIntegerField(choices=Month.choices)

	class Meta:
		indexes = [models.Index(fields=["year", "month"])]
		ordering = ["-year", "-month"]
		constraints = [
			models.UniqueConstraint(fields=["year", "month"], name="uniq_exam_session"),
			models.CheckConstraint(
				condition=Q(month__gte=1, month__lte=12),
				name="month_between_1_and_12",
			),
		]
		verbose_name_plural = "Exam Sessions"

	def __str__(self):
		return f"{self.get_month_display()} - {self.year}"

	objects = ExamSessionManager()


def get_quiz_asset_upload_to(instance, filename):
	_, ext = os.path.splitext(filename)

	return f"quizzes/assets/{uuid.uuid4()}{ext}"


class QuizAsset(TimeStampedModel):
	title = models.CharField(max_length=255, blank=True, default="")
	image = models.ImageField(upload_to=get_quiz_asset_upload_to)

	def __str__(self):
		return self.title if self.title else str(self.pk)

	class Meta:
		verbose_name_plural = "Quiz Assets"


class ModelABCMeta(ModelBase, ABCMeta):
	pass


class AbstractQuiz(TimeStampedModel, ActivatableModel, metaclass=ModelABCMeta):
	class QuizCategory(models.TextChoices):
		GEOGRAPHY = "GEOGRAPHY", "Geography"
		CIVICS = "CIVICS", "Civics"
		HISTORY = "HISTORY", "History"
		CULTURE = "CULTURE", "Culture"

	category = models.CharField(
		max_length=9,
		choices=QuizCategory,
		default=QuizCategory.GEOGRAPHY,
	)
	exam_sessions = models.ManyToManyField(
		ExamSession,
		blank=True,
		related_name="%(class)s_quizzes",
	)

	_cached_content_model = None

	@property
	def exam_sessions_preview(self):
		return ", ".join(
			[str(exam_session) for exam_session in self.exam_sessions.all()]
		)

	@abstractmethod
	def _parse_content(self):
		"""Parse and validate self.content into the typed dataclass.
		Subclasses implement this. Must raise ValidationError on bad data. """
		pass

	@property
	def content_model(self):
		if self._cached_content_model is None:
			self._cached_content_model = self._parse_content()
		return self._cached_content_model

	def clean(self):
		super().clean()
		# Reset cache and reparse to validate against current content.
		self._cached_content_model = None
		self._cached_content_model = self._parse_content()
		self._validate_content()

	def _validate_content(self):
		"""Override for extra business-rule checks beyond structural parsing."""
		pass

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"id: {self.id} - {self.category}"

	class Meta:
		abstract = True

	objects = AbstractQuizManager()


class Statement(AbstractQuiz):
	class QuizType(models.TextChoices):
		TRUE_FALSE = "TRUE_FALSE", "True/False"
		MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple Choice"

	type = models.CharField(
		max_length=15,
		choices=QuizType,
		default=QuizType.TRUE_FALSE,
	)

	content = JSONField(
		blank=True, default=dict, schema=StatementChoiceContent.STATEMENT_CONTENT_SCHEMA
	)

	def __str__(self):
		return f"id: {self.id}, {self.type} - {self.category}"

	class Meta:
		verbose_name_plural = "Statements (True/False or Multiple choice)"

	objects = StatementManager()

	@staticmethod
	def get_asset_image(asset_id):
		if not asset_id:
			return None

		try:
			return QuizAsset.objects.get(id=asset_id).image
		except QuizAsset.DoesNotExist:
			return None

	def get_choices_with_images(self):
		choices = self.content.get("choices", None)

		if not choices:
			return None

		asset_ids = [choice.get("asset_id") for choice in choices if choice.get("asset_id")]
		assets = QuizAsset.objects.in_bulk(asset_ids)

		for choice in choices:
			asset_id = choice.get("asset_id")
			asset = assets.get(asset_id)
			choice["image"] = asset.image if asset else None

		return choices

	def _parse_content(self):
		return StatementChoiceContent.from_json(self.content)

	def _validate_content(self):
		data = self.content_model
		if self.type == self.QuizType.MULTIPLE_CHOICE:
			if not any(choice.is_correct for choice in data.choices):
				raise ValidationError(
					"Multiple-choice questions must have at least one correct choice."
				)


class DragAndDrop(AbstractQuiz):
	content = JSONField(
		blank=True, default=list, schema=DragAndDropContent.DRAG_AND_DROP_CONTENT_SCHEMA
	)

	class Meta:
		verbose_name_plural = "Drag And Drop"

	def _parse_content(self):
		return DragAndDropContent.from_json(self.content)


class Matching(AbstractQuiz):
	content = JSONField(
		blank=True, default=list, schema=MatchingContent.MATCHING_CONTENT_SCHEMA
	)

	def _parse_content(self):
		return MatchingContent.from_json(self.content)


	class Meta:
		verbose_name_plural = "Matching"


class FillInTheBlank(AbstractQuiz):
	content = JSONField(
		blank=True,
		default=dict,
		schema=FillInTheBlankContent.FILL_IN_THE_BLANK_CONTENT_SCHEMA,
	)

	class Meta:
		verbose_name_plural = "Fill in the blank"

	def _parse_content(self):
		return FillInTheBlankContent.from_json(self.content)

