from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StatementChoice:
	text: Optional[str] = None
	asset_id: Optional[int] = None
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

	choices: List[StatementChoice] = field(default_factory=list)
	prompt_text: Optional[str] = None
	prompt_asset_id: Optional[int] = None

	@classmethod
	def from_json(cls, data: dict):
		choices = [StatementChoice.from_json(c) for c in data.get("choices", [])]

		return cls(
			prompt_text=data.get("prompt_text"),
			prompt_asset_id=data.get("prompt_asset_id"),
			choices=choices,
		)


@dataclass
class DragDropColumn:
	title: str
	values: List[str]

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			title=data["title"],
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

	columns: List[DragDropColumn]

	@classmethod
	def from_json(cls, data: list):
		return cls(columns=[DragDropColumn.from_json(col) for col in data])


@dataclass
class MatchItem:
	text: str
	id: Optional[int] = None
	matched_id: Optional[int] = None

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			id=data.get("id"),
			matched_id=data.get("matched_id"),
			text=data["text"],
		)


@dataclass
class MatchingColumn:
	title: str
	items: List[MatchItem]

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			title=data["title"],
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

	columns: List[MatchingColumn]

	@classmethod
	def from_json(cls, data: list):
		return cls(columns=[MatchingColumn.from_json(col) for col in data])


@dataclass
class FillBlankText:
	text: str

	@classmethod
	def from_json(cls, data: dict):
		return cls(text=data["text"])


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
	texts: List[FillBlankText]
	prompt_asset_id: Optional[int] = None

	@classmethod
	def from_json(cls, data: dict):
		return cls(
			show_answers_as_choices=data.get("show_answers_as_choices", False),
			prompt_asset_id=data.get("prompt_asset_id"),
			texts=[FillBlankText.from_json(t) for t in data.get("texts", [])],
		)
