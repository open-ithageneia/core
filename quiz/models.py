from django.db import models
from django_jsonform.models.fields import JSONField

from open_ithageneia.models import TimeStampedModel


# class TrueFalseQuiz(TimeStampedModel):
#     instructions = models.TextField(default="") # add default text
#     context = models.TextField(default="")

# class TrueFalseStatement(TimeStampedModel):
#     quiz = models.ForeignKey("TrueFalseQuiz", on_delete=models.CASCADE, related_name="statements")
#     text = models.TextField(blank=True, default="")
#     image = models.ImageField(upload_to="quiz_statements/", blank=True, null=True)
#     is_correct = models.BooleanField()

# The above is best if you will:

# edit often in admin

# track user answers

# import/export data reliably

# filter statements / reuse them

# SQLite doesn't have a real "JSON column type" like Postgres, but it does support JSON via:

# SQLite's JSON1 functions (very common in modern SQLite builds)

# And Django's models.JSONField works on SQLite by storing JSON as TEXT and validating/serializing in Python.

# So: Yes, you can use Django JSONField with SQLite, just expect limited querying power compared to Postgres.

# Downsides of JSON approach (especially on SQLite):

# Editing in admin is annoying unless you build a custom JSON editor UI

# Harder to validate per-item

# Harder to track per-statement answers historically

# Querying/filtering individual items is limited

# Import-export becomes more brittle

'''
What we want:
1) Show JSON field properly in admin
2) Validate JSON field structure according to quiz rules
3) Fixtures
4) Check django-import-export
5) Τι κάνουμε με τις εικόνες?
6) Categories?
'''

# Check https://docs.djangoproject.com/en/6.0/ref/databases/#enabling-json1-extension-on-sqlite
# The JSON1 extension is enabled by default on SQLite 3.38+. -> 3.51.1 OK

# There is also this: https://pypi.org/project/django-json-widget/


TRUE_FALSE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό της κάθε πρότασης, σημειώνοντας Σ, αν η πρόταση που σας δίνεται παρακάτω είναι σωστή, ή Λ, αν είναι λάθος."
# MULTIPLE_CHOICE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και δίπλα τη σωστή απάντηση, σημειώνοντας το αντίστοιχο γράμμα (Α ή Β ή Γ ή Δ)."


class TrueFalseQuiz(TimeStampedModel):
    STATEMENTS_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "statement": { "type": "string", "title": "Statement" },
                "is_true": { "type": "boolean", "title": "Correct?", "default": False },
            },
            "required": ["statement", "is_true"],
        },
        "default": [],
        # "maxItems": 4,
    }

    instructions = models.TextField(blank=True, default=TRUE_FALSE_BASE_INSTRUCTION)
    context = models.TextField(blank=True, default="")
    statements = JSONField(blank=True, default=list, schema=STATEMENTS_SCHEMA)
    # statements = models.JSONField(blank=True, default=list)


# class MutlipleChoice(TimeStampedModel):
#     instructions = models.TextField(blank=True, default=MULTIPLE_CHOICE_BASE_INSTRUCTION)
#     context = models.TextField(blank=True, default="")
#     statements = models.JSONField(blank=True, default=list)