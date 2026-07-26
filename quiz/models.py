import os
import uuid
from abc import abstractmethod, ABCMeta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django_jsonform.models.fields import JSONField

from open_ithageneia.models import ActivatableModel, TimeStampedModel

from .managers import AbstractQuizManager, StatementManager
from .schemas import (
	StatementChoiceContent,
	DragAndDropContent,
	MatchingContent,
	FillInTheBlankContent,
	OpenEndedContent,
	MapPointerContent,
	AREA_NAME_CHOICES_BY_LEVEL,
)


def _map_pointer_content_schema(instance=None):
	"""Dynamic django-jsonform schema: scope the ``area`` enum to the map
	level of the instance being edited (falls back to the default level on
	the admin "add" form where no instance is bound)."""
	level = getattr(instance, "level", None)
	return MapPointerContent.build_schema(level)


def get_quiz_asset_upload_to(instance, filename):
	_, ext = os.path.splitext(filename)

	return f"quizzes/assets/{uuid.uuid4()}{ext}"


class QuizAsset(TimeStampedModel):
	title = models.CharField(max_length=255, blank=True, default="")
	image = models.ImageField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)
	audio = models.FileField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)

	def __str__(self):
		return self.title if self.title else str(self.pk)

	class Meta:
		verbose_name_plural = "Quiz Assets"


class QuizCategory(TimeStampedModel):
	GEOGRAPHY = "GEOGRAPHY"
	CIVICS = "CIVICS"
	HISTORY = "HISTORY"
	CULTURE = "CULTURE"

	code = models.CharField(max_length=32, primary_key=True)
	name = models.CharField(max_length=64)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		verbose_name_plural = "Quiz Categories"
		ordering = ["order", "code"]

	def __str__(self):
		return self.name or self.code


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

	_cached_content_model = None

	@abstractmethod
	def _parse_content(self):
		"""Parse and validate self.content into the typed dataclass.
		Subclasses implement this. Must raise ValidationError on bad data."""
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

	content = JSONField(
		blank=True, default=dict, schema=StatementChoiceContent.STATEMENT_CONTENT_SCHEMA
	)

	second_part = models.OneToOneField(
		"self",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="first_part",
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

	@staticmethod
	def get_asset_audio(asset_id):
		if not asset_id:
			return None

		try:
			return QuizAsset.objects.get(id=asset_id).audio
		except QuizAsset.DoesNotExist:
			return None

	def get_choices_with_images(self):
		choices = self.content.get("choices", None)

		if not choices:
			return None

		asset_ids = [
			choice.get("asset_id") for choice in choices if choice.get("asset_id")
		]
		assets = QuizAsset.objects.in_bulk(asset_ids)

		for choice in choices:
			asset_id = choice.get("asset_id")
			asset = assets.get(asset_id)
			choice["image"] = asset.image if asset else None

		return choices

	def _parse_content(self):
		return StatementChoiceContent.from_json(self.content)

	def clean(self):
		super().clean()
		if self.second_part_id and self.second_part_id == self.id:
			raise ValidationError({"second_part": "A statement cannot link to itself."})

	def _validate_content(self):
		data = self.content_model
		if self.type == self.StatementType.MULTIPLE_CHOICE:
			if not any(choice.is_correct for choice in data.choices):
				raise ValidationError(
					"Multiple-choice questions must have at least one correct choice."
				)


class DragAndDrop(AbstractQuiz):
	INSTRUCTION_TEXT = "Σύρετε και αποθέστε στη σωστή θέση"

	content = JSONField(
		blank=True, default=list, schema=DragAndDropContent.DRAG_AND_DROP_CONTENT_SCHEMA
	)

	class Meta:
		verbose_name_plural = "Drag And Drop"

	def _parse_content(self):
		return DragAndDropContent.from_json(self.content)


class Matching(AbstractQuiz):
	INSTRUCTION_TEXT = "Αντιστοιχίστε τα σωστά ζεύγη"

	content = JSONField(
		blank=True, default=dict, schema=MatchingContent.MATCHING_CONTENT_SCHEMA
	)

	def _parse_content(self):
		return MatchingContent.from_json(self.content)

	class Meta:
		verbose_name_plural = "Matching"


class FillInTheBlank(AbstractQuiz):
	INSTRUCTION_TEXT = "Συμπληρώστε τα κενά"

	content = JSONField(
		blank=True,
		default=dict,
		schema=FillInTheBlankContent.FILL_IN_THE_BLANK_CONTENT_SCHEMA,
	)

	class Meta:
		verbose_name_plural = "Fill in the blank"

	def _parse_content(self):
		return FillInTheBlankContent.from_json(self.content)


class OpenEnded(AbstractQuiz):
	content = JSONField(
		blank=True,
		default=dict,
		schema=OpenEndedContent.OPEN_ENDED_CONTENT_SCHEMA,
	)

	class Meta:
		verbose_name_plural = "Open Ended"

	def _parse_content(self):
		return OpenEndedContent.from_json(self.content)

	def _validate_content(self):
		data = self.content_model
		if data.min_correct_answers < 1:
			raise ValidationError("min_correct_answers must be at least 1.")
		if data.min_correct_answers > len(data.texts):
			raise ValidationError(
				f"min_correct_answers ({data.min_correct_answers}) cannot exceed "
				f"the number of available answers ({len(data.texts)})."
			)


class MapPointer(AbstractQuiz):
	INSTRUCTION_TEXT = "Τοποθετήστε κάθε επιλογή στη σωστή περιοχή του χάρτη"

	class MapLevel(models.IntegerChoices):
		DECENTRALIZED_ADMIN = 1, "Decentralized administration (Αποκεντρωμένη διοίκηση)"
		REGION = 2, "Region (Περιφέρεια)"
		PREFECTURE_UNIT = 3, "Prefecture unit (Νομός / Νησί)"
		MUNICIPALITY = 4, "Municipality (Δήμος)"
		GEOGRAPHIC_DEPARTMENT = 5, "Geographic department (Γεωγραφικό διαμέρισμα)"

	level = models.PositiveSmallIntegerField(
		choices=MapLevel.choices,
		default=MapLevel.MUNICIPALITY,
		help_text="Administrative division level used for the map.",
	)

	content = JSONField(
		blank=True,
		default=dict,
		schema=_map_pointer_content_schema,
	)

	class Meta:
		verbose_name_plural = "Map Pointer"

	def _parse_content(self):
		return MapPointerContent.from_json(self.content)

	def _validate_content(self):
		data = self.content_model
		if data.min_correct_answers < 1:
			raise ValidationError("min_correct_answers must be at least 1.")
		if data.min_correct_answers > len(data.texts):
			raise ValidationError(
				f"min_correct_answers ({data.min_correct_answers}) cannot exceed "
				f"the number of available answers ({len(data.texts)})."
			)
		valid_areas = set(AREA_NAME_CHOICES_BY_LEVEL[int(self.level)])
		for group in data.texts:
			if group.area and group.area not in valid_areas:
				raise ValidationError(
					f"Area '{group.area}' is not a valid level-{self.level} area."
				)
