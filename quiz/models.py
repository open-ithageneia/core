from django.db import models
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


TRUE_FALSE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό της κάθε πρότασης, σημειώνοντας Σ, αν η πρόταση που σας δίνεται παρακάτω είναι σωστή, ή Λ, αν είναι λάθος."


class TrueFalseQuiz(TimeStampedModel):
    instructions = models.TextField(blank=True, default=TRUE_FALSE_BASE_INSTRUCTION)
    context = models.TextField(blank=True, default="")
    items = models.JSONField(default=list)


class MutlipleChoice(TimeStampedModel):
    pass