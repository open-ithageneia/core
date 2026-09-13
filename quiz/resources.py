import re
import threading
import uuid
import zipfile
from io import BytesIO
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from import_export import resources

from quiz.models import (
	DragAndDrop,
	DragAndDropValue,
	FillInTheBlank,
	FillInTheBlankText,
	Listening,
	ListeningPart,
	MatchPair,
	Matching,
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

	**Where content is written.** A question's content is child rows now, and a
	row needs its parent's pk — so the scalar columns are set in
	``before_save_instance`` and the children are written in
	``after_save_instance``. Children are deleted and recreated rather than
	diffed: ``skip_unchanged = False`` means every import rewrites the content
	wholesale, which is exactly what assigning a whole new ``content`` dict used
	to do. The semantics are unchanged; only the place they happen moved.
	"""

	EXPORT_HEADERS: list[str] = []
	# Relations ``get_export_row`` walks. Exports iterate the whole table, so
	# without these an export is a query per question per relation.
	EXPORT_PREFETCH: tuple[str, ...] = ()

	# ------------------------------------------------------------------
	# Export: flatten the content tables into the same columns used by import
	# ------------------------------------------------------------------

	def get_export_row(self, instance) -> list:
		"""Return a flat list of cell values for *instance*.

		Subclasses MUST override this.
		"""
		raise NotImplementedError

	def get_export_headers(self, queryset) -> list:
		"""Column names for this export.

		A hook rather than a plain constant because a type with a variable number
		of child rows has a variable number of columns — see ``StatementResource``.
		"""
		return self.EXPORT_HEADERS

	def export(self, *args, queryset=None, **kwargs):
		"""Build a tablib Dataset with flat import-compatible columns."""
		import tablib

		if queryset is None:
			queryset = self.get_queryset()

		headers = self.get_export_headers(queryset)
		if not headers:
			# Fallback to default behaviour if subclass doesn't define headers
			return super().export(*args, queryset=queryset, **kwargs)

		if self.EXPORT_PREFETCH:
			queryset = queryset.prefetch_related(*self.EXPORT_PREFETCH)
			rows = queryset.iterator(chunk_size=100)
		else:
			rows = queryset.iterator()

		dataset = tablib.Dataset(headers=headers)
		for instance in rows:
			dataset.append(self.get_export_row(instance))

		return dataset

	class Meta:
		# ``content`` is not a field any more — each resource maps the flat
		# spreadsheet columns onto real columns and child rows itself.
		fields = ("id", "category")
		skip_unchanged = False
		abstract = True


class StatementResource(AbstractQuizResource):
	EXPORT_HEADERS = [
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
		*[
			col
			for i in range(1, 5)
			for col in (f"choice{i}_text", f"choice{i}_image", f"choice{i}_is_correct")
		],
	]
	EXPORT_PREFETCH = ("choices", "part")
	# What EXPORT_HEADERS declares, and the floor for a sized export so the
	# sheet keeps its familiar shape when every question has fewer.
	DEFAULT_CHOICE_COLUMNS = 4

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
		"""The choice rows described by the sheet, in column order.

		A choice with neither text nor an image is skipped — the same rule the
		``statement_choice_has_text_or_image`` constraint now enforces in the
		database.
		"""
		choices = []

		for i in self.get_choice_numbers(row):
			text = row.get(f"choice{i}_text")
			image_data = row.get(f"choice{i}_image")
			is_correct = row.get(f"choice{i}_is_correct")

			if not text and _is_blank(image_data):
				continue

			choices.append(
				{
					"text": text or "",
					"is_correct": _parse_bool(is_correct),
					"image_id": _import_image_column(image_data, title=f"Choice {i}"),
				}
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

	def after_save_instance(self, instance, row, **kwargs):
		choices = self.build_choices(row)

		instance.choices.all().delete()
		StatementChoice.objects.bulk_create(
			[
				StatementChoice(statement=instance, order=order, **choice)
				for order, choice in enumerate(choices)
			]
		)

		# The model can only check this once the choices exist, and they did not
		# when the parent was saved — so the importer checks it here, keeping the
		# guarantee the pre-save content dict used to give.
		if (
			choices
			and instance.type == Statement.StatementType.MULTIPLE_CHOICE
			and not any(choice["is_correct"] for choice in choices)
		):
			raise ValueError(
				"Multiple-choice questions must have at least one correct choice."
			)

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

	# Columns before the choice ones, and how many cells each choice takes.
	FIXED_EXPORT_COLUMNS = 10
	CELLS_PER_CHOICE = 3

	def get_export_headers(self, queryset) -> list:
		"""Size the choice columns to the questions actually being exported.

		The declared ``EXPORT_HEADERS`` assumes four choices. A question with any
		other number produced a row of a different width, which tablib rejects
		outright — so exporting anything but a four-choice question failed. The
		count comes from the data instead.
		"""
		widest = max(
			(question.choices.count() for question in queryset),
			default=self.DEFAULT_CHOICE_COLUMNS,
		)
		count = max(widest, self.DEFAULT_CHOICE_COLUMNS)

		return self.EXPORT_HEADERS[: self.FIXED_EXPORT_COLUMNS] + [
			col
			for i in range(1, count + 1)
			for col in (f"choice{i}_text", f"choice{i}_image", f"choice{i}_is_correct")
		]

	def export(self, *args, queryset=None, **kwargs):
		# The row builder has to pad to the same width the headers were sized to.
		if queryset is None:
			queryset = self.get_queryset()
		self._export_choice_columns = (
			len(self.get_export_headers(queryset)) - self.FIXED_EXPORT_COLUMNS
		) // self.CELLS_PER_CHOICE
		return super().export(*args, queryset=queryset, **kwargs)

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
		columns = getattr(self, "_export_choice_columns", self.DEFAULT_CHOICE_COLUMNS)
		for index in range(columns):
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
	EXPORT_PREFETCH = ("values",)

	class Meta(AbstractQuizResource.Meta):
		model = DragAndDrop

	def before_save_instance(self, instance, row, **kwargs):
		instance.left_title = row.get("left_title", "") or ""
		instance.right_title = row.get("right_title", "") or ""

	def after_save_instance(self, instance, row, **kwargs):
		instance.values.all().delete()

		values = []
		for side, column in (
			(DragAndDropValue.Side.LEFT, "left_values"),
			(DragAndDropValue.Side.RIGHT, "right_values"),
		):
			texts = [v.strip() for v in row.get(column, "").split(",") if v.strip()]
			values.extend(
				DragAndDropValue(question=instance, side=side, text=text, order=order)
				for order, text in enumerate(texts)
			)

		DragAndDropValue.objects.bulk_create(values)

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		values = list(instance.values.all())

		def texts(side):
			return ", ".join(v.text for v in values if v.side == side)

		return [
			instance.id,
			instance.category_id,
			instance.left_title,
			instance.right_title,
			texts(DragAndDropValue.Side.LEFT),
			texts(DragAndDropValue.Side.RIGHT),
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
	]
	EXPORT_PREFETCH = ("pairs",)

	class Meta(AbstractQuizResource.Meta):
		model = Matching

	def parse_pair_item(self, item: str):
		if item.startswith(self.ASSET_PREFIX):
			return item[len(self.ASSET_PREFIX) :], True
		return item, False

	def extract_pairs(self, pairs):
		"""Turn the ``left_right`` cell syntax into ``MatchPair`` kwargs.

		This used to synthesise ``id``/``matched_id`` from the loop index, which is
		what gave away that those integers were bookkeeping rather than data. The
		pair row is the pairing now, so there is nothing left to number.
		"""
		parsed = []

		for pair in pairs:
			if self.ITEM_PAIR_SEPARATOR not in pair:
				raise ValueError(
					f"Item '{pair}' is not in the expected 'left{self.ITEM_PAIR_SEPARATOR}right' format."
				)
			left_item, right_item = pair.split(self.ITEM_PAIR_SEPARATOR, maxsplit=1)

			left_item, is_left_asset = self.parse_pair_item(left_item)
			right_item, is_right_asset = self.parse_pair_item(right_item)

			parsed.append(
				{
					"left_text": "" if is_left_asset else left_item.strip(),
					"left_image_id": int(left_item.strip()) if is_left_asset else None,
					"right_text": "" if is_right_asset else right_item.strip(),
					"right_image_id": (
						int(right_item.strip()) if is_right_asset else None
					),
				}
			)

		return parsed

	def before_save_instance(self, instance, row, **kwargs):
		instance.left_title = row.get("left_title", "") or ""
		instance.right_title = row.get("right_title", "") or ""

	def after_save_instance(self, instance, row, **kwargs):
		raw_pairs = row.get("items", "") or ""
		pairs = [v.strip() for v in raw_pairs.split(self.ITEM_SEPARATOR) if v.strip()]

		instance.pairs.all().delete()
		MatchPair.objects.bulk_create(
			[
				MatchPair(question=instance, order=order, **pair)
				for order, pair in enumerate(self.extract_pairs(pairs))
			]
		)

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def _serialize_item(self, text: str, image_id) -> str:
		"""Convert one side of a pair back to its string representation."""
		if image_id:
			return f"{self.ASSET_PREFIX}{image_id}"
		return text

	def get_export_row(self, instance):
		pairs = [
			f"{self._serialize_item(pair.left_text, pair.left_image_id)}"
			f"{self.ITEM_PAIR_SEPARATOR}"
			f"{self._serialize_item(pair.right_text, pair.right_image_id)}"
			for pair in instance.pairs.all()
		]

		return [
			instance.id,
			instance.category_id,
			instance.left_title,
			instance.right_title,
			f" {self.ITEM_SEPARATOR} ".join(pairs),
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
	EXPORT_PREFETCH = ("texts",)

	class Meta(AbstractQuizResource.Meta):
		model = FillInTheBlank

	def before_save_instance(self, instance, row, **kwargs):
		instance.show_answers_as_choices = _parse_bool(
			row.get("show_answers_as_choices", False)
		)
		instance.prompt_image_id = _import_image_column(
			row.get("prompt_image"), title="Prompt"
		)

	def after_save_instance(self, instance, row, **kwargs):
		texts = []
		i = 1
		while f"text_{i}" in row and row[f"text_{i}"]:
			texts.append(row[f"text_{i}"])
			i += 1

		instance.texts.all().delete()
		FillInTheBlankText.objects.bulk_create(
			[
				FillInTheBlankText(question=instance, text=text, order=order)
				for order, text in enumerate(texts)
			]
		)

		# The sheet has no extra-choices column, and assigning a whole new content
		# dict always dropped any that were set in the admin. Kept as it was so an
		# import behaves the same as before, rather than quietly changing on the
		# people who rely on it.
		instance.extra_choices.all().delete()

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		texts = [t.text for t in instance.texts.all()]

		row = [
			instance.id,
			instance.category_id,
			"true" if instance.show_answers_as_choices else "false",
			instance.prompt_image_id or "",
		]

		for i in range(self.MAX_EXPORT_TEXTS):
			row.append(texts[i] if i < len(texts) else "")

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
	EXPORT_PREFETCH = ("answers__alternatives",)

	class Meta(AbstractQuizResource.Meta):
		model = OpenEnded

	@staticmethod
	def _parse_texts(row):
		"""``"a|b, c"`` → ``[["a", "b"], ["c"]]`` — comma separates answers, pipe
		separates the alternatives of one answer."""
		texts = []
		for value in (row.get("texts", "") or "").split(","):
			value = value.strip()
			if not value:
				continue
			alternatives = [a.strip() for a in value.split("|") if a.strip()]
			if alternatives:
				texts.append(alternatives)
		return texts

	def before_save_instance(self, instance, row, **kwargs):
		instance.prompt_text = row.get("prompt_text") or ""
		instance.prompt_image_id = _import_image_column(
			row.get("prompt_image"), title="Prompt"
		)

		min_correct_answers = row.get("min_correct_answers")
		if not min_correct_answers:
			min_correct_answers = len(self._parse_texts(row))
		instance.min_correct_answers = int(min_correct_answers)

	def after_save_instance(self, instance, row, **kwargs):
		texts = self._parse_texts(row)

		instance.answers.all().delete()

		alternatives = []
		for order, alts in enumerate(texts):
			answer = OpenEndedAnswer.objects.create(question=instance, order=order)
			alternatives.extend(
				OpenEndedAlternative(answer=answer, text=text, order=alt_order)
				for alt_order, text in enumerate(alts)
			)
		OpenEndedAlternative.objects.bulk_create(alternatives)

		# Same reason as StatementResource: the count only exists once the rows do.
		if texts and instance.min_correct_answers > len(texts):
			raise ValueError(
				f"min_correct_answers ({instance.min_correct_answers}) cannot exceed "
				f"the number of available answers ({len(texts)})."
			)

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		text_parts = [
			"|".join(alt.text for alt in answer.alternatives.all())
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
