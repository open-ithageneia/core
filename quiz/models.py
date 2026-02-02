from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django_jsonform.models.fields import JSONField

from open_ithageneia.models import TimeStampedModel, ActivatableModel


'''
What we want:
1) Show JSON field properly in admin
2) Validate JSON field structure according to quiz rules
4) Check django-import-export
9) Pillow?
10) Admin
'''

# Check https://docs.djangoproject.com/en/6.0/ref/databases/#enabling-json1-extension-on-sqlite
# The JSON1 extension is enabled by default on SQLite 3.38+. -> 3.51.1 OK

# There is also this: https://pypi.org/project/django-json-widget/


TRUE_FALSE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό της κάθε πρότασης, σημειώνοντας Σ, αν η πρόταση που σας δίνεται παρακάτω είναι σωστή, ή Λ, αν είναι λάθος."
# MULTIPLE_CHOICE_BASE_INSTRUCTION = "Γράψτε στο τετράδιό σας τον αριθμό του θέματος και δίπλα τη σωστή απάντηση, σημειώνοντας το αντίστοιχο γράμμα (Α ή Β ή Γ ή Δ)."


class ExamSession(TimeStampedModel):
    class Month(models.IntegerChoices):
        JAN = 1, "January"
        FEB = 2, "February"
        MAR = 3, "March"
        APR = 4, "April"
        MAY = 5, "May"
        JUN = 6, "June"
        JUL = 7, "July"
        AUG = 8, "August"
        SEP = 9, "September"
        OCT = 10, "October"
        NOV = 11, "November"
        DEC = 12, "December"

    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    month = models.PositiveSmallIntegerField(choices=Month.choices)

    class Meta:
        indexes = [models.Index(fields=["year", "month"])]
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="uniq_exam_session"),
            models.CheckConstraint(
                condition=Q(month__gte=1, month__lte=12),
                name="month_between_1_and_12",
            ),
        ]

    def __str__(self):
        return f"{self.get_month_display()}, {self.year}"


def get_quiz_asset_upload_to(instance, filename):
    return f"quizzes/assets/{instance.id}/{filename}"


class QuizAsset(TimeStampedModel):
    title = models.CharField(max_length=255, blank=True, default="")
    image = models.ImageField(upload_to=get_quiz_asset_upload_to)

    def __str__(self):
        return self.title if self.title else self.pk


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
    instructions = models.TextField(
        blank=True,
        default=TRUE_FALSE_BASE_INSTRUCTION
    ) # Choices also?
    exam_session = models.ForeignKey(
        ExamSession,
        null=True,
        blank=True,
        related_name="quiz_questions",
        on_delete=models.SET_NULL, # or PROTECT?
    )
    content = JSONField(
        blank=True,
        default=lambda: {"choices": []},
        schema=CONTENT_SCHEMA
    )


