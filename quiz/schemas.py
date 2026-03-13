TRUE_FALSE_MULTIPLE_CHOICE_QUIZ_SCHEMA = {
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

DRAG_AND_DROP_QUIZ_SCHEMA = {
	"type": "array",
	"minItems": 2,
	"maxItems": 2,
	"items": {
		"type": "object",
		"required": ["title", "values"],
		"properties": {
			"title": {"type": "string", "title": "Title"},
			"values": {"type": "array", "title": "Values", "items": {"type": "string"}},
		},
		"additionalProperties": False,
	},
}

MATCHING_QUIZ_SCHEMA = {
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

FILL_IN_THE_BLANK_QUIZ_SCHEMA = {
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
