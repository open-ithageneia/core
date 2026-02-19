{
  "Question": {
    "id": "string",
    "category": "string",
    "active": true,
    "type": "multipleChoice | multiSelect | matching | wordMatching | shortText | listInput | trueFalseGroup | categorization | mapPoints | openText",

    "common": {
      "question": "string",
      "prompt": "string (optional)",
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
      "options": [
        { "key": "string", "label": "string" }
      ],
      "correctAnswer": ["string"],
      "maxSelections": 2
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

    "wordMatching": {
      "pairs": [
        { "left": "string", "right": "string" }
      ],
      "correctAnswer": {
        "leftWord": "rightWord"
      }
    },

    "shortText": {
      "multipleBlanks": true,
      "correctAnswer": ["string"]
    },

    "listInput": {
      "minItems": 1,
      "maxItems": 4,
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

    "categorization": {
      "categories": [
        { "key": "string", "label": "string" }
      ],
      "items": [
        { "key": "string", "label": "string" }
      ],
      "correctAnswer": {
        "categoryKey": ["itemKey"]
      }
    },

    "mapPoints": {
      "rules": {
        "maxPoints": 4,
        "tolerancePct": 3.5
      },
      "canonicalAnswer": {
        "points": [
          {
            "x": 0,
            "y": 0,
            "label": "string"
          }
        ]
      }
    },

    "openText": {
      "correctAnswer": "string",
      "maxWords": 200
    }
  }
}
