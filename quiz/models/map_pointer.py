from django.core.exceptions import ValidationError
from django.db import models

from .base import AbstractQuiz, MinCorrectAnswersMixin
from .map_area import MapArea, MapLevel


class MapPointer(MinCorrectAnswersMixin, AbstractQuiz):
	INSTRUCTION_TEXT = "Τοποθετήστε κάθε επιλογή στη σωστή περιοχή του χάρτη"

	# Kept as an alias so ``MapPointer.MapLevel`` still resolves everywhere it is
	# referenced; the enum itself lives in ``map_area``, for ``MapArea``.
	MapLevel = MapLevel

	level = models.PositiveSmallIntegerField(
		choices=MapLevel.choices,
		default=MapLevel.MUNICIPALITY,
		help_text="Administrative division level used for the map.",
	)
	show_answers = models.BooleanField(default=True)

	class Meta:
		verbose_name_plural = "Map Pointer"

	def _validate_content(self):
		self._validate_min_correct_answers()
		if not self.pk:
			return
		# The level decides which areas the picker offers, so an answer pointing
		# at an area from another level could never be matched.
		wrong_level = (
			MapArea.objects.filter(answer_links__answer__question=self)
			.exclude(level=self.level)
			.values_list("name", flat=True)
			.distinct()
		)
		if wrong_level:
			raise ValidationError(
				f"These areas are not level-{self.level} areas: "
				f"{', '.join(sorted(wrong_level))}."
			)
		# One label cannot be placed on the same polygon twice, so a repeat is
		# always a mistake — and the client would draw the label once per link.
		# ``order_by()`` clears the model's default ordering, which Django would
		# otherwise add to the GROUP BY and count every link on its own.
		repeated = {
			group["area_id"]
			for group in MapPointerAnswerArea.objects.filter(answer__question=self)
			.values("answer_id", "area_id")
			.order_by()
			.annotate(links=models.Count("id"))
			.filter(links__gt=1)
		}
		if repeated:
			names = MapArea.objects.filter(pk__in=repeated).values_list(
				"name", flat=True
			)
			raise ValidationError(
				f"An answer lists the same area more than once: "
				f"{', '.join(sorted(names))}."
			)


class MapPointerAnswer(models.Model):
	"""One label the candidate places on the map.

	An answer may accept several areas: a river crossing many prefectures is
	correct on any of them. Two answers may also share an area — a polygon
	several answers pass through accepts each of them, and holds one label per
	answer placed there.
	"""

	question = models.ForeignKey(
		MapPointer,
		on_delete=models.CASCADE,
		related_name="answers",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer answer"
		verbose_name_plural = "Map pointer answers"

	def __str__(self):
		first = self.alternatives.first()
		return first.text if first else f"answer {self.pk}"


class MapPointerAlternative(models.Model):
	answer = models.ForeignKey(
		MapPointerAnswer,
		on_delete=models.CASCADE,
		related_name="alternatives",
	)
	text = models.CharField(max_length=255)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer alternative"
		verbose_name_plural = "Map pointer alternatives"

	def __str__(self):
		return self.text


class MapPointerAnswerArea(models.Model):
	"""An area an answer may be placed on.

	An explicit through table rather than a plain ``ManyToManyField`` because the
	order the areas were chosen in is part of what the client receives.
	"""

	answer = models.ForeignKey(
		MapPointerAnswer,
		on_delete=models.CASCADE,
		related_name="area_links",
	)
	area = models.ForeignKey(
		MapArea,
		on_delete=models.PROTECT,
		related_name="answer_links",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Map pointer answer area"
		verbose_name_plural = "Map pointer answer areas"
		# No unique (answer, area) constraint, for the same reason
		# ``StatementChoice`` has no check constraint: ``_validate_content``
		# rejects a repeated area, so none should exist, but the backfill must
		# not be the thing that discovers otherwise on a production deploy.

	def __str__(self):
		return self.area.name
