import re
import threading
import uuid
import zipfile
from io import BytesIO
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.db.models import Count, Max
from import_export import resources

from quiz.models import (
	DragAndDrop,
	DragAndDropValue,
	FillInTheBlank,
	FillInTheBlankText,
	Listening,
	ListeningPart,
	Matching,
	MatchPair,
	OpenEnded,
	OpenEndedAlternative,
	OpenEndedAnswer,
	QuizAsset,
	Statement,
	StatementChoice,
)

# ---------------------------------------------------------------------------
# Thread-local store for images extracted from a ZIP upload.
# Populated by ``load_images_from_zip()`` before django-import-export
# processes rows, and cleared by ``clear_image_store()`` afterwards.
# Maps normalised filename (lowercase, no directory prefix) → bytes.
# ---------------------------------------------------------------------------
_image_store = threading.local()

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff"}
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".webm"}
_MEDIA_EXTENSIONS = _IMAGE_EXTENSIONS | _AUDIO_EXTENSIONS


def load_images_from_zip(zip_bytes: bytes) -> bytes:
	"""Extract images from a ZIP archive and stash them in the thread-local.

	Returns the raw bytes of the **first** spreadsheet file found inside the
	ZIP (.xlsx, .xls, or .csv) so that django-import-export can process it.
	"""
	_image_store.images = {}
	spreadsheet_bytes = None

	with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
		for name in zf.namelist():
			# Skip directories and macOS resource-fork junk.
			if name.endswith("/") or "/__MACOSX" in name or name.startswith("__MACOSX"):
				continue

			suffix = PurePosixPath(name).suffix.lower()

			if suffix in (".xlsx", ".xls", ".csv"):
				if spreadsheet_bytes is None:
					spreadsheet_bytes = zf.read(name)
			elif suffix in _MEDIA_EXTENSIONS:
				# Key = filename only (lowered), so users just type "img.png".
				key = PurePosixPath(name).name.lower()
				_image_store.images[key] = zf.read(name)

	if spreadsheet_bytes is None:
		raise ValueError(
			"The ZIP archive must contain at least one .xlsx, .xls, or .csv file."
		)

	return spreadsheet_bytes


def clear_image_store():
	"""Remove all cached images from the thread-local store."""
	_image_store.images = {}


def _get_image_bytes(filename: str) -> bytes | None:
	"""Look up *filename* in the thread-local image store."""
	store: dict = getattr(_image_store, "images", {})
	return store.get(filename.lower())


def _parse_bool(value) -> bool:
	"""Safely convert a spreadsheet cell to bool.

	Handles strings like "false"/"FALSE"/"0" that ``bool()`` would
	incorrectly treat as ``True``.
	"""
	if isinstance(value, bool):
		return value
	return str(value).strip().lower() in ("true", "1", "yes")


def _is_blank(value) -> bool:
	"""Return True when *value* is empty, None, or whitespace-only."""
	return value is None or str(value).strip() == ""


def _create_asset_from_bytes(
	file_bytes: bytes, filename: str, title: str = "", field: str = "image"
) -> int:
	"""Persist raw file bytes as a new QuizAsset and return its pk.

	*field* selects the target model field: ``"image"`` or ``"audio"``.
	"""
	suffix = PurePosixPath(filename).suffix or ".png"
	dest_name = f"{uuid.uuid4()}{suffix}"
	asset = QuizAsset.objects.create(
		title=title,
		**{field: ContentFile(file_bytes, name=dest_name)},
	)
	return asset.pk


