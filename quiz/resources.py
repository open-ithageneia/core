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
			elif suffix in _IMAGE_EXTENSIONS:
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


def _create_asset_from_bytes(image_bytes: bytes, filename: str, title: str = "") -> int:
	"""Persist raw image bytes as a new QuizAsset and return its pk."""
	suffix = PurePosixPath(filename).suffix or ".png"
	dest_name = f"{uuid.uuid4()}{suffix}"
	asset = QuizAsset.objects.create(
		title=title,
		image=ContentFile(image_bytes, name=dest_name),
	)
	return asset.pk


def _is_asset_id(value) -> bool:
	"""Return True when *value* looks like an integer asset ID."""
	try:
		int_val = int(value)
		return int_val > 0
	except (TypeError, ValueError):
		return False


def _import_image_column(value, title: str = "") -> int | None:
	"""Resolve an image column value to a ``QuizAsset`` pk.

	The value can be one of:

	* **blank / None** → returns ``None``.
	* **integer (asset ID)** → validated against ``QuizAsset`` and returned
	  directly.  This path does *not* require a ZIP upload.
	* **filename string** → looked up in the thread-local image store
	  (populated from a ZIP upload) and persisted as a new ``QuizAsset``.
	"""
	if _is_blank(value):
		return None

	raw = str(value).strip()

	# --- path 1: existing asset ID (numeric) ---
	if _is_asset_id(raw):
		asset_pk = int(raw)
		if not QuizAsset.objects.filter(pk=asset_pk).exists():
			raise ValueError(
				f"QuizAsset with ID {asset_pk} does not exist. "
				f"Provide a valid asset ID or an image filename inside a ZIP."
			)
		return asset_pk

	# --- path 2: filename from ZIP image store ---
	filename = raw
	image_bytes = _get_image_bytes(filename)

	if image_bytes is None:
		raise ValueError(
			f"Image '{filename}' not found in the uploaded ZIP archive. "
			f"Make sure the file exists in the images/ folder inside the ZIP."
		)

	return _create_asset_from_bytes(image_bytes, filename, title=title)


class AbstractQuizResource(resources.ModelResource):
	"""Base resource for all quiz types.

	Provides:
	- An ``exam_session`` constructor kwarg (from the import form dropdown).
	  Since ``exam_sessions`` is an M2M field it is set *after* the
	  instance is saved via ``after_save_instance``.
	- Common Meta defaults (``fields``, ``skip_unchanged``).

	Subclasses must set ``Meta.model`` and may extend ``Meta.fields``.
	"""

	def __init__(self, *, exam_session=None, **kwargs):
		self.exam_session = exam_session
		super().__init__(**kwargs)

	def after_save_instance(self, instance, row, **kwargs):
		super().after_save_instance(instance, row, **kwargs)
		if self.exam_session is not None:
			instance.exam_sessions.add(self.exam_session)

	class Meta:
		fields = ("id", "category", "content")
		skip_unchanged = False
		abstract = True


class StatementResource(AbstractQuizResource):
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
			"choices": choices,
		}


class DragAndDropResource(AbstractQuizResource):
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


class MatchingResource(AbstractQuizResource):
	class Meta(AbstractQuizResource.Meta):
		model = Matching

	def before_save_instance(self, instance, row, **kwargs):
		raw_items = row.get("items", "")
		pairs = [v.strip() for v in raw_items.split(",") if v.strip()]

		left_objects = []
		right_objects = []

		for idx, pair in enumerate(pairs, start=1):
			if "/" not in pair:
				raise ValueError(
					f"Item '{pair}' is not in the expected 'left/right' format."
				)
			left_text, right_text = pair.split("/", maxsplit=1)

			left_objects.append(
				{
					"id": idx,
					"text": left_text.strip(),
					"matched_id": idx + len(pairs),
				}
			)
			right_objects.append(
				{
					"id": idx + len(pairs),
					"text": right_text.strip(),
					"matched_id": idx,
				}
			)

		instance.content = [
			{
				"title": row.get("left_title", ""),
				"items": left_objects,
			},
			{
				"title": row.get("right_title", ""),
				"items": right_objects,
			},
		]


class FillInTheBlankResource(AbstractQuizResource):
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


class OpenEndedResource(AbstractQuizResource):
	class Meta(AbstractQuizResource.Meta):
		model = OpenEnded
		fields = (
			"id",
			"type",
			"category",
			"content",
		)

	def before_save_instance(self, instance, row, **kwargs):
		raw_texts = row.get("texts", "")
		texts = [v.strip() for v in raw_texts.split(",") if v.strip()]
		min_correct_answers = row.get("min_correct_answers")
		if not min_correct_answers:
			min_correct_answers = len(texts)

		instance.content = {
			"prompt_text": row.get("prompt_text") or "",
			"prompt_asset_id": _import_image_column(
				row.get("prompt_image"), title="Prompt"
			),
			"texts": texts,
			"min_correct_answers": min_correct_answers,
		}
