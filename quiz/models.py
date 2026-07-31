import os
import uuid
from abc import abstractmethod, ABCMeta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.urls import reverse
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
	"""Dynamic django-jsonform schema: scope the ``areas`` enum to the map
	level of the instance being edited (falls back to the default level on
	the admin "add" form where no instance is bound)."""
	level = int(getattr(instance, "level", None) or MapPointerContent.DEFAULT_LEVEL)
	return MapPointerContent.build_schema(
		level,
		# The area picker searches within one level, so the level is part of the
		# endpoint it queries (see MapPointerAdmin.area_options_view).
		area_options_url=reverse(
			"admin:quiz_mappointer_area_options", kwargs={"level": level}
		),
	)


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
	LISTENING = "LISTENING"

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


class ListeningPart(TimeStampedModel):
	"""One section of a listening question, with the description that introduces
	it.

	A part knows nothing about its questions — a ``Statement`` points at the part
	it belongs to, not the other way around. Parts carry no name or number: they
	are ordered by creation and the UI labels them Α, Β, … by position. The first
	part is usually the true/false statements and the second the multiple-choice
	questions, but the mapping is not enforced.
	"""

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
		# Nothing names a part, so its description doubles as the label in the
		# admin — the questions inline picks a part from a dropdown.
		lines = self.description.strip().splitlines()
		label = lines[0][:60] if lines else f"part {self.pk}"
		return f"{label} (listening {self.listening_id})"

	@property
	def position(self):
		"""1-based position among the parts of its listening question — what makes
		this part Μέρος Α or Μέρος Β, since parts have no name of their own."""
		ids = list(
			ListeningPart.objects.filter(listening_id=self.listening_id).values_list(
				"id", flat=True
			)
		)
		return ids.index(self.id) + 1

	@classmethod
	def at_position(cls, listening, position):
		"""The part of *listening* at *position*, creating the parts up to it when
		the group doesn't have that many yet. Returns ``(part, created)``, where
		*created* says whether any had to be added.

		Positions are how both the admin and the importer address parts: a part
		being created in the same save has no pk to point at yet, and a spreadsheet
		has no pk to write down.
		"""
		parts = list(cls.objects.filter(listening=listening))
		created = len(parts) < position
		while len(parts) < position:
			parts.append(cls.objects.create(listening=listening))
		return parts[position - 1], created


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

	listening = models.ForeignKey(
		"Listening",
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="questions",
		help_text="Set when this statement is one part of a listening question.",
	)
	part = models.ForeignKey(
		ListeningPart,
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
		# The part carries its own listening FK, so the two could disagree.
		if self.part_id and self.part.listening_id != self.listening_id:
			raise ValidationError(
				{"part": "The part must belong to the same listening question."}
			)

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

	def _validate_content(self):
		data = self.content_model
		if self.type == self.StatementType.MULTIPLE_CHOICE:
			if not any(choice.is_correct for choice in data.choices):
				raise ValidationError(
					"Multiple-choice questions must have at least one correct choice."
				)


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
	"""An audio comprehension question: one clip, played a limited number of
	times, followed by the questions asked about it, split into parts.

	The parts are ``ListeningPart`` rows (``parts``), each holding the
	description that introduces it. The questions are ordinary ``Statement`` rows
	linked through ``Statement.listening`` — one ``TRUE_FALSE`` statement and N
	``MULTIPLE_CHOICE`` ones — each pointing at the part it belongs to. Nothing
	about the group itself is free-form, so it has real columns instead of a JSON
	``content`` field.
	"""

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

	def _parse_content(self):
		# This type has no JSON content — the questions come from the reverse
		# ``questions`` relation and everything else is a column. ``AbstractQuiz``
		# still calls this from ``clean()``, so it has to return something.
		return None

	def _validate_content(self):
		# A group being created has no questions yet, and the admin saves the
		# parent before its inlines, so this only catches programmatic edits.
		# ``ListeningQuestionInline``'s formset is the gate for admin saves.
		if not self.pk:
			return
		types = list(self.questions.values_list("type", flat=True))
		if types:
			validate_listening_question_types(types)


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
		seen_areas: dict[str, int] = {}
		for idx, group in enumerate(data.texts):
			label = group.alternatives[0] if group.alternatives else ""
			if len(set(group.areas)) != len(group.areas):
				raise ValidationError(
					f"Answer '{label}' lists the same area more than once."
				)
			for area in group.areas:
				if area not in valid_areas:
					raise ValidationError(
						f"Area '{area}' is not a valid level-{self.level} area."
					)
				# Two answers sharing an area would make that area ambiguous:
				# whichever answer is placed there could be scored as correct.
				if seen_areas.setdefault(area, idx) != idx:
					raise ValidationError(
						f"Area '{area}' is used by more than one answer."
					)