def _import_asset_column(value, title: str = "", field: str = "image") -> int | None:
	"""Resolve an asset column value to a ``QuizAsset`` pk.

	The value can be one of:

	* **blank / None** → returns ``None``.
	* **integer (asset ID)** → validated against ``QuizAsset`` and returned
	  directly.  This path does *not* require a ZIP upload.
	* **filename string** → looked up in the thread-local media store
	  (populated from a ZIP upload) and persisted as a new ``QuizAsset``
	  on the given *field* (``"image"`` or ``"audio"``).
	"""
	if _is_blank(value):
		return None

	raw = str(value).strip()

	# --- path 1: existing asset ID (numeric) ---
	if int(float(raw)) > 0:
		asset_pk = int(float(raw))
		if not QuizAsset.objects.filter(pk=asset_pk).exists():
			raise ValueError(
				f"QuizAsset with ID {asset_pk} does not exist. "
				f"Provide a valid asset ID or a media filename inside a ZIP."
			)
		return asset_pk

	# --- path 2: filename from ZIP media store ---
	filename = raw
	file_bytes = _get_image_bytes(filename)

	if file_bytes is None:
		raise ValueError(
			f"File '{filename}' not found in the uploaded ZIP archive. "
			f"Make sure the file exists inside the ZIP."
		)

	return _create_asset_from_bytes(file_bytes, filename, title=title, field=field)


def _import_image_column(value, title: str = "") -> int | None:
	"""Resolve an image column value to a ``QuizAsset`` pk (see ``_import_asset_column``)."""
	return _import_asset_column(value, title=title, field="image")


def _import_audio_column(value, title: str = "") -> int | None:
	"""Resolve an audio column value to a ``QuizAsset`` pk (see ``_import_asset_column``)."""
	return _import_asset_column(value, title=title, field="audio")


class AbstractQuizResource(resources.ModelResource):
	"""Base resource for all quiz types.

	Provides:
	- Common Meta defaults (``fields``, ``skip_unchanged``).
	- A custom ``export()`` that produces flat spreadsheet columns matching
	  the import format (round-trip fidelity).

	Subclasses must set ``Meta.model`` and may extend ``Meta.fields``.
	They should also define ``EXPORT_HEADERS`` (list of column names) and
	override ``get_export_row(instance)`` → list of cell values.

	**The spreadsheet columns are unchanged by the move to content tables.**
	What changed is where they are written: the question's own columns are set
	in ``before_save_instance``, and its child rows in ``save_content``, which
	runs after the instance has a pk to point at.
	"""

	EXPORT_HEADERS: list[str] = []

	#: related rows ``get_export_row`` reads, fetched up front.
	export_prefetch: tuple = ()

	# ------------------------------------------------------------------
	# Import
	# ------------------------------------------------------------------

	def before_import_row(self, row, **kwargs):
		super().before_import_row(row, **kwargs)
		self.validate_content(row)

	def validate_content(self, row):
		"""Reject a malformed content cell before anything is written.

		``save_content`` runs from ``after_save_instance`` — after the question
		row is saved and its old children deleted — so a cell that first fails
		there leaves a question with none of its content behind whenever
		``IMPORT_EXPORT_USE_TRANSACTIONS`` is off. Parsing here is also what
		puts the error in the admin's import preview rather than at confirm
		time.
		"""

	def save_content(self, instance, row):
		"""Write the question's child rows. Called once *instance* has a pk.

		Replace, don't merge: ``skip_unchanged = False`` means every import
		rewrites a question's content wholesale, which is the semantics these
		sheets have always had. A re-import of the same row therefore clears the
		old children first.
		"""

	def after_save_instance(self, instance, row, **kwargs):
		super().after_save_instance(instance, row, **kwargs)
		self.save_content(instance, row)
		# The rules that span child rows can only see them now. Before the
		# content tables the whole question was validated in one ``save()``,
		# because it was one column; re-running validation here keeps a bad
		# sheet failing the import rather than landing half-valid.
		instance.full_clean()

	# ------------------------------------------------------------------
	# Export: flatten content rows back into the same columns used by import
	# ------------------------------------------------------------------

	def get_export_row(self, instance) -> list:
		"""Return a flat list of cell values for *instance*.

		Subclasses MUST override this.
		"""
		raise NotImplementedError

	def get_export_headers_for(self, queryset) -> list:
		"""The columns this export will carry.

		A hook for the types whose width depends on the data being exported;
		most are a fixed list.
		"""
		return self.EXPORT_HEADERS

	def export(self, *args, queryset=None, **kwargs):
		"""Build a tablib Dataset with flat import-compatible columns."""
		import tablib

		if queryset is None:
			queryset = self.get_queryset()

		headers = self.get_export_headers_for(queryset)
		if not headers:
			# Fallback to default behaviour if subclass doesn't define headers
			return super().export(*args, queryset=queryset, **kwargs)

		if self.export_prefetch:
			queryset = queryset.prefetch_related(*self.export_prefetch)

		dataset = tablib.Dataset(headers=headers)
		# chunk_size is what lets ``iterator()`` honour the prefetches above.
		for instance in queryset.iterator(chunk_size=200):
			dataset.append(self.get_export_row(instance))

		return dataset

	class Meta:
		fields = ("id", "category")
		skip_unchanged = False
		abstract = True


