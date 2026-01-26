from django.core.exceptions import ValidationError
from django.db import models

from open_ithageneia.models.shared import TimeStampedModel, Semester


class QuizCategoryModel(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "quiz_category"

    def __str__(self):
        return self.name


# TRUE_FALSE
# MULTIPLE_CHOICE
# MAPPING
# CATEGORIZE
# RECALL
# GAP_FILL
# GAP_FILL_MULTIPLE_CHOICE
class QuizQuestionTypeModel(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    instructions = models.TextField()

    class Meta:
        db_table = "quiz_question_type"

    def __str__(self):
        return self.name


class QuizQuestionModel(TimeStampedModel):
    number = models.IntegerField()
    context = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True, upload_to="quiz/questions")
    semester = models.ForeignKey(Semester, on_delete=models.RESTRICT)
    category = models.ForeignKey(QuizCategoryModel, on_delete=models.RESTRICT)
    type = models.ForeignKey(QuizQuestionTypeModel, on_delete=models.RESTRICT)
    min_correct_answers = models.IntegerField(null=True, blank=True)
    are_sentences_continuous = models.BooleanField(null=True, blank=True)
    are_answers_hidden = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "quiz_question"

        constraints = [
            models.UniqueConstraint(
                fields=["semester", "category", "number"],
                name="unique_question_per_semester_category",
            )
        ]

        indexes = [
            models.Index(fields=["semester", "category"]),
        ]

        ordering = ["number"]

    def __str__(self):
        return f"{self.semester} {self.category.name} ΘΕΜΑ {self.number}"


class ItemGroupModel(TimeStampedModel):
    class GroupType(models.IntegerChoices):
        Choices = 0, "Choices"
        Categories = 2, "Categories"
        Blanks = 3, "Blanks"

    name = models.CharField(max_length=100, null=True, blank=True)
    is_first = models.BooleanField(null=True, blank=True)
    type = models.IntegerField(choices=GroupType, default=GroupType.Choices)

    question = models.ForeignKey(
        QuizQuestionModel, on_delete=models.CASCADE, related_name="item_groups"
    )

    class Meta:
        db_table = "quiz_item_group"


class QuizQuestionItemModel(TimeStampedModel):
    text = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True)

    is_correct = models.BooleanField(null=True, blank=True)
    item_group = models.ForeignKey(ItemGroupModel, null=True, on_delete=models.RESTRICT)
    pair = models.ForeignKey("self", null=True, on_delete=models.RESTRICT)
    question = models.ForeignKey(QuizQuestionModel, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_question_item"

    def clean(self):
        if self.item_group and self.item_group.question_id != self.question_id:
            raise ValidationError("Answer question must match item group question")
