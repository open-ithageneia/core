import json
import os
import re
import unicodedata
import uuid
from abc import ABCMeta
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase

from open_ithageneia.models import ActivatableModel, TimeStampedModel

from .managers import AbstractQuizManager, StatementManager


def get_quiz_asset_upload_to(instance, filename):
	_, ext = os.path.splitext(filename)

	return f"quizzes/assets/{uuid.uuid4()}{ext}"


def fold_for_search(text):
	"""Lowercase and strip accents so a name matches however it is typed — Greek
	is routinely typed without its tonos."""
	stripped = "".join(
		char
		for char in unicodedata.normalize("NFD", text)
		if not unicodedata.combining(char)
	)
	return unicodedata.normalize("NFC", stripped).strip().casefold()


def legacy_content_field(default=dict):
	"""The pre-refactor ``content`` JSON column: still on the row, read by nothing.

	Migration 0022 copied every one of these into the content tables and verified
	the copy. The column deliberately survives that migration — it is the only
	record of what the row looked like beforehand, so a mistake the verify step
	did not catch stays recoverable, and an older image redeployed against this
	database still finds the shape it expects.

	``editable=False`` keeps it out of every form and the admin. Do not read it
	and do not write it: rows created from now on get the empty default, so it is
	a frozen snapshot rather than a second copy kept in step. A follow-up
	migration drops these six columns once production has run on the content
	tables.
	"""
	return models.JSONField(blank=True, default=default, editable=False)


class QuizAsset(TimeStampedModel):
	title = models.CharField(max_length=255, blank=True, default="")
	image = models.ImageField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)
	audio = models.FileField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)

	def __str__(self):
		return self.title if self.title else str(self.pk)

	class Meta:
		verbose_name_plural = "Quiz Assets"

	@property
	def image_url(self):
		return self.image.url if self.image else None

	@property
	def audio_url(self):
		return self.audio.url if self.audio else None


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


class MapLevel(models.IntegerChoices):
	"""Administrative division levels the map can be drawn at.

	At module level rather than nested in ``MapPointer`` because ``MapArea``
	needs it too and is declared first. ``MapPointer.MapLevel`` stays as an
	alias.
	"""

	DECENTRALIZED_ADMIN = 1, "Decentralized administration (Αποκεντρωμένη διοίκηση)"
	REGION = 2, "Region (Περιφέρεια)"
	PREFECTURE_UNIT = 3, "Prefecture unit (Νομός / Νησί)"
	MUNICIPALITY = 4, "Municipality and islands (Δήμος και νησιά)"
	GEOGRAPHIC_DEPARTMENT = 5, "Geographic department (Γεωγραφικό διαμέρισμα)"


