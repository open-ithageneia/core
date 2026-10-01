from django.db import models

from .assets import QuizAsset
from .base import AbstractQuiz


class Matching(AbstractQuiz):
	INSTRUCTION_TEXT = "Αντιστοιχίστε τα σωστά ζεύγη"

	left_title = models.CharField(max_length=255, blank=True, default="")
	right_title = models.CharField(max_length=255, blank=True, default="")

	class Meta:
		verbose_name_plural = "Matching"


class MatchPair(models.Model):
	question = models.ForeignKey(
		Matching,
		on_delete=models.CASCADE,
		related_name="pairs",
	)
	left_text = models.TextField(blank=True, default="")
	left_image = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
	)
	right_text = models.TextField(blank=True, default="")
	right_image = models.ForeignKey(
		QuizAsset,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="+",
	)
	order = models.PositiveSmallIntegerField(
		default=0, help_text="Position of the left item in its column."
	)
	right_order = models.PositiveSmallIntegerField(
		default=0,
		help_text=(
			"Position of the right item in its column. Leave equal to the left "
			"order unless the right column should be shuffled."
		),
	)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Match pair"
		verbose_name_plural = "Match pairs"

	def __str__(self):
		return f"{self.left_text or '—'} ↔ {self.right_text or '—'}"

	@property
	def has_left(self):
		return bool(self.left_text or self.left_image_id)

	@property
	def has_right(self):
		return bool(self.right_text or self.right_image_id)
