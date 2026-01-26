from django.db import models

from .managers import TimeStampedQueryset


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TimeStampedQueryset.as_manager()

    class Meta:
        abstract = True


class Semester(models.Model):
    class SemesterHalf(models.IntegerChoices):
        First = 0, "First half"
        Second = 1, "Second half"

    year = models.PositiveSmallIntegerField()
    half = models.PositiveSmallIntegerField(choices=SemesterHalf)

    class Meta:
        unique_together = ("year", "half")
        ordering = ["-year", "-half"]
        db_table = "semester"

    def __str__(self):
        return f"{self.get_half_display()} of {self.year}"


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


class QuizQuestionBaseModel(TimeStampedModel):
    number = models.IntegerField()
    context = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True, upload_to="quiz/questions")
    semester = models.ForeignKey(Semester, on_delete=models.RESTRICT)
    category = models.ForeignKey(QuizCategoryModel, on_delete=models.RESTRICT)
    type = models.ForeignKey(QuizQuestionTypeModel, on_delete=models.RESTRICT)

    class Meta:
        abstract = True

        constraints = [
            models.UniqueConstraint(
                fields=["semester", "category", "number"],
                name="unique_question_per_semester_category",
            )
        ]

        indexes = [
            models.Index(fields=["semester", "category", "type"]),
        ]

        ordering = ["number"]

    def __str__(self):
        return f"{self.semester} {self.category.name} ΘΕΜΑ {self.number}"


class QuizTrueFalseQuestionModel(QuizQuestionBaseModel):
    class Meta:
        db_table = "quiz_true_false_question"


class QuizMultipleChoiceQuestionModel(QuizQuestionBaseModel):
    # Can be removed
    has_multiple = models.BooleanField(default=False)

    class Meta:
        db_table = "quiz_multiple_question"


class QuizRecallQuestionModel(QuizQuestionBaseModel):
    min_correct_answers = models.IntegerField(default=1)

    class Meta:
        db_table = "quiz_recall_question"


class QuizMappingQuestionModel(QuizQuestionBaseModel):
    class Meta:
        db_table = "quiz_mapping_question"


class QuizCategorizeQuestionModel(QuizQuestionBaseModel):
    class Meta:
        db_table = "quiz_categorize_question"


class QuizGapFillQuestionModel(QuizQuestionBaseModel):
    class Meta:
        db_table = "quiz_gap_fill_question"


class QuizGapFillMultipleChoiceQuestionModel(QuizQuestionBaseModel):
    class Meta:
        db_table = "quiz_gap_fill_multiple_choice_question"


class QuizQuestionItemModel(TimeStampedModel):
    text = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True, upload_to="quiz/questions")

    class Meta:
        abstract = True


class QuizTrueFalseItem(QuizQuestionItemModel):
    question = models.ForeignKey(QuizTrueFalseQuestionModel, on_delete=models.RESTRICT)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "quiz_true_false_item"


class QuizMultipleChoiceItem(QuizQuestionItemModel):
    question = models.ForeignKey(
        QuizMultipleChoiceQuestionModel, on_delete=models.RESTRICT
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "quiz_multiple_choice_item"


class QuizRecallItem(QuizQuestionItemModel):
    question = models.ForeignKey(QuizRecallQuestionModel, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_recall_item"


class QuizMappingItem(QuizQuestionItemModel):
    question = models.ForeignKey(QuizMappingQuestionModel, on_delete=models.RESTRICT)
    pair = models.OneToOneField("self", on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_mapping_item"


class QuizCategoryGroup(QuizQuestionItemModel):
    question = models.ForeignKey(QuizCategorizeQuestionModel, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_categorize_group"


class QuizCategoryItem(QuizQuestionItemModel):
    group = models.ForeignKey(QuizCategoryGroup, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_categorize_item"


class QuizGap(QuizQuestionItemModel):
    question = models.ForeignKey(QuizGapFillQuestionModel, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_gap"


class QuizGapItem(QuizQuestionItemModel):
    gap = models.OneToOneField(QuizGap, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_gap_item"


class QuizGapMultipleChoice(QuizQuestionItemModel):
    question = models.ForeignKey(QuizGapFillQuestionModel, on_delete=models.RESTRICT)

    class Meta:
        db_table = "quiz_gap_multiple_choice"


class QuizGapChoiceItem(QuizQuestionItemModel):
    gap = models.ForeignKey(QuizGapMultipleChoice, on_delete=models.RESTRICT)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "quiz_gap_choice_item"
