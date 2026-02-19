{
  "Question": {
    "id": "string",
    "category": "string",
    "type": "multipleChoice | shortText | listInput | trueFalseGroup | matching | categorization | mapPoints",

    "multipleChoice": {
      "question": "string",
      "options": {
        "A": "string",
        "B": "string",
        "C": "string",
        "D": "string"
      },
      "correctAnswer": "string"
    },

    "shortText": {
      "question": "string",
      "prompt": "string (optional)",
      "multipleBlanks": true,
      "correctAnswer": ["string"]
    },

    "listInput": {
      "question": "string",
      "minItems": "number",
      "maxItems": "number",
      "correctAnswer": ["string"]
    },

    "trueFalseGroup": {
      "question": "string",
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
      "question": "string",
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

    "categorization": {
      "question": "string",
      "categories": [
        { "key": "string", "label": "string" }
      ],
      "items": ["string"],
      "correctAnswer": {
        "category.key": ["string"]
      }
    },

    "mapPoints": {
      "question": "string",
      "rules": {
        "map": true,
        "maxPoints": "number (optional)",
        "minItems": "number (optional)",
        "maxItems": "number (optional)",
        "expectsSubset": "boolean (optional)",
        "tolerancePct": "number",
        "tolerance": "boolean (optional)"
      },
      "canonicalAnswer": {
        "type": "points",
        "points": [
          {
            "label": "string",
            "aliases": ["string (optional)"],
            "x": "number (0-100)",
            "y": "number (0-100)"
          }
        ]
      },
      "answerBullets": ["string (optional)"],
      "keywords": ["string (optional)"]
    }
  }
}
