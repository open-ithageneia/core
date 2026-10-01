import os
import uuid

from django.db import models

from open_ithageneia.models import TimeStampedModel


def get_quiz_asset_upload_to(instance, filename):
	_, ext = os.path.splitext(filename)

	return f"quizzes/assets/{uuid.uuid4()}{ext}"


class QuizAsset(TimeStampedModel):
	title = models.CharField(max_length=255, blank=True, default="")
	image = models.ImageField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)
	audio = models.FileField(upload_to=get_quiz_asset_upload_to, blank=True, null=True)

	def __str__(self):
		return self.title if self.title else str(self.pk)

	class Meta:
		verbose_name_plural = "Quiz Assets"

	@property
	def image_url(self):
		return self.image.url if self.image else None

	@property
	def audio_url(self):
		return self.audio.url if self.audio else None


class QuizCategory(TimeStampedModel):
	GEOGRAPHY = "GEOGRAPHY"
	CIVICS = "CIVICS"
	HISTORY = "HISTORY"
	CULTURE = "CULTURE"
	LISTENING = "LISTENING"

	code = models.CharField(max_length=32, primary_key=True)
	name = models.CharField(max_length=64)
	name_el = models.CharField(
		"Greek name",
		max_length=64,
		blank=True,
		default="",
		help_text="Name shown to the user. Falls back to the English name when empty.",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		verbose_name_plural = "Quiz Categories"
		ordering = ["order", "code"]

	def __str__(self):
		return self.name or self.code

	@property
	def label(self):
		return self.name_el or self.name or self.code
