{
  "Question": {
    "id": "string",
    "category": "string",
    "active": true,
    "type": "multipleChoice | matching | trueFalseGroup | wordMatching | multiSelect",

    "common": {
      "question": "string",
      "media": [
        {
          "id": "string",
          "type": "image | video | audio",
          "src": "string",
          "alt": "string"
        }
      ]
    },

    "multipleChoice": {
      "options": {
        "A": "string",
        "B": "string",
        "C": "string",
        "D": "string"
      },
      "correctAnswer": "string"
    },

    "multiSelect": {
      "options": ["string"],
      "minSelections": "number",
      "maxSelections": "number",
      "correctAnswer": ["string"]
    },

    "matching": {
      "columnAHeader": "string",
      "columnBHeader": "string",
      "columnA": [
        { "key": "string", "label": "string" }
      ],
      "columnB": [
        { "key": "string", "label": "string" }
      ],
      "correctAnswer": {
        "columnA.key": "columnB.key"
      }
    },

    "trueFalseGroup": {
      "statements": [
        {
          "key": "string",
          "text": "string"
        }
      ],
      "correctAnswer": {
        "statement.key": "T | F"
      }
    },

    "wordMatching": {
      "wordBank": {
        "optionKey": "string"
      },
      "textTemplate": "string (με placeholders π.χ. 1. __ )",
      "correctAnswer": {
        "blankNumber": "wordBankKey"
      },
      "hasExtraOption": "boolean"
    }
  }
}