class MapArea(models.Model):
	"""One named area of the map, at one administrative level.

	Rows are generated from the GeoJSON the frontend draws, by
	``manage.py sync_map_areas`` — never by hand. ``name`` has to stay
	byte-identical to the property the client matches an answer against in
	``geo/util.ts``, so editing it here would silently break that match.

	The table exists so that a renamed or removed GeoJSON feature becomes a
	report — ``sync()`` names the areas that vanished and counts the answers
	still pointing at them — instead of what it used to be: answers that quietly
	stopped being correct, with no way to find them.
	"""

	# level → (GeoJSON filename, property key holding the Greek area name).
	#   1 = decentralized administrations (αποκεντρωμένες διοικήσεις) — GADM level 1
	#   2 = regions (περιφέρειες)                                     — GADM level 2
	#   3 = prefecture units (νομοί/νησιά)                            — peterdsp greece-prefectures-and-units
	#   4 = municipalities and islands (δήμοι και νησιά)              — GADM level 3
	#   5 = geographic departments (γεωγραφικά διαμερίσματα)          — derived (build_geographic_departments.py)
	LEVEL_SOURCES = {
		1: ("gadm41_GRC_1.json", "NL_NAME_1"),
		2: ("gadm41_GRC_2.json", "NL_NAME_2"),
		3: ("greece_prefecture_units.json", "name_greek"),
		4: ("gadm41_GRC_3.json", "NL_NAME_3"),
		5: ("greece_geographic_departments.json", "name"),
	}

	GEO_DATA_DIR = (
		Path(__file__).resolve().parent.parent / "frontend" / "js" / "geo" / "data"
	)

	level = models.PositiveSmallIntegerField(choices=MapLevel.choices)
	name = models.CharField(
		max_length=255,
		help_text="Greek name, exactly as it appears in the GeoJSON.",
	)
	search_name = models.CharField(
		max_length=255,
		db_index=True,
		editable=False,
		help_text="Accent-folded, casefolded form of the name, for the picker.",
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
		return self.name

	def save(self, *args, **kwargs):
		self.search_name = fold_for_search(self.name)
		super().save(*args, **kwargs)

	@classmethod
	def geojson_names(cls, level):
		"""The distinct area names the GeoJSON for *level* defines, sorted.

		Read on demand, never at import time: building a validation enum out of
		five GeoJSON files on every process start is what this table replaced.
		"""
		filename, name_key = cls.LEVEL_SOURCES[level]
		with open(cls.GEO_DATA_DIR / filename, encoding="utf-8") as handle:
			data = json.load(handle)
		return sorted({feature["properties"][name_key] for feature in data["features"]})

	@classmethod
	def sync(cls, level):
		"""Bring one level into line with its GeoJSON.

		Returns ``(added, deleted, blocked)`` — the names gained, the orphans
		removed, and ``(name, answer_count)`` for orphans an answer still points
		at. **Those are kept, not deleted**: an area that vanished from the
		GeoJSON while answers still reference it is the breakage this table
		exists to surface, so it is reported rather than quietly dropped.
		"""
		expected = set(cls.geojson_names(level))
		existing = {area.name: area for area in cls.objects.filter(level=level)}

		added = sorted(expected - set(existing))
		cls.objects.bulk_create(
			[
				cls(level=level, name=name, search_name=fold_for_search(name))
				for name in added
			]
		)

		deleted, blocked = [], []
		for name in sorted(set(existing) - expected):
			references = existing[name].answer_links.count()
			if references:
				blocked.append((name, references))
			else:
				deleted.append(name)
		if deleted:
			cls.objects.filter(level=level, name__in=deleted).delete()

		return added, deleted, blocked


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

	# The question as it is put to the candidate. Shared by every type that asks
	# one in words or with a picture, which is most of them: ``DragAndDrop``
	# leaves all three unset, and ``Listening`` carries its clip on ``audio``
	# instead, since there the clip is the question rather than an illustration
	# of it.
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
		"""1-based position among the parts of its listening question — what
		makes this part Μέρος Α or Μέρος Β, since parts have no name of their
		own."""
		ids = list(
			ListeningPart.objects.filter(listening_id=self.listening_id).values_list(
				"id", flat=True
			)
		)
		return ids.index(self.id) + 1

	@classmethod
	def at_position(cls, listening, position):
		"""The part of *listening* at *position*, creating the parts up to it
		when the group doesn't have that many yet. Returns ``(part, created)``,
		where *created* says whether any had to be added.

		Positions are how both the admin and the importer address parts: a part
		being created in the same save has no pk to point at yet, and a
		spreadsheet has no pk to write down.
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

	content = legacy_content_field()

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

	def _validate_content(self):
		# A question being created has no choices yet and the admin saves the
		# parent first, so this only catches programmatic saves;
		# ``StatementChoiceFormSet`` is the gate for admin ones.
		if not self.pk:
			return
		if self.type == self.StatementType.MULTIPLE_CHOICE:
			if not self.choices.filter(is_correct=True).exists():
				raise ValidationError(
					"Multiple-choice questions must have at least one correct choice."
				)

	class Meta:
		# ``order`` is what sequences the questions inside a listening part, so
		# it belongs on the model rather than at each call site: the serializer
		# reads ``part.questions.all()`` and has to get them in order whether or
		# not the queryset was prefetched. Standalone statements all sit at
		# ``order=0`` and so come back by id, as before.
		ordering = ["order", "id"]
		verbose_name_plural = "Statements (True/False or Multiple choice)"

	objects = StatementManager()


class StatementChoice(models.Model):
	"""One option offered for a ``Statement`` — text, a picture, or both."""

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
		# Deliberately no "must have text or an image" check constraint. It would
		# be true of every choice the admin and the importer produce, but the
		# backfill has to accept whatever the JSON columns are actually holding,
		# and a constraint that rejects one legacy row turns a deploy into a
		# crash-looping container. Worth adding once the data is known clean.

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

	left_title = models.CharField(max_length=255, blank=True, default="")
	right_title = models.CharField(max_length=255, blank=True, default="")

	content = legacy_content_field(default=list)

	class Meta:
		verbose_name_plural = "Drag And Drop"


class DragAndDropValue(models.Model):
	"""One draggable value, on one of the question's two sides."""

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

	left_title = models.CharField(max_length=255, blank=True, default="")
	right_title = models.CharField(max_length=255, blank=True, default="")

	content = legacy_content_field()

	class Meta:
		verbose_name_plural = "Matching"


class MatchPair(models.Model):
	"""One left item and the right item it matches.

	The row *is* the pairing. The ``id``/``matched_id`` the client receives are
	not stored: they were only ever bookkeeping — the importer synthesised them
	from the pair's index and nothing checked that the two columns agreed — so
	the serializer regenerates them from the row order instead. The numbers
	change; the relation they encode does not, and the relation is all the client
	reads them for.

	The two columns are ordered independently. ``order`` places the left item and
	``right_order`` the right one, because a matching exercise whose right column
	runs parallel to its left gives the answers away by position. They are equal
	for every question authored so far, but the shape has always been able to
	express otherwise and still can.

	A side with neither text nor image is *absent*, and the item is left out of
	its column. That is how the columns come to differ in length: a row with no
	left side is a right-column distractor that no left item matches, and a row
	with no right side is a left item with nothing to match — the two shapes the
	old JSON could hold that a pair cannot.
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
	order = models.PositiveSmallIntegerField(
		default=0, help_text="Position of the left item in its column."
	)
	right_order = models.PositiveSmallIntegerField(
		default=0,
		help_text=(
			"Position of the right item in its column. Leave equal to the left "
			"order unless the right column should be shuffled."
		),
	)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Match pair"
		verbose_name_plural = "Match pairs"

	def __str__(self):
		return f"{self.left_text or '—'} ↔ {self.right_text or '—'}"

	@property
	def has_left(self):
		return bool(self.left_text or self.left_image_id)

	@property
	def has_right(self):
		return bool(self.right_text or self.right_image_id)


class FillInTheBlank(AbstractQuiz):
	INSTRUCTION_TEXT = "Συμπληρώστε τα κενά"

	show_answers_as_choices = models.BooleanField(default=False)

	content = legacy_content_field()

	class Meta:
		verbose_name_plural = "Fill in the blank"

	def has_multiple_choices(self):
		"""Whether any blank offers the candidate a choice inline.

		A stored flag per sentence, so this is a read rather than a re-parse.
		"""
		return any(text.has_multiple_choices for text in self.texts.all())

	def instruction_choices(self):
		"""The word bank shown above the question, or ``None`` when there isn't one.

		Only offered when the question asks for it and no blank already carries
		its own choices — a blank that offers options inline needs no bank, and
		mixing the two would show the same words twice. Blanks whose choices
		repeat contribute once.
		"""
		if not self.show_answers_as_choices or self.has_multiple_choices():
			return None

		choices = [choice.text for choice in self.extra_choices.all()]
		seen = set()
		for text in self.texts.all():
			for part in text.parts.all():
				if not part.is_blank:
					continue
				texts = tuple(choice.text for choice in part.choices.all())
				if texts and texts not in seen:
					seen.add(texts)
					choices.extend(texts)
		return choices

	def rebuild_parts(self):
		"""Re-derive every sentence's parts. See ``FillInTheBlankText.save``."""
		for text in self.texts.all():
			text.rebuild_parts()


class FillInTheBlankText(models.Model):
	"""One sentence of a fill-in-the-blank question, stored as authored.

	``text`` holds the authoring DSL and is the source of truth::

	    Η Κως συνορεύει με <{{την Τουρκία}}*>
	    Το <{{1821}}*, {{1822}}> είναι η χρονιά της επανάστασης

	``<...>`` delimits a blank, ``{{...}}`` a choice within it, and a trailing
	``*`` marks the choice that is correct. A blank with several choices becomes
	a multiple-choice blank; a blank with one becomes a free-text answer.

	Saving parses that string into ``parts`` and their ``choices``. Those rows are
	derived — never edited directly — so the sentence stays one thing to author
	while the parse tree is queryable and the serializer no longer runs a regex
	per request. ``rebuild_parts()`` re-derives them for anything that writes
	around ``save()``.
	"""

	# The markup, and the only place it is defined.
	BLANK_PATTERN = re.compile(r"<(.+?)>")
	CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")

	question = models.ForeignKey(
		FillInTheBlank,
		on_delete=models.CASCADE,
		related_name="texts",
	)
	text = models.TextField(
		help_text=(
			"Use <{{answer}}*> for a blank and mark the correct choice with *. "
			'E.g. "Η Κως συνορεύει με <{{την Τουρκία}}*>".'
		),
	)
	has_multiple_choices = models.BooleanField(
		default=False,
		editable=False,
		help_text="Derived: whether any of this sentence's blanks offers a choice.",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank text"
		verbose_name_plural = "Fill in the blank texts"

	def __str__(self):
		return self.text[:80]

	def clean(self):
		super().clean()
		# Parsing is the validation: a sentence with no blank, an empty choice or
		# no correct answer is caught here rather than at display time.
		self.parse()

	def save(self, *args, **kwargs):
		# Validate before writing, so a malformed sentence never reaches the table
		# and the derived rows are never built from one.
		self.full_clean(exclude=["question"])
		super().save(*args, **kwargs)
		self.rebuild_parts()

	def blanks(self):
		"""The body of each blank, in order, markup and all."""
		return self.BLANK_PATTERN.findall(self.text)

	def choices_in(self, blank):
		"""``[(text, is_correct), …]`` for one blank body."""
		return [
			(choice, marker == "*")
			for choice, marker in self.CHOICE_PATTERN.findall(blank)
		]

	def correct_answer(self, blank):
		"""The choice marked correct in one blank body."""
		correct = [
			choice for choice, is_correct in self.choices_in(blank) if is_correct
		]
		return correct[0] if correct else "?"

	def parse(self):
		"""``{"parts": [...], "has_multiple_choices": bool}`` from the authored text.

		Raises ``ValidationError`` on bad markup — this doubles as the field's
		validation, so there is no second implementation of the rules to keep in
		step. ``rebuild_parts`` is what turns the result into rows.
		"""
		raw_blanks = self.blanks()
		if not raw_blanks:
			raise ValidationError(
				f"{self.text}: no blanks found. Use <({{{{answer}}}}*)> syntax."
			)

		has_multiple_choices = False
		for blank in raw_blanks:
			choices = self.choices_in(blank)
			if not choices:
				raise ValidationError(
					f"{blank}: invalid blank — must contain at least one {{{{choice}}}}."
				)
			for choice, _ in choices:
				if not choice.strip():
					raise ValidationError(f"{choice}: blank contains an empty choice.")

			correct = [choice for choice, is_correct in choices if is_correct]
			if not correct:
				raise ValidationError(
					f"blank '<({blank})>' has no correct answer. "
					f"Mark exactly one with *."
				)
			if len(choices) > 1 and len(correct) == 1:
				has_multiple_choices = True

		parts = []
		# split() on a single-group pattern alternates literal text and blanks.
		for index, chunk in enumerate(self.BLANK_PATTERN.split(self.text)):
			if index % 2 == 0:
				if chunk:
					parts.append({"text": chunk, "is_blank": False, "choices": []})
			else:
				parts.append(
					{
						"text": "",
						"is_blank": True,
						"choices": [
							{"text": choice, "is_correct": is_correct}
							for choice, is_correct in self.choices_in(chunk)
						],
					}
				)

		return {"parts": parts, "has_multiple_choices": has_multiple_choices}

	def rebuild_parts(self):
		"""Replace the derived rows with what the sentence now says.

		Wholesale rather than incremental: the string is the source of truth, so
		anything no longer in it is gone. Called by ``save()``, and by hand after a
		``bulk_create`` or any other write that goes around it.
		"""
		parsed = self.parse()

		if self.has_multiple_choices != parsed["has_multiple_choices"]:
			self.has_multiple_choices = parsed["has_multiple_choices"]
			type(self).objects.filter(pk=self.pk).update(
				has_multiple_choices=self.has_multiple_choices
			)

		self.parts.all().delete()
		for order, part in enumerate(parsed["parts"]):
			row = FillInTheBlankPart.objects.create(
				sentence=self,
				text=part["text"],
				is_blank=part["is_blank"],
				order=order,
			)
			FillInTheBlankChoice.objects.bulk_create(
				[
					FillInTheBlankChoice(
						part=row,
						text=choice["text"],
						is_correct=choice["is_correct"],
						order=position,
					)
					for position, choice in enumerate(part["choices"])
				]
			)


class FillInTheBlankPart(models.Model):
	"""One run of a sentence: either literal text, or a blank with its choices.

	Derived from ``FillInTheBlankText.text`` and rewritten whenever it is saved.
	Nothing should edit these rows directly — the next save of the sentence would
	throw the edit away.
	"""

	sentence = models.ForeignKey(
		FillInTheBlankText,
		on_delete=models.CASCADE,
		related_name="parts",
	)
	text = models.TextField(
		blank=True,
		default="",
		help_text="The literal text of this run. Empty for a blank.",
	)
	is_blank = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank part"
		verbose_name_plural = "Fill in the blank parts"

	def __str__(self):
		return "[blank]" if self.is_blank else self.text[:40]


class FillInTheBlankChoice(models.Model):
	"""One option inside a blank. Derived alongside its part."""

	part = models.ForeignKey(
		FillInTheBlankPart,
		on_delete=models.CASCADE,
		related_name="choices",
	)
	text = models.CharField(max_length=255)
	is_correct = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank choice"
		verbose_name_plural = "Fill in the blank choices"

	def __str__(self):
		return self.text


class FillInTheBlankExtraChoice(models.Model):
	"""A distractor offered alongside the real answers when the question shows
	its answers as choices."""

	question = models.ForeignKey(
		FillInTheBlank,
		on_delete=models.CASCADE,
		related_name="extra_choices",
	)
	text = models.CharField(max_length=255)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank extra choice"
		verbose_name_plural = "Fill in the blank extra choices"

	def __str__(self):
		return self.text


class MinCorrectAnswersMixin(models.Model):
	"""Shared by the two types that take a written answer and score it against a
	set of acceptable ones.

	The rule used to be copy-pasted into both models' validation.
	"""

	min_correct_answers = models.PositiveSmallIntegerField(default=1)

	class Meta:
		abstract = True

	def _validate_min_correct_answers(self):
		if self.min_correct_answers < 1:
			raise ValidationError("min_correct_answers must be at least 1.")
		# Counting answers needs a saved parent; the admin formset repeats it.
		if not self.pk:
			return
		available = self.answers.count()
		if available and self.min_correct_answers > available:
			raise ValidationError(
				f"min_correct_answers ({self.min_correct_answers}) cannot exceed "
				f"the number of available answers ({available})."
			)


class OpenEnded(MinCorrectAnswersMixin, AbstractQuiz):
	content = legacy_content_field()

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


class MapPointer(MinCorrectAnswersMixin, AbstractQuiz):
	INSTRUCTION_TEXT = "Τοποθετήστε κάθε επιλογή στη σωστή περιοχή του χάρτη"

	# Kept as an alias so ``MapPointer.MapLevel`` still resolves everywhere it is
	# referenced; the enum itself lives at module level, for ``MapArea``.
	MapLevel = MapLevel

	level = models.PositiveSmallIntegerField(
		choices=MapLevel.choices,
		default=MapLevel.MUNICIPALITY,
		help_text="Administrative division level used for the map.",
	)
	show_answers = models.BooleanField(default=True)

	content = legacy_content_field()

	class Meta:
		verbose_name_plural = "Map Pointer"

	def _validate_content(self):
		self._validate_min_correct_answers()
		if not self.pk:
			return
		# The level decides which areas the picker offers, so an answer pointing
		# at an area from another level could never be matched.
		wrong_level = (
			MapArea.objects.filter(answer_links__answer__question=self)
			.exclude(level=self.level)
			.values_list("name", flat=True)
			.distinct()
		)
		if wrong_level:
			raise ValidationError(
				f"These areas are not level-{self.level} areas: "
				f"{', '.join(sorted(wrong_level))}."
			)
		# One label cannot be placed on the same polygon twice, so a repeat is
		# always a mistake — and the client would draw the label once per link.
		# ``order_by()`` clears the model's default ordering, which Django would
		# otherwise add to the GROUP BY and count every link on its own.
		repeated = {
			group["area_id"]
			for group in MapPointerAnswerArea.objects.filter(answer__question=self)
			.values("answer_id", "area_id")
			.order_by()
			.annotate(links=models.Count("id"))
			.filter(links__gt=1)
		}
		if repeated:
			names = MapArea.objects.filter(pk__in=repeated).values_list(
				"name", flat=True
			)
			raise ValidationError(
				f"An answer lists the same area more than once: "
				f"{', '.join(sorted(names))}."
			)


class MapPointerAnswer(models.Model):
	"""One label the candidate places on the map.

	An answer may accept several areas: a river crossing many prefectures is
	correct on any of them. Two answers may also share an area — a polygon
	several answers pass through accepts each of them, and holds one label per
	answer placed there.
	"""

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
	text = models.CharField(max_length=255)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer alternative"
		verbose_name_plural = "Map pointer alternatives"

	def __str__(self):
		return self.text


class MapPointerAnswerArea(models.Model):
	"""An area an answer may be placed on.

	An explicit through table rather than a plain ``ManyToManyField`` because the
	order the areas were chosen in is part of what the client receives.
	"""

	answer = models.ForeignKey(
		MapPointerAnswer,
		on_delete=models.CASCADE,
		related_name="area_links",
	)
	area = models.ForeignKey(
		MapArea,
		on_delete=models.PROTECT,
		related_name="answer_links",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer answer area"
		verbose_name_plural = "Map pointer answer areas"
		# No unique (answer, area) constraint, for the same reason
		# ``StatementChoice`` has no check constraint: ``_validate_content``
		# rejects a repeated area, so none should exist, but the backfill must
		# not be the thing that discovers otherwise on a production deploy.

	def __str__(self):
		return self.area.name