def _choice_columns(count) -> list:
	"""The ``choiceN_*`` column-triples for *count* choices."""
	return [
		column
		for index in range(1, count + 1)
		for column in (
			f"choice{index}_text",
			f"choice{index}_image",
			f"choice{index}_is_correct",
		)
	]


class StatementResource(AbstractQuizResource):
	# How many choice column-triples an ordinary sheet carries. Every row has to
	# be exactly as wide as the header or tablib rejects it, so a question
	# holding more than this widens the whole sheet rather than losing the
	# extras — see ``get_export_headers_for``.
	MIN_EXPORT_CHOICES = 4

	BASE_HEADERS = [
		"id",
		"type",
		"category",
		"prompt_text",
		"prompt_image",
		"prompt_audio",
		"listening",
		"part",
		"part_description",
		"order",
	]

	EXPORT_HEADERS = [*BASE_HEADERS, *_choice_columns(MIN_EXPORT_CHOICES)]

	#: Width of the export being built, set by ``get_export_headers_for``.
	_export_choices = MIN_EXPORT_CHOICES

	export_prefetch = ("choices", "part")

	class Meta(AbstractQuizResource.Meta):
		model = Statement
		fields = (
			"id",
			"type",
			"category",
		)

	choice_pattern = re.compile(r"choice(\d+)_text")

	def get_choice_numbers(self, row):
		"""Find all choice numbers present in the sheet."""
		numbers = []

		for key in row.keys():
			match = self.choice_pattern.match(key)
			if match:
				numbers.append(int(match.group(1)))

		return sorted(numbers)

	def build_choices(self, row):
		"""The choices the sheet describes, as unsaved ``StatementChoice`` rows."""
		choices = []

		for i in self.get_choice_numbers(row):
			text = row.get(f"choice{i}_text")
			image_data = row.get(f"choice{i}_image")
			is_correct = row.get(f"choice{i}_is_correct")

			# A column pair with neither text nor image is an unused slot in the
			# sheet, not an empty choice.
			if not text and _is_blank(image_data):
				continue

			choices.append(
				StatementChoice(
					text=text or "",
					is_correct=_parse_bool(is_correct),
					image_id=_import_image_column(image_data, title=f"Choice {i}"),
					order=len(choices),
				)
			)

		return choices

	def before_save_instance(self, instance, row, **kwargs):
		instance.prompt_text = row.get("prompt_text") or ""
		instance.prompt_image_id = _import_image_column(
			row.get("prompt_image"), title="Prompt"
		)
		instance.prompt_audio_id = _import_audio_column(
			row.get("prompt_audio"), title="Prompt audio"
		)

		instance.listening_id = self._resolve_listening(row)
		instance.part = self._resolve_part(row, instance.listening_id)
		instance.order = self._resolve_order(row)

	def save_content(self, instance, row):
		instance.choices.all().delete()
		choices = self.build_choices(row)
		for choice in choices:
			choice.statement = instance
		StatementChoice.objects.bulk_create(choices)

	@staticmethod
	def _resolve_listening(row) -> int | None:
		"""Resolve the ``listening`` column to a Listening pk, if valid."""
		value = row.get("listening")
		if _is_blank(value):
			return None

		listening_id = int(float(str(value).strip()))
		if not Listening.objects.filter(pk=listening_id).exists():
			raise ValueError(
				f"Listening question with ID {listening_id} does not exist. "
				f"Create the listening question first, then import its parts."
			)
		return listening_id

	@staticmethod
	def _resolve_part(row, listening_id) -> ListeningPart | None:
		"""Resolve the ``part`` column to the matching part of the listening
		question, creating the parts up to that position if the group doesn't have
		them yet.

		Parts have no name of their own, so they are addressed by position: 1 is
		the first part (shown as Μέρος Α), 2 the second, and so on. Defaults to the
		first. A non-blank ``part_description`` column sets the description of that
		part — it describes the part, not the row it arrives on, so every row of
		the same part may carry it.

		Statements that are not part of a listening question have no part.
		"""
		if listening_id is None:
			return None

		value = row.get("part")
		if _is_blank(value):
			position = 1
		else:
			try:
				position = int(float(str(value).strip()))
			except ValueError:
				raise ValueError(
					f"Invalid part '{value}'. Parts are addressed by position: "
					f"1 for the first part, 2 for the second, and so on."
				) from None
		if position < 1:
			raise ValueError(f"Invalid part '{value}'. The first part is 1.")

		part, _ = ListeningPart.at_position(Listening(pk=listening_id), position)

		description = row.get("part_description")
		if not _is_blank(description):
			description = str(description).strip()
			if part.description != description:
				part.description = description
				part.save(update_fields=["description", "updated_at"])

		return part

	@staticmethod
	def _resolve_order(row) -> int:
		"""Resolve the ``order`` column, defaulting to 0."""
		value = row.get("order")
		if _is_blank(value):
			return 0
		return int(float(str(value).strip()))

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_headers_for(self, queryset) -> list:
		"""Widen the sheet when some question holds more choices than the usual
		four.

		Truncating the row to a fixed four would be silent data loss: nothing
		caps a question at four choices, the extras would simply not be in the
		sheet, and re-importing it deletes them for good — ``save_content``
		replaces a question's choices wholesale. Import already reads however
		many ``choiceN_*`` columns it is given.
		"""
		widest = queryset.annotate(_choices=Count("choices")).aggregate(
			Max("_choices")
		)["_choices__max"]
		self._export_choices = max(self.MIN_EXPORT_CHOICES, widest or 0)
		return [*self.BASE_HEADERS, *_choice_columns(self._export_choices)]

	def get_export_row(self, instance):
		row = [
			instance.id,
			instance.type,
			instance.category_id,
			instance.prompt_text,
			instance.prompt_image_id or "",
			instance.prompt_audio_id or "",
			instance.listening_id or "",
			instance.part.position if instance.part_id else "",
			instance.part.description if instance.part_id else "",
			instance.order,
		]

		choices = list(instance.choices.all())
		for index in range(self._export_choices):
			if index < len(choices):
				choice = choices[index]
				row.append(choice.text)
				row.append(choice.image_id or "")
				row.append("true" if choice.is_correct else "false")
			else:
				row.extend(["", "", ""])

		return row


