from .constants import QuizType


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
        "oneOf": [
            # LEFT
            {
                "type": "object",
                "required": ["title", "items"],
                "properties": {
                    "title": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "text"],
                            "properties": {
                                "id": {"type": "integer"},
                                "text": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    },
                },
                "additionalProperties": False,
            },
            # RIGHT
            {
                "type": "object",
                "required": ["title", "items"],
                "properties": {
                    "title": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["matched_id", "text"],
                            "properties": {
                                "matched_id": {"type": "integer"},
                                "text": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    },
                },
                "additionalProperties": False,
            },
        ],
    },
}

FILL_IN_THE_BLANK_QUIZ_SCHEMA = {
    "type": "object",
    "required": ["show_answers_as_choices", "content"],
    "properties": {
        "prompt_asset_id": {"type": "integer", "title": "Prompt asset id"},
        "show_answers_as_choices": {
            "type": "boolean",
            "title": "Show answers as choices",
            "default": False,
        },
        "content": {
            "oneOf": [
                # texts + separate answers list
                {
                    "type": "object",
                    "properties": {
                        "texts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "text": {"type": "string"},  # use placeholder "__"
                                },
                                "required": ["id", "text"],
                            },
                        },
                        "answers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "matched_id": {
                                        "oneOf": [
                                            {"type": "integer"},
                                            {"type": "null"},
                                        ]
                                    },
                                    "text": {"type": "string"},
                                },
                                "required": ["matched_id", "text"],
                            },
                        },
                    },
                    "required": ["texts", "answers"],
                    "additionalProperties": False,
                },
                # answers nested under each text item
                {
                    "type": "object",
                    "properties": {
                        "texts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "text": {"type": "string"},  # use placeholder "__"
                                    "answers": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "matched_id": {
                                                    "oneOf": [
                                                        {"type": "integer"},
                                                        {"type": "null"},
                                                    ]
                                                },
                                                "text": {"type": "string"},
                                            },
                                            "required": ["matched_id", "text"],
                                        },
                                    },
                                },
                                "required": ["id", "text"],
                            },
                        }
                    },
                    "required": ["texts"],
                    "additionalProperties": False,
                },
            ]
        },
    },
    "additionalProperties": False,
}


def get_quiz_schema(instance):
    quiz_type = instance.type

    if quiz_type == QuizType.FILL_IN_THE_BLANK:
        return FILL_IN_THE_BLANK_QUIZ_SCHEMA
    if quiz_type == QuizType.DRAG_AND_DROP:
        return DRAG_AND_DROP_QUIZ_SCHEMA
    if quiz_type == QuizType.MATCHING:
        return MATCHING_QUIZ_SCHEMA

    return TRUE_FALSE_MULTIPLE_CHOICE_QUIZ_SCHEMA
