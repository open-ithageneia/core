{
  "Question": {
    "id": "string",
    "category": "string",
    "active": true,
    "type": "multipleChoice | multiSelect | shortText | trueFalseGroup | matching | openText",

    "common": {
      "question": "string",
      "prompt": "string (optional)"
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
      "correctAnswer": ["string"],
      "maxSelections": 2
    },

    "shortText": {
      "multipleBlanks": true,
      "prompt": "string (optional)",
      "correctAnswer": ["string"]
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

    "openText": {
      "maxWords": 50,
      "correctAnswer": "string"
    }
  }
}
