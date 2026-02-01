from django.db import models
from django.dispatch import receiver
from django_jsonform.models.fields import JSONField

from open_ithageneia.models import TimeStampedModel, ActivatableModel


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
4) Check django-import-export
8) Semester? (May, November each year)
9) Pillow?
10) Admin
'''

# Check https://docs.djangoproject.com/en/6.0/ref/databases/#enabling-json1-extension-on-sqlite
# The JSON1 extension is enabled by default on SQLite 3.38+. -> 3.51.1 OK

# There is also this: https://pypi.org/project/django-json-widget/


TRUE_FALSE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό της κάθε πρότασης, σημειώνοντας Σ, αν η πρόταση που σας δίνεται παρακάτω είναι σωστή, ή Λ, αν είναι λάθος."
# MULTIPLE_CHOICE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και δίπλα τη σωστή απάντηση, σημειώνοντας το αντίστοιχο γράμμα (Α ή Β ή Γ ή Δ)."


def get_quiz_asset_upload_to(instance, filename):
    return f"quizzes/assets/{instance.id}/{filename}"


class QuizAsset(TimeStampedModel):
    title = models.CharField(max_length=255, blank=True, default="")
    image = models.ImageField(upload_to=get_quiz_asset_upload_to)


# We use signals because get_quiz_asset_upload_to function will fail
# since instance.id does not exist before creation


@receiver(models.signals.pre_save, sender=QuizAsset)
def quiz_asset_instance_pre_save(sender, instance, **kwargs):
    """QuizAsset model instance pre save"""

    if not instance.pk and instance.image:
        # quiz instance not created and user uploads a image
        instance._tmp_image_on_create = instance.image
        instance.image = None


@receiver(models.signals.post_save, sender=QuizAsset)
def quiz_asset_instance_post_save(sender, instance, created, **kwargs):
    """QuizAsset model instance post save"""

    if created and hasattr(instance, "_tmp_image_on_create"):
        instance.image = getattr(instance, "_tmp_image_on_create")

        instance.save(update_fields=["image"])


def get_true_false_quiz_upload_to(instance, filename):
    return f"quizzes/tf/{instance.id}/{filename}"


class QuizType(models.TextChoices):
    TRUE_FALSE = "TRUE_FALSE", "True/False"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Mutliple Choice"


class QuizCategory(models.TextChoices):
    GEORGRAPHY = "GEORGRAPHY", "Geography"
    CIVICS = "CIVICS", "Civics"
    HISTORY = "HISTORY", "History"
    CULTURE = "CULTURE", "Culture"



class QuestionQuiz(TimeStampedModel, ActivatableModel):
    '''
    Currently works for True/False and Multiple Choice Quizzes
    '''

    CONTENT_SCHEMA = {
        "type": "object",
        "properties": {
            "prompt_text": { "type": "string", "title": "Question" },
            "prompt_asset_id": { "type": "integer", "title": "Question image asset ID" },
            "choices": {
                "type": "array",
                "title": "Choices",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": { "type": "string", "title": "Choice text" },
                        "asset_id": { "type": "integer", "title": "Choice image asset ID" },
                        "is_correct": { "type": "boolean", "title": "Correct?", "default": False},
                    },
                    "required": ["is_correct"],
                },
                "default": [],
            },
        },
        "required": ["choices"],
    }

    type = models.CharField(
        max_length=15,
        choices=QuizType,
        default=QuizType.TRUE_FALSE,
    )
    category = models.CharField(
        max_length=10,
        choices=QuizCategory,
        default=QuizCategory.GEORGRAPHY,
    )
    instructions = models.TextField(blank=True, default=TRUE_FALSE_BASE_INSTRUCTION) # Choices also?
    content = JSONField(blank=True, default=lambda: {"choices": []}, schema=CONTENT_SCHEMA)


# class TrueFalseQuiz(TimeStampedModel):
#     STATEMENTS_SCHEMA = {
#         "type": "array",
#         "default": [],
#         "items": {
#             "type": "object",
#             "properties": {
#                 "statement": { "type": "string", "title": "Statement" },
#                 # "image": {"type": "string", "title": "Image URL/path" },
#                 "asset_id": {"type": "integer", "title": "Image asset ID", "required": False},
#                 "is_correct": { "type": "boolean", "title": "Correct?", "default": False },
#             },
#             "required": ["is_correct"],
#         },
#         # "maxItems": 4,
#     }

#     instructions = models.TextField(blank=True, default=TRUE_FALSE_BASE_INSTRUCTION)
#     context = models.TextField(blank=True, default="")
#     # context_image = models.ImageField(null=True, blank=True, upload_to=get_true_false_quiz_upload_to)
#     statements = JSONField(blank=True, default=list, schema=STATEMENTS_SCHEMA)

