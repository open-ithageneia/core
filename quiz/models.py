import os
import re
import unicodedata
import uuid
from abc import ABCMeta
from collections import namedtuple

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase

from open_ithageneia.models import ActivatableModel, TimeStampedModel

from .managers import AbstractQuizManager, StatementManager


def fold_for_search(text: str) -> str:
	"""Lowercase and strip accents so area names match however they are typed
	(Greek is routinely typed without its tonos)."""
	stripped = "".join(
		char
		for char in unicodedata.normalize("NFD", text or "")
		if not unicodedata.combining(char)
	)
	return unicodedata.normalize("NFC", stripped).strip().casefold()


def get_quiz_asset_upload_to(instance, filename):
	_, ext = os.path.splitext(filename)

	return f"quizzes/assets/{uuid.uuid4()}{ext}"


class MapLevel(models.IntegerChoices):
	"""Administrative division levels the map questions can be asked at.

	Module-level rather than nested in ``MapPointer`` because ``MapArea`` — which
	is declared first, since map answers point at it — needs the same choices.
	``MapPointer.MapLevel`` is kept as an alias so existing references and
	migration 0017's ``choices=`` keep resolving.
	"""

	DECENTRALIZED_ADMIN = 1, "Decentralized administration (Αποκεντρωμένη διοίκηση)"
	REGION = 2, "Region (Περιφέρεια)"
	PREFECTURE_UNIT = 3, "Prefecture unit (Νομός / Νησί)"
	MUNICIPALITY = 4, "Municipality and islands (Δήμος και νησιά)"
	GEOGRAPHIC_DEPARTMENT = 5, "Geographic department (Γεωγραφικό διαμέρισμα)"


class QuizAsset(TimeStampedModel):
	title = models.CharField(max_length=255, blank=True, default="")
	image = models.ImageField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)
	audio = models.FileField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)

	def __str__(self):
		return self.title if self.title else str(self.pk)

	class Meta:
		verbose_name_plural = "Quiz Assets"


class MapArea(models.Model):
	"""One named area of the map, at one administrative level.

	Rows are generated from the GeoJSON the frontend draws (see
	``MAP_LEVEL_SOURCES`` and the ``sync_map_areas`` command) — ``name`` must stay
	byte-identical to the property the frontend matches answers against in
	``geo/util.ts``, which is why it is not edited by hand.

	This replaces the enum that used to be built by reading five GeoJSON files at
	module import: a renamed or split feature is now a row with real foreign keys
	pointing at it, so the questions it breaks can actually be found.
	"""

	level = models.PositiveSmallIntegerField(choices=MapLevel.choices)
	name = models.CharField(max_length=255)
	search_name = models.CharField(
		max_length=255,
		db_index=True,
		editable=False,
		help_text="Accent-stripped, casefolded name, for the area picker.",
	)

	class Meta:
		ordering = ["level", "name"]
		verbose_name = "Map area"
		verbose_name_plural = "Map areas"
		constraints = [
			models.UniqueConstraint(
				fields=["level", "name"], name="unique_map_area_per_level"
			),
		]

	def __str__(self):
		return f"{self.name} (level {self.level})"

	def save(self, *args, **kwargs):
		self.search_name = fold_for_search(self.name)
		super().save(*args, **kwargs)


