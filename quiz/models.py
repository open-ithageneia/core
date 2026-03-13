import os
import re
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

	@property
	def exam_sessions_preview(self):
		return ", ".join(
			[str(exam_session) for exam_session in self.exam_sessions.all()]
		)

	@abstractmethod
	def validate_content(self):
		pass

	@abstractmethod
	@property
	def content_model(self):
		pass

	def clean(self):
		print("clean called")

		super().clean()
		self.validate_content()

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

		asset_ids = [(choice.get("asset_id", None)) for choice in choices]
		assets = QuizAsset.objects.in_bulk(asset_ids)

		for choice in choices:
			asset_id = choice.get("asset_id", None)
			asset = assets.get(asset_id)
			choice["image"] = self.get_asset_image(asset.id) if asset else None

		return choices

	def validate_content(self):
		data = StatementChoiceContent.from_json(self.content)
		if self.type == self.QuizType.MULTIPLE_CHOICE:
			for choice in data.choices:
				if choice.is_correct:
					return

	@property
	def content_model(self):
		return StatementChoiceContent.from_json(self.content)


class DragAndDrop(AbstractQuiz):

	content = JSONField(
		blank=True, default=list, schema=DragAndDropContent.DRAG_AND_DROP_CONTENT_SCHEMA
	)

	class Meta:
		verbose_name_plural = "Drag And Drop"

	def validate_content(self):
		DragAndDropContent.from_json(self.content)

	@property
	def content_model(self) -> DragAndDropContent:
		return DragAndDropContent.from_json(self.content)


class Matching(AbstractQuiz):

	content = JSONField(
		blank=True, default=list, schema=MatchingContent.MATCHING_CONTENT_SCHEMA
	)

	def validate_content(self):
		MatchingContent.from_json(self.content)

	class Meta:
		verbose_name_plural = "Matching"

	@property
	def content_model(self) -> MatchingContent:
		return MatchingContent.from_json(self.content)


class FillInTheBlank(AbstractQuiz):
	BLANK_PATTERN = re.compile(r"<(.+?)>")
	CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")

	content = JSONField(
		blank=True,
		default=dict,
		schema=FillInTheBlankContent.FILL_IN_THE_BLANK_CONTENT_SCHEMA,
	)

	class Meta:
		verbose_name_plural = "Fill in the blank"

	def validate_content(self):
		FillInTheBlankContent.from_json(self.content)

		texts = self.content.get("texts", [])

		for i, item in enumerate(texts):
			text = item.get("text", "")
			raw_blanks = self.BLANK_PATTERN.findall(text)

			if not raw_blanks:
				raise ValidationError(
					f"Text #{i + 1}: no blanks found. Use <({{{{answer}}}}*)> syntax."
				)

			for blank in raw_blanks:
				choices = self.CHOICE_PATTERN.findall(blank)

				if not choices:
					raise ValidationError(
						f"Text #{i + 1}: invalid blank — must contain at least one {{{{choice}}}}."
					)

				for choice_text, marker in choices:
					if not choice_text.strip():
						raise ValidationError(
							f"Text #{i + 1}: blank contains an empty choice."
						)

				correct = [c for c, marker in choices if marker == "*"]

				if len(correct) == 0:
					raise ValidationError(
						f"Text #{i + 1}: blank '<({blank})>' has no correct answer. "
						f"Mark exactly one with *."
					)

				if len(correct) > 1:
					raise ValidationError(
						f"Text #{i + 1}: blank '<({blank})>' has {len(correct)} correct answers "
						f"({', '.join(correct)}). Mark exactly one with *."
					)

	@property
	def content_model(self) -> FillInTheBlankContent:
		return FillInTheBlankContent.from_json(self.content)