class DragAndDropResource(AbstractQuizResource):
	EXPORT_HEADERS = [
		"id",
		"category",
		"left_title",
		"right_title",
		"left_values",
		"right_values",
	]

	export_prefetch = ("values",)

	class Meta(AbstractQuizResource.Meta):
		model = DragAndDrop

	def before_save_instance(self, instance, row, **kwargs):
		instance.left_title = row.get("left_title", "") or ""
		instance.right_title = row.get("right_title", "") or ""

	def save_content(self, instance, row):
		instance.values.all().delete()

		def split(column):
			return [v.strip() for v in (row.get(column) or "").split(",") if v.strip()]

		DragAndDropValue.objects.bulk_create(
			[
				DragAndDropValue(
					question=instance, side=side, text=text, order=position
				)
				for side, column in (
					(DragAndDropValue.Side.LEFT, "left_values"),
					(DragAndDropValue.Side.RIGHT, "right_values"),
				)
				for position, text in enumerate(split(column))
			]
		)

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		values = list(instance.values.all())

		def joined(side):
			return ", ".join(value.text for value in values if value.side == side)

		return [
			instance.id,
			instance.category_id,
			instance.left_title,
			instance.right_title,
			joined(DragAndDropValue.Side.LEFT),
			joined(DragAndDropValue.Side.RIGHT),
		]