class QuizCategory(TimeStampedModel):
	GEOGRAPHY = "GEOGRAPHY"
	CIVICS = "CIVICS"
	HISTORY = "HISTORY"
	CULTURE = "CULTURE"
	LISTENING = "LISTENING"

	code = models.CharField(max_length=32, primary_key=True)
	name = models.CharField(max_length=64)
	name_el = models.CharField(
		"Greek name",
		max_length=64,
		blank=True,
		default="",
		help_text="Name shown to the user. Falls back to the English name when empty.",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		verbose_name_plural = "Quiz Categories"
		ordering = ["order", "code"]

	def __str__(self):
		return self.name or self.code

	@property
	def label(self):
		"""The name to show the user: Greek if it has been filled in, otherwise
		the English name (and the code as a last resort)."""
		return self.name_el or self.name or self.code


class ModelABCMeta(ModelBase, ABCMeta):
	pass


def validate_min_correct_answers(min_correct: int, total: int):
	"""Shared rule for the two types that ask for *some* of their answers.

	Lives here rather than being copy-pasted into each type's validation, which
	is where it was before.
	"""
	if min_correct < 1:
		raise ValidationError("min_correct_answers must be at least 1.")
	if min_correct > total:
		raise ValidationError(
			f"min_correct_answers ({min_correct}) cannot exceed "
			f"the number of available answers ({total})."
		)


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

	# The prompt is a single-valued scalar on every type that has one, so it is a
	# column rather than a key inside a blob: it can be searched, ordered by, and
	# — for the assets — protected by a real foreign key.
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
		help_text="Audio played with the question.",
	)

	def clean(self):
		super().clean()
		self._validate_content()

	def _validate_content(self):
		"""Override for business-rule checks.

		Anything that counts child rows has to guard on ``self.pk``: a row being
		created has no children yet, and the admin saves a parent before its
		inlines. The inline formsets are the gate for admin saves — see
		``ListeningQuestionFormSet``, which has always worked this way.
		"""
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

	def _validate_content(self):
		# Choices are rows now, so a statement being created has none yet and the
		# admin saves the parent before the inline. ``StatementChoiceFormSet`` is
		# the gate there; this catches programmatic edits.
		if not self.pk:
			return
		if self.type == self.StatementType.MULTIPLE_CHOICE:
			if not self.choices.filter(is_correct=True).exists():
				raise ValidationError(
					"Multiple-choice questions must have at least one correct choice."
				)


class StatementChoice(models.Model):
	"""One selectable answer of a ``Statement``."""

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
		constraints = [
			# A choice the candidate cannot see is a bug, and the importer already
			# silently skipped these. Now the database says so.
			models.CheckConstraint(
				condition=~models.Q(text="") | models.Q(image__isnull=False),
				name="statement_choice_has_text_or_image",
			),
		]

	def __str__(self):
		return self.text or f"choice {self.pk}"


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
	``MULTIPLE_CHOICE`` ones — each pointing at the part it belongs to.

	This type was already relational before the rest caught up; it is the shape
	the others have now been converted to.
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

	# Exactly two columns, always — so they are two columns on the row rather
	# than a table that would need a "there must be exactly 2" constraint.
	left_title = models.TextField(blank=True, default="")
	right_title = models.TextField(blank=True, default="")

	class Meta:
		verbose_name_plural = "Drag And Drop"


class DragAndDropValue(models.Model):
	class Side(models.TextChoices):
		LEFT = "LEFT", "Left"
		RIGHT = "RIGHT", "Right"

	question = models.ForeignKey(
		DragAndDrop,
		on_delete=models.CASCADE,
		related_name="values",
	)
	side = models.CharField(max_length=5, choices=Side.choices)
	text = models.TextField()
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["side", "order", "id"]
		verbose_name = "Drag and drop value"
		verbose_name_plural = "Drag and drop values"

	def __str__(self):
		return self.text


class Matching(AbstractQuiz):
	INSTRUCTION_TEXT = "Αντιστοιχίστε τα σωστά ζεύγη"

	left_title = models.TextField(blank=True, default="")
	right_title = models.TextField(blank=True, default="")

	class Meta:
		verbose_name_plural = "Matching"


class MatchPair(models.Model):
	"""One correct pairing of a ``Matching`` question.

	The row *is* the pairing. The ``id``/``matched_id`` integers the client works
	with carried no meaning of their own — the importer synthesised them from the
	loop index — so they are regenerated on the way out instead of stored.
	"""

	question = models.ForeignKey(
		Matching,
		on_delete=models.CASCADE,
		related_name="pairs",
	)
	left_text = models.TextField(blank=True, default="")
	left_image = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
	)
	right_text = models.TextField(blank=True, default="")
	right_image = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Match pair"
		verbose_name_plural = "Match pairs"

	def __str__(self):
		left = self.left_text or self.left_image_id
		right = self.right_text or self.right_image_id
		return f"{left} → {right}"


