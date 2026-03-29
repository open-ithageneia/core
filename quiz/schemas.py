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

	def to_dict(self):
		from quiz.services import AssetService

		return {
			"is_correct": self.is_correct,
			"text": self.text,
			"asset_url": AssetService.resolve_asset_url(self.asset_id),
		}

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

	def to_dict(self):
		from quiz.services import AssetService

		return {
			"choices": [c.to_dict() for c in self.choices],
			"prompt_text": self.prompt_text,
			"prompt_asset_url": AssetService.resolve_asset_url(self.prompt_asset_id),
		}

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

	def to_dict(self):
		return {
			"title": self.title,
			"values": self.values
		}

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

	def to_dict(self):
		return [c.to_dict() for c in self.columns]

	@classmethod
	def from_json(cls, data: list):
		if not isinstance(data, list) or len(data) != 2:
			raise ValidationError(
				"Drag-and-drop content must be a list of exactly 2 columns."
			)
		return cls(columns=[DragDropColumn.from_json(col) for col in data])


@dataclass
class MatchItem:
	id: int
	matched_id: int
	text: str | None = None
	asset_id: str | None = None

	def to_dict(self):
		from quiz.services import AssetService

		return {
			"text": self.text,
			"asset_url": AssetService.resolve_asset_url(self.asset_id),
			"id": self.id,
			"matched_id": self.matched_id
		}

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			id=data.get("id"),
			asset_id=data.get("asset_id"),
			matched_id=data.get("matched_id"),
			text=_require(data, "text", "MatchItem"),
		)


@dataclass
class MatchingColumn:
	title: str
	items: list[MatchItem]

	def to_dict(self):
		return {
			"title": self.title, "items": [i.to_dict() for i in self.items]
		}

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
						"required": ["id", "matched_id"],
						"properties": {
							"id": {"type": "integer"},
							"matched_id": {"type": "integer"},
							"text": {"type": "string"},
							"asset_id": {
								"type": "integer",
								"title": "Image asset ID",
							},
						},
						"additionalProperties": False,
					},
				},
			},
		},
	}

	columns: list[MatchingColumn]

	def to_dict(self):
		return [c.to_dict() for c in self.columns]

	@classmethod
	def from_json(cls, data: list):
		if not isinstance(data, list) or len(data) != 2:
			raise ValidationError(
				"Matching content must be a list of exactly 2 columns."
			)
		return cls(columns=[MatchingColumn.from_json(col) for col in data])


@dataclass
class FillBlankChoice:
	text: str
	is_correct: bool

	def to_dict(self):
		return {
			"text": self.text,
			"is_correct": self.is_correct
		}


@dataclass
class FillBlankTextPart:
	text: str
	is_blank: bool
	choices: list[FillBlankChoice] = field(default_factory=list)

	def to_dict(self):
		d = {"text": None if self.is_blank else self.text, "is_blank": self.is_blank}
		if self.is_blank:
			d["choices"] = [c.to_dict() for c in self.choices]
		return d


@dataclass
class FillBlankText:
	BLANK_PATTERN = re.compile(r"<(.+?)>")
	CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")

	text_parts: list[FillBlankTextPart]
	has_multiple_choices: bool

	def to_dict(self):
		return {
			"parts": [p.to_dict() for p in self.text_parts]
		}

	@classmethod
	def from_json(cls, data: dict):
		text = _require(data, "text", "FillBlankText")
		text_parts = []

		raw_blanks = cls.BLANK_PATTERN.findall(text)

		if not raw_blanks:
			raise ValidationError(
				f"{text}: no blanks found. Use <({{{{answer}}}}*)> syntax."
			)

		has_multiple_choices = False
		for blank in raw_blanks:
			choices = cls.CHOICE_PATTERN.findall(blank)

			if not choices:
				raise ValidationError(
					f"{blank}: invalid blank — must contain at least one {{{{choice}}}}."
				)

			if len(choices) > 1:
				has_multiple_choices = True

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
				parsed_choices = [
					FillBlankChoice(text=c, is_correct=marker == "*")
					for c, marker in cls.CHOICE_PATTERN.findall(part)
				]
				text_parts.append(
					FillBlankTextPart(text=part, is_blank=True, choices=parsed_choices)
				)

		return cls(text_parts=text_parts, has_multiple_choices=has_multiple_choices)


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

	has_multiple_choices: bool
	show_answers_as_choices: bool
	texts: list[FillBlankText]
	prompt_asset_id: int | None = None

	def to_dict(self):
		from quiz.services import AssetService

		return {
			"show_answers_as_choices": self.show_answers_as_choices,
			"has_multiple_choices": self.has_multiple_choices,
			"texts": [t.to_dict() for t in self.texts],
			"prompt_asset_url": AssetService.resolve_asset_url(self.prompt_asset_id),
		}

	@classmethod
	def from_json(cls, data: dict):
		texts = [FillBlankText.from_json(t) for t in data.get("texts", [])]
		has_multiple_choices = any(t.has_multiple_choices for t in texts)
		return cls(
			show_answers_as_choices=data.get("show_answers_as_choices", False),
			prompt_asset_id=data.get("prompt_asset_id"),
			texts=texts,
			has_multiple_choices=has_multiple_choices,
		)


@dataclass
class OpenEndedContent:
	OPEN_ENDED_CONTENT_SCHEMA = {
		"type": "object",
		"required": ["prompt_text", "min_correct_answers", "texts"],
		"properties": {
			"prompt_text": {"type": "string", "title": "Question"},
			"prompt_asset_id": {"type": "integer", "title": "Prompt asset id"},
			"min_correct_answers": {
				"type": "integer",
				"title": "Minimum correct answers",
			},
			"texts": {
				"type": "array",
				"items": {
					"type": "object",
					"required": ["text"],
					"properties": {"text": {"type": "string"}},
				},
				"additionalProperties": False,
			},
		},
		"additionalProperties": False,
	}

	min_correct_answers: int
	texts: list[str]
	prompt_text: str | None = None
	prompt_asset_id: int | None = None

	def to_dict(self):
		from quiz.services import AssetService

		return {
			"min_min_correct_answers": self.min_correct_answers,
			"prompt_text": self.prompt_text,
			"texts": self.texts,
			"prompt_asset_url": AssetService.resolve_asset_url(self.prompt_asset_id),
		}

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			prompt_asset_id=data.get("prompt_asset_id"),
			prompt_text=data.get("prompt_text"),
			texts=data.get("texts"),
			min_correct_answers=data.get("min_correct_answers"),
		)
