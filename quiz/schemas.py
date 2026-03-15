import re
from django.core.exceptions import ValidationError
from dataclasses import dataclass, field


def _require(data: dict, key: str, context: str = ""):
	"""Return data[key] or raise ValidationError (not KeyError)."""
	try:
		return data[key]
	except KeyError:
		label = f" in {context}" if context else ""
		raise ValidationError(f"Missing required field '{key}'{label}.")


@dataclass
class StatementChoice:
	text: str | None = None
	asset_id: int | None = None
	is_correct: bool = False

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			text=data.get("text"),
			asset_id=data.get("asset_id"),
			is_correct=data.get("is_correct", False),
		)


@dataclass
class StatementChoiceContent:
	STATEMENT_CONTENT_SCHEMA = {
		"type": "object",
		"properties": {
			"prompt_text": {"type": "string", "title": "Question"},
			"prompt_asset_id": {"type": "integer", "title": "Question image asset ID"},
			"choices": {
				"type": "array",
				"title": "Choices",
				"items": {
					"type": "object",
					"properties": {
						"text": {"type": "string", "title": "Choice text"},
						"asset_id": {
							"type": "integer",
							"title": "Choice image asset ID",
						},
						"is_correct": {
							"type": "boolean",
							"title": "Correct?",
							"default": False,
						},
					},
					"required": ["is_correct"],
				},
				"default": [],
			},
		},
		"required": ["choices"],
	}

	choices: list[StatementChoice] = field(default_factory=list)
	prompt_text: str | None = None
	prompt_asset_id: int | None = None

	@classmethod
	def from_json(cls, data: dict):
		raw_choices = _require(data, "choices", "StatementChoiceContent")
		choices = [StatementChoice.from_json(c) for c in raw_choices]

		return cls(
			prompt_text=data.get("prompt_text"),
			prompt_asset_id=data.get("prompt_asset_id"),
			choices=choices,
		)


@dataclass
class DragDropColumn:
	title: str
	values: list[str]

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			title=_require(data, "title", "DragDropColumn"),
			values=data.get("values", []),
		)


@dataclass
class DragAndDropContent:
	DRAG_AND_DROP_CONTENT_SCHEMA = {
		"type": "array",
		"minItems": 2,
		"maxItems": 2,
		"items": {
			"type": "object",
			"required": ["title", "values"],
			"properties": {
				"title": {"type": "string", "title": "Title"},
				"values": {
					"type": "array",
					"title": "Values",
					"items": {"type": "string"},
				},
			},
			"additionalProperties": False,
		},
	}

	columns: list[DragDropColumn]

	@classmethod
	def from_json(cls, data: list):
		if not isinstance(data, list) or len(data) != 2:
			raise ValidationError(
				"Drag-and-drop content must be a list of exactly 2 columns."
			)
		return cls(columns=[DragDropColumn.from_json(col) for col in data])


@dataclass
class MatchItem:
	text: str
	id: int | None = None
	matched_id: int | None = None

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			id=data.get("id"),
			matched_id=data.get("matched_id"),
			text=_require(data, "text", "MatchItem"),
		)


@dataclass
class MatchingColumn:
	title: str
	items: list[MatchItem]

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			title=_require(data, "title", "MatchingColumn"),
			items=[MatchItem.from_json(i) for i in data.get("items", [])],
		)


@dataclass
class MatchingContent:
	MATCHING_CONTENT_SCHEMA = {
		"type": "array",
		"minItems": 2,
		"maxItems": 2,
		"items": {
			"type": "object",
			"required": ["title", "items"],
			"properties": {
				"title": {"type": "string"},
				"items": {
					"type": "array",
					"items": {
						"type": "object",
						"required": ["text"],
						"properties": {
							"id": {"type": "integer"},
							"matched_id": {"type": "integer"},
							"text": {"type": "string"},
						},
						"additionalProperties": False,
					},
				},
			},
		},
	}

	columns: list[MatchingColumn]

	@classmethod
	def from_json(cls, data: list):
		if not isinstance(data, list) or len(data) != 2:
			raise ValidationError(
				"Matching content must be a list of exactly 2 columns."
			)
		return cls(columns=[MatchingColumn.from_json(col) for col in data])


@dataclass
class FillBlankTextPart:
	text: str
	is_blank: bool


@dataclass
class FillBlankText:
	BLANK_PATTERN = re.compile(r"<(.+?)>")
	CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")

	text_parts: list[FillBlankTextPart]

	@classmethod
	def from_json(cls, data: dict):
		text = _require(data, "text", "FillBlankText")
		text_parts = []

		raw_blanks = cls.BLANK_PATTERN.findall(text)

		if not raw_blanks:
			raise ValidationError(
				f"{text}: no blanks found. Use <({{{{answer}}}}*)> syntax."
			)

		for blank in raw_blanks:
			choices = cls.CHOICE_PATTERN.findall(blank)

			if not choices:
				raise ValidationError(
					f"{blank}: invalid blank — must contain at least one {{{{choice}}}}."
				)

			for choice_text, marker in choices:
				if not choice_text.strip():
					raise ValidationError(
						f"{choice_text}: blank contains an empty choice."
					)

			correct = [c for c, marker in choices if marker == "*"]

			if len(correct) == 0:
				raise ValidationError(
					f"blank '<({blank})>' has no correct answer. Mark exactly one with *."
				)

			if len(correct) > 1:
				raise ValidationError(
					f"blank '<({blank})>' has {len(correct)} correct answers "
					f"({', '.join(correct)}). Mark exactly one with *."
				)

		# build text_parts
		parts = cls.BLANK_PATTERN.split(text)

		for i, part in enumerate(parts):
			if i % 2 == 0:
				if part:
					text_parts.append(FillBlankTextPart(text=part, is_blank=False))
			else:
				text_parts.append(FillBlankTextPart(text=part, is_blank=True))

		return cls(text_parts=text_parts)


@dataclass
class FillInTheBlankContent:
	FILL_IN_THE_BLANK_CONTENT_SCHEMA = {
		"type": "object",
		"required": ["show_answers_as_choices", "texts"],
		"properties": {
			"prompt_asset_id": {"type": "integer", "title": "Prompt asset id"},
			"show_answers_as_choices": {
				"type": "boolean",
				"title": "Show answers as choices",
				"default": False,
			},
			"texts": {
				"type": "array",
				"items": {
					"type": "object",
					"required": ["text"],
					"properties": {
						"text": {
							"type": "string",
							"title": "Text",
							"description": 'Use <{{answer1}}, {{answer2}}> for blanks. E.g. "The <{{13th}}, {{Thirteenth}})> Amendment..."',
						},
					},
					"additionalProperties": False,
				},
			},
		},
		"additionalProperties": False,
	}

	show_answers_as_choices: bool
	texts: list[FillBlankText]
	prompt_asset_id: int | None = None

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			show_answers_as_choices=data.get("show_answers_as_choices", False),
			prompt_asset_id=data.get("prompt_asset_id"),
			texts=[FillBlankText.from_json(t) for t in data.get("texts", [])],
		)