class MatchingResource(AbstractQuizResource):
	ITEM_SEPARATOR = "|"
	ITEM_PAIR_SEPARATOR = "_"
	ASSET_PREFIX = "$"

	EXPORT_HEADERS = [
		"id",
		"category",
		"left_title",
		"right_title",
		"items",
		"right_order",
	]

	export_prefetch = ("pairs",)

	class Meta(AbstractQuizResource.Meta):
		model = Matching

	def parse_pair_item(self, item: str):
		if item.startswith(self.ASSET_PREFIX):
			return item[len(self.ASSET_PREFIX) :], True
		return item, False

	def parse_right_order(self, row, count) -> list:
		"""The ``right_order`` column: where each pair's right item sits in its
		own column, given in the same order as ``items``.

		Blank — which is what every sheet written before the column existed
		says — means the right column runs parallel to the left.
		"""
		raw = row.get("right_order", "") or ""
		positions = [value.strip() for value in str(raw).split(",") if value.strip()]
		if not positions:
			return []
		if len(positions) != count:
			raise ValueError(
				f"'right_order' gives {len(positions)} positions for {count} "
				f"pairs. Give one per pair, in the same order as 'items'."
			)
		try:
			return [int(float(position)) for position in positions]
		except ValueError:
			raise ValueError(
				f"Invalid right_order '{raw}'. Expected whole numbers separated "
				f"by commas."
			) from None

	def extract_pairs(self, pairs, right_order=()):
		"""Turn the ``left_right | left_right`` cell into unsaved ``MatchPair`` rows.

		This used to synthesise an ``id`` and ``matched_id`` per side from the
		pair's index — bookkeeping the row itself now carries.
		"""
		rows = []

		for index, pair in enumerate(pairs):
			if self.ITEM_PAIR_SEPARATOR not in pair:
				raise ValueError(
					f"Item '{pair}' is not in the expected "
					f"'left{self.ITEM_PAIR_SEPARATOR}right' format."
				)
			left_item, right_item = pair.split(self.ITEM_PAIR_SEPARATOR, maxsplit=1)

			left_item, left_is_asset = self.parse_pair_item(left_item)
			right_item, right_is_asset = self.parse_pair_item(right_item)

			# The sheet pairs left_right, so the two columns run parallel
			# unless ``right_order`` places the right item somewhere else.
			match_pair = MatchPair(
				order=index,
				right_order=right_order[index] if right_order else index,
			)
			if left_is_asset:
				match_pair.left_image_id = int(left_item.strip())
			else:
				match_pair.left_text = left_item.strip()
			if right_is_asset:
				match_pair.right_image_id = int(right_item.strip())
			else:
				match_pair.right_text = right_item.strip()

			rows.append(match_pair)

		return rows

	def before_save_instance(self, instance, row, **kwargs):
		instance.left_title = row.get("left_title", "") or ""
		instance.right_title = row.get("right_title", "") or ""

	def split_items(self, row) -> list:
		"""The ``items`` cell, split into one ``left_right`` string per pair."""
		raw_pairs = row.get("items", "") or ""
		return [
			value.strip()
			for value in raw_pairs.split(self.ITEM_SEPARATOR)
			if value.strip()
		]

	def validate_content(self, row):
		# Parsing is pure, so doing it once here and again in ``save_content``
		# costs nothing and keeps neither of them holding state for the other.
		pairs = self.split_items(row)
		self.extract_pairs(pairs, self.parse_right_order(row, len(pairs)))

	def save_content(self, instance, row):
		instance.pairs.all().delete()

		pairs = self.split_items(row)
		match_pairs = self.extract_pairs(pairs, self.parse_right_order(row, len(pairs)))
		for match_pair in match_pairs:
			match_pair.question = instance
		MatchPair.objects.bulk_create(match_pairs)

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def _serialize_item(self, text, image_id) -> str:
		"""Convert one side of a pair back to its string representation."""
		if image_id:
			return f"{self.ASSET_PREFIX}{image_id}"
		return text

	def get_export_row(self, instance):
		# The row is the pairing, so the left → right mapping no longer has to be
		# rebuilt by matching ids across the two columns.
		rows = list(instance.pairs.all())
		pairs = [
			f"{self._serialize_item(pair.left_text, pair.left_image_id)}"
			f"{self.ITEM_PAIR_SEPARATOR}"
			f"{self._serialize_item(pair.right_text, pair.right_image_id)}"
			for pair in rows
		]

		return [
			instance.id,
			instance.category_id,
			instance.left_title,
			instance.right_title,
			f" {self.ITEM_SEPARATOR} ".join(pairs),
			# Written out even when the columns are parallel: the pairing is in
			# ``items`` and this is the only thing carrying where the right item
			# actually sits, so a re-import that had to guess would flatten a
			# deliberately shuffled column back into the answer.
			",".join(str(pair.right_order) for pair in rows),
		]


