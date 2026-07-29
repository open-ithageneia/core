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
	FillInTheBlank,
	Listening,
	ListeningPart,
	Matching,
	QuizAsset,
	Statement,
	OpenEnded,
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
	"""

	EXPORT_HEADERS: list[str] = []

	# ------------------------------------------------------------------
	# Export: flatten JSON content back into the same columns used by import
	# ------------------------------------------------------------------

	def get_export_row(self, instance) -> list:
		"""Return a flat list of cell values for *instance*.

		Subclasses MUST override this.
		"""
		raise NotImplementedError

	def export(self, *args, queryset=None, **kwargs):
		"""Build a tablib Dataset with flat import-compatible columns."""
		import tablib

		if queryset is None:
			queryset = self.get_queryset()

		headers = self.EXPORT_HEADERS
		if not headers:
			# Fallback to default behaviour if subclass doesn't define headers
			return super().export(*args, queryset=queryset, **kwargs)

		dataset = tablib.Dataset(headers=headers)
		for instance in queryset.iterator():
			dataset.append(self.get_export_row(instance))

		return dataset

	class Meta:
		fields = ("id", "category", "content")
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

	class Meta(AbstractQuizResource.Meta):
		model = Statement
		fields = (
			"id",
			"type",
			"category",
			"content",
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
		choices = []

		for i in self.get_choice_numbers(row):
			text = row.get(f"choice{i}_text")
			image_data = row.get(f"choice{i}_image")
			is_correct = row.get(f"choice{i}_is_correct")

			if not text and _is_blank(image_data):
				continue

			choice = {
				"text": text or "",
				"is_correct": _parse_bool(is_correct),
			}

			asset_id = _import_image_column(image_data, title=f"Choice {i}")
			if asset_id is not None:
				choice["asset_id"] = asset_id

			choices.append(choice)

		return choices

	def before_save_instance(self, instance, row, **kwargs):
		choices = self.build_choices(row)

		instance.content = {
			"prompt_text": row.get("prompt_text") or "",
			"prompt_asset_id": _import_image_column(
				row.get("prompt_image"), title="Prompt"
			),
			"prompt_audio_asset_id": _import_audio_column(
				row.get("prompt_audio"), title="Prompt audio"
			),
			"choices": choices,
		}

		instance.listening_id = self._resolve_listening(row)
		instance.part = self._resolve_part(row, instance.listening_id)
		instance.order = self._resolve_order(row)

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

	def get_export_row(self, instance):
		content = instance.content or {}
		choices = content.get("choices", [])

		row = [
			instance.id,
			instance.type,
			instance.category_id,
			content.get("prompt_text", ""),
			content.get("prompt_asset_id", "") or "",
			content.get("prompt_audio_asset_id", "") or "",
			instance.listening_id or "",
			instance.part.position if instance.part_id else "",
			instance.part.description if instance.part_id else "",
			instance.order,
		]

		for choice in choices:
			row.append(choice.get("text", ""))
			row.append(choice.get("asset_id", "") or "")
			row.append("true" if choice.get("is_correct") else "false")

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

	class Meta(AbstractQuizResource.Meta):
		model = DragAndDrop

	def before_save_instance(self, instance, row, **kwargs):
		left_values = [
			v.strip() for v in row.get("left_values", "").split(",") if v.strip()
		]
		right_values = [
			v.strip() for v in row.get("right_values", "").split(",") if v.strip()
		]

		instance.content = [
			{
				"title": row.get("left_title", ""),
				"values": left_values,
			},
			{
				"title": row.get("right_title", ""),
				"values": right_values,
			},
		]

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		content = instance.content or []
		left = content[0] if len(content) > 0 else {}
		right = content[1] if len(content) > 1 else {}

		return [
			instance.id,
			instance.category_id,
			left.get("title", ""),
			right.get("title", ""),
			", ".join(left.get("values", [])),
			", ".join(right.get("values", [])),
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

	class Meta(AbstractQuizResource.Meta):
		model = Matching

	def parse_pair_item(self, item: str):
		if item.startswith(self.ASSET_PREFIX):
			return item[len(self.ASSET_PREFIX) :], True
		return item, False

	@staticmethod
	def get_item_object(identifier, item, is_asset, matched_id):
		obj = {
			"id": identifier,
			"matched_id": matched_id,
		}

		if is_asset:
			obj["asset_id"] = int(item.strip())
		else:
			obj["text"] = item.strip()

		return obj

	def extract_pairs(self, pairs):
		left_objects = []
		right_objects = []

		for idx, pair in enumerate(pairs, start=1):
			if self.ITEM_PAIR_SEPARATOR not in pair:
				raise ValueError(
					f"Item '{pair}' is not in the expected 'left{self.ITEM_PAIR_SEPARATOR}right' format."
				)
			left_item, right_item = pair.split(self.ITEM_PAIR_SEPARATOR, maxsplit=1)

			left_item, is_left_item_asset = self.parse_pair_item(left_item)
			right_item, is_right_item_asset = self.parse_pair_item(right_item)

			left_obj = self.get_item_object(
				idx, left_item, is_left_item_asset, idx + len(pairs)
			)
			right_obj = self.get_item_object(
				idx + len(pairs), right_item, is_right_item_asset, idx
			)

			left_objects.append(left_obj)
			right_objects.append(right_obj)

		return left_objects, right_objects

	def before_save_instance(self, instance, row, **kwargs):
		raw_pairs = row.get("items", "")
		if not raw_pairs:
			raw_pairs = ""
		pairs = [v.strip() for v in raw_pairs.split(self.ITEM_SEPARATOR) if v.strip()]

		left_objects, right_objects = self.extract_pairs(pairs)

		instance.content = {
			"columns": [
				{
					"title": row.get("left_title", ""),
					"items": left_objects,
				},
				{
					"title": row.get("right_title", ""),
					"items": right_objects,
				},
			],
		}

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def _serialize_item(self, item: dict) -> str:
		"""Convert a single item dict back to its string representation."""
		if "asset_id" in item:
			return f"{self.ASSET_PREFIX}{item['asset_id']}"
		return item.get("text", "")

	def get_export_row(self, instance):
		content = instance.content or {}
		columns = content.get("columns", []) if isinstance(content, dict) else content
		left = columns[0] if len(columns) > 0 else {}
		right = columns[1] if len(columns) > 1 else {}

		left_items = left.get("items", [])
		right_items = right.get("items", [])

		# Build a mapping from left item id → right item (via matched_id)
		right_by_matched = {item.get("matched_id"): item for item in right_items}

		pairs = []
		for left_item in left_items:
			left_str = self._serialize_item(left_item)
			right_item = right_by_matched.get(left_item.get("id"), {})
			right_str = self._serialize_item(right_item)
			pairs.append(f"{left_str}{self.ITEM_PAIR_SEPARATOR}{right_str}")

		return [
			instance.id,
			instance.category_id,
			left.get("title", ""),
			right.get("title", ""),
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

	class Meta(AbstractQuizResource.Meta):
		model = FillInTheBlank

	def before_save_instance(self, instance, row, **kwargs):
		texts = []
		i = 1
		while f"text_{i}" in row and row[f"text_{i}"]:
			texts.append({"text": row[f"text_{i}"]})
			i += 1

		instance.content = {
			"show_answers_as_choices": _parse_bool(
				row.get("show_answers_as_choices", False)
			),
			"prompt_asset_id": _import_image_column(
				row.get("prompt_image"), title="Prompt"
			),
			"texts": texts,
		}

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		content = instance.content or {}
		texts = content.get("texts", [])

		row = [
			instance.id,
			instance.category_id,
			"true" if content.get("show_answers_as_choices") else "false",
			content.get("prompt_asset_id", "") or "",
		]

		for i in range(self.MAX_EXPORT_TEXTS):
			if i < len(texts):
				row.append(texts[i].get("text", ""))
			else:
				row.append("")

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

	class Meta(AbstractQuizResource.Meta):
		model = OpenEnded

	def before_save_instance(self, instance, row, **kwargs):
		raw_texts = row.get("texts", "")
		texts = []
		for v in raw_texts.split(","):
			v = v.strip()
			if not v:
				continue
			# Support pipe-separated alternatives: "word1|word2"
			alternatives = [a.strip() for a in v.split("|") if a.strip()]
			if alternatives:
				texts.append({"alternatives": alternatives})
		min_correct_answers = row.get("min_correct_answers")
		if not min_correct_answers:
			min_correct_answers = len(texts)

		instance.content = {
			"prompt_text": row.get("prompt_text") or "",
			"prompt_asset_id": _import_image_column(
				row.get("prompt_image"), title="Prompt"
			),
			"texts": texts,
			"min_correct_answers": int(min_correct_answers),
		}

	# ------------------------------------------------------------------
	# Export
	# ------------------------------------------------------------------

	def get_export_row(self, instance):
		content = instance.content or {}
		texts = content.get("texts", [])

		# Serialize texts back to comma-separated, with pipe for alternatives
		text_parts = []
		for t in texts:
			if isinstance(t, dict):
				alternatives = t.get("alternatives", [])
				if alternatives:
					text_parts.append("|".join(alternatives))
				else:
					# Fallback for old format with "text" key
					text_parts.append(t.get("text", ""))
			else:
				text_parts.append(str(t))

		return [
			instance.id,
			instance.category_id,
			content.get("prompt_text", ""),
			content.get("prompt_asset_id", "") or "",
			", ".join(text_parts),
			content.get("min_correct_answers", ""),
		]
