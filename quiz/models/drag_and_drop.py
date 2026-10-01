from django.db import models

from .base import AbstractQuiz


class DragAndDrop(AbstractQuiz):
	INSTRUCTION_TEXT = "Σύρετε και αποθέστε στη σωστή θέση"

	left_title = models.CharField(max_length=255, blank=True, default="")
	right_title = models.CharField(max_length=255, blank=True, default="")

	class Meta:
		verbose_name_plural = "Drag And Drop"


class DragAndDropValue(models.Model):
	class Side(models.TextChoices):
		LEFT = "LEFT", "Left"
		RIGHT = "RIGHT", "Right"

	question = models.ForeignKey(
		DragAndDrop,
		on_delete=models.CASCADE,
		related_name="values",
	)
	side = models.CharField(max_length=5, choices=Side.choices)
	text = models.TextField()
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["side", "order", "id"]
		verbose_name = "Drag and drop value"
		verbose_name_plural = "Drag and drop values"

	def __str__(self):
		return self.text