class FillInTheBlankResource(AbstractQuizResource):
	# Maximum number of text columns to export
	MAX_EXPORT_TEXTS = 5

	EXPORT_HEADERS = [
		"id",
		"category",
		"show_answers_as_choices",
		"prompt_image",
		*[f"text_{i}" for i in range(1, 6)],
	]

	export_prefetch = ("texts",)

	class Meta(AbstractQuizResource.Meta):
		model = FillInTheBlank

	def before_save_instance(self, instance, row, **kwargs):
		instance.show_answers_as_choices = _parse_bool(
			row.get("show_answers_as_choices", False)
		)
		instance.prompt_image_id = _import_image_column(
			row.get("prompt_image"), title="Prompt"
		)

	def save_content(self, instance, row):
		instance.texts.all().delete()
		# The sheet has no extra-choices column, so an import clears them — the
		# same thing it has always done, back when it rewrote the whole blob.
		instance.extra_choices.all().delete()

		position = 1
		while f"text_{position}" in row and row[f"text_{position}"]:
			# Saved one at a time rather than bulk-created: ``save()`` validates the
			# markup and derives the sentence's parts, and ``bulk_create`` does
			# neither. A question has a handful of sentences at most.
			FillInTheBlankText(
				question=instance,
				text=row[f"text_{position}"],
				order=position - 1,
			).save()
			position += 1

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		texts = [text.text for text in instance.texts.all()]

		row = [
			instance.id,
			instance.category_id,
			"true" if instance.show_answers_as_choices else "false",
			instance.prompt_image_id or "",
		]

		for index in range(self.MAX_EXPORT_TEXTS):
			row.append(texts[index] if index < len(texts) else "")

		return row


class OpenEndedResource(AbstractQuizResource):
	EXPORT_HEADERS = [
		"id",
		"category",
		"prompt_text",
		"prompt_image",
		"texts",
		"min_correct_answers",
	]

	export_prefetch = ("answers__alternatives",)

	class Meta(AbstractQuizResource.Meta):
		model = OpenEnded

	@staticmethod
	def _parse_texts(row):
		"""``"a|b, c"`` → ``[["a", "b"], ["c"]]`` — comma separates answers, pipe
		separates the spellings that all count as the same one."""
		answers = []
		for chunk in (row.get("texts", "") or "").split(","):
			chunk = chunk.strip()
			if not chunk:
				continue
			alternatives = [alt.strip() for alt in chunk.split("|") if alt.strip()]
			if alternatives:
				answers.append(alternatives)
		return answers

	def before_save_instance(self, instance, row, **kwargs):
		instance.prompt_text = row.get("prompt_text") or ""
		instance.prompt_image_id = _import_image_column(
			row.get("prompt_image"), title="Prompt"
		)
		min_correct_answers = row.get("min_correct_answers")
		if not min_correct_answers:
			min_correct_answers = len(self._parse_texts(row)) or 1
		instance.min_correct_answers = int(min_correct_answers)

	def save_content(self, instance, row):
		instance.answers.all().delete()

		for position, alternatives in enumerate(self._parse_texts(row)):
			answer = OpenEndedAnswer.objects.create(question=instance, order=position)
			OpenEndedAlternative.objects.bulk_create(
				[
					OpenEndedAlternative(answer=answer, text=text, order=index)
					for index, text in enumerate(alternatives)
				]
			)

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		text_parts = [
			"|".join(alternative.text for alternative in answer.alternatives.all())
			for answer in instance.answers.all()
		]

		return [
			instance.id,
			instance.category_id,
			instance.prompt_text,
			instance.prompt_image_id or "",
			", ".join(text_parts),
			instance.min_correct_answers,
		]
