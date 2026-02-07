from django.db import models


class QuizType(models.TextChoices):
    TRUE_FALSE = "TRUE_FALSE", "True/False"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Mutliple Choice"
    FILL_IN_THE_BLANK = "FILL_IN_THE_BLANK", "Fill In The Blank"
    MATCHING = "MATCHING", "Matching"
    DRAG_AND_DROP = "DRAG_AND_DROP", "Drag And Drop"
    OPEN_TEXT = "OPEN_TEXT", "Open Text"


class QuizCategory(models.TextChoices):
    GEORGRAPHY = "GEORGRAPHY", "Geography"
    CIVICS = "CIVICS", "Civics"
    HISTORY = "HISTORY", "History"
    CULTURE = "CULTURE", "Culture"