class FillInTheBlank(AbstractQuiz):
	"""Sentences with blanks the candidate fills in.

	The sentence text stays a single string holding the authoring DSL
	(``<{{answer}}*, {{other}}>``) — that is markup, not data. Exploding its parse
	tree into tables would mean either storing derived rows that have to be
	re-derived on every edit, or making authors fill in formsets instead of
	typing a sentence. The structure *around* the sentences is relational like
	everything else.
	"""

	INSTRUCTION_TEXT = "Συμπληρώστε τα κενά"

	show_answers_as_choices = models.BooleanField(default=False)

	class Meta:
		verbose_name_plural = "Fill in the blank"

	def instruction_choices(self, parsed):
		"""The word bank offered above the question, or ``None``.

		There is no bank when the question does not ask for one, and none when a
		blank already offers its own options inline — the answers would give those
		away. Identical choice groups contribute once: the same blank repeated
		across sentences is one option, not several.

		*parsed* is the already-parsed texts, so the sentences are walked once per
		serialization rather than once here and again for the parts.
		"""
		if not self.show_answers_as_choices:
			return None
		if any(text.has_multiple_choices for text in parsed):
			return None

		choices = [choice.text for choice in self.extra_choices.all()]
		seen = set()
		for text in parsed:
			for group in text.choice_groups:
				if group and group not in seen:
					seen.add(group)
					choices.extend(group)
		return choices


# What ``FillInTheBlankText.parse()`` yields: the sentence broken into display
# parts, whether any blank offers a real choice between options, and the choice
# groups the question needs to build its instruction list. One parse, three
# answers — they all come from the same walk over the markup.
ParsedText = namedtuple("ParsedText", "parts has_multiple_choices choice_groups")


class FillInTheBlankText(models.Model):
	"""One sentence of a fill-in-the-blank question.

	The text is markup, not data: ``<{{answer}}*, {{other}}>`` marks a blank, and
	the ``*`` marks the correct option. It stays one string because that is how
	authors write it — exploding the parse tree into tables would mean either
	storing derived rows to re-derive on every edit, or making authors fill in a
	formset instead of typing a sentence. Parsing it is this model's job.
	"""

	BLANK_PATTERN = re.compile(r"<(.+?)>")
	CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")

	question = models.ForeignKey(
		FillInTheBlank,
		on_delete=models.CASCADE,
		related_name="texts",
	)
	text = models.TextField(
		help_text=(
			"Use <{{answer1}}*, {{answer2}}> for blanks, marking the correct one "
			"with *. E.g. Η Κως συνορεύει με <{{την Τουρκία}}*>"
		),
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank text"
		verbose_name_plural = "Fill in the blank texts"

	def __str__(self):
		return self.text

	def clean(self):
		super().clean()
		# Parsing is the validation: the markup either yields blanks with exactly
		# one correct choice each, or it raises.
		self.parse()

	def parse(self) -> ParsedText:
		"""Break the sentence into its display parts.

		Raises ``ValidationError`` on malformed markup, which is what makes this
		double as the field's validation.
		"""
		raw_blanks = self.BLANK_PATTERN.findall(self.text)

		if not raw_blanks:
			raise ValidationError(
				f"{self.text}: no blanks found. Use <({{{{answer}}}}*)> syntax."
			)

		has_multiple_choices = False
		for blank in raw_blanks:
			choices = self.CHOICE_PATTERN.findall(blank)

			if not choices:
				raise ValidationError(
					f"{blank}: invalid blank — must contain at least one {{{{choice}}}}."
				)

			for choice_text, _marker in choices:
				if not choice_text.strip():
					raise ValidationError(
						f"{choice_text}: blank contains an empty choice."
					)

			correct = [c for c, marker in choices if marker == "*"]

			if len(correct) == 0:
				raise ValidationError(
					f"blank '<({blank})>' has no correct answer. Mark exactly one with *."
				)

			if len(choices) > 1 and len(correct) == 1:
				has_multiple_choices = True

		parts = []
		choice_groups = []
		# split() alternates literal text and blank contents.
		for index, chunk in enumerate(self.BLANK_PATTERN.split(self.text)):
			if index % 2 == 0:
				if chunk:
					parts.append({"text": chunk, "is_blank": False})
				continue

			choices = [
				{"text": text, "is_correct": marker == "*"}
				for text, marker in self.CHOICE_PATTERN.findall(chunk)
			]
			# A blank shows no text of its own — that is the point of it.
			parts.append({"text": None, "is_blank": True, "choices": choices})
			choice_groups.append(tuple(choice["text"] for choice in choices))

		return ParsedText(parts, has_multiple_choices, choice_groups)


class FillInTheBlankExtraChoice(models.Model):
	"""A decoy offered alongside the real answers when the question shows its
	answers as a choice list."""

	question = models.ForeignKey(
		FillInTheBlank,
		on_delete=models.CASCADE,
		related_name="extra_choices",
	)
	text = models.TextField()
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank extra choice"
		verbose_name_plural = "Fill in the blank extra choices"

	def __str__(self):
		return self.text


class OpenEnded(AbstractQuiz):
	min_correct_answers = models.PositiveSmallIntegerField(default=1)

	class Meta:
		verbose_name_plural = "Open Ended"

	def _validate_content(self):
		if not self.pk:
			return
		validate_min_correct_answers(self.min_correct_answers, self.answers.count())


class OpenEndedAnswer(models.Model):
	"""One thing the candidate has to name. Its ``alternatives`` are the spellings
	and phrasings that all count as naming it."""

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
	text = models.TextField()
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Open ended alternative"
		verbose_name_plural = "Open ended alternatives"

	def __str__(self):
		return self.text


class MapPointer(AbstractQuiz):
	INSTRUCTION_TEXT = "Τοποθετήστε κάθε επιλογή στη σωστή περιοχή του χάρτη"

	# Kept as an alias so ``MapPointer.MapLevel`` still resolves for callers and
	# for migration 0017's ``choices=``.
	MapLevel = MapLevel

	level = models.PositiveSmallIntegerField(
		choices=MapLevel.choices,
		default=MapLevel.MUNICIPALITY,
		help_text="Administrative division level used for the map.",
	)
	show_answers = models.BooleanField(default=True)
	min_correct_answers = models.PositiveSmallIntegerField(default=1)

	class Meta:
		verbose_name_plural = "Map Pointer"

	def _validate_content(self):
		if not self.pk:
			return
		validate_min_correct_answers(self.min_correct_answers, self.answers.count())
		# The areas an answer points at have to exist at this question's level.
		# This used to compare strings against an enum built from GeoJSON at import
		# time; now it is a join, so changing the level surfaces what it breaks.
		wrong = (
			MapPointerAnswerArea.objects.filter(answer__question=self)
			.exclude(area__level=self.level)
			.select_related("area")
			.first()
		)
		if wrong:
			raise ValidationError(
				f"Area '{wrong.area.name}' is not a valid level-{self.level} area."
			)


class MapPointerAnswer(models.Model):
	question = models.ForeignKey(
		MapPointer,
		on_delete=models.CASCADE,
		related_name="answers",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer answer"
		verbose_name_plural = "Map pointer answers"

	def __str__(self):
		first = self.alternatives.first()
		return first.text if first else f"answer {self.pk}"


class MapPointerAlternative(models.Model):
	answer = models.ForeignKey(
		MapPointerAnswer,
		on_delete=models.CASCADE,
		related_name="alternatives",
	)
	text = models.TextField()
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer alternative"
		verbose_name_plural = "Map pointer alternatives"

	def __str__(self):
		return self.text


class MapPointerAnswerArea(models.Model):
	"""An area one answer may be placed on.

	More than one is allowed because a single answer can legitimately span
	several areas (e.g. a river crossing many prefectures) — placing the label on
	any of them counts as correct. Two answers may also share an area.

	An explicit row rather than a plain ``ManyToManyField`` so the authoring order
	survives: the client is handed the areas in the order they were entered.
	"""

	answer = models.ForeignKey(
		MapPointerAnswer,
		on_delete=models.CASCADE,
		related_name="areas",
	)
	area = models.ForeignKey(
		MapArea,
		on_delete=models.PROTECT,
		related_name="answers",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer answer area"
		verbose_name_plural = "Map pointer answer areas"
		constraints = [
			models.UniqueConstraint(
				fields=["answer", "area"], name="unique_area_per_map_pointer_answer"
			),
		]

	def __str__(self):
		return self.area.name
