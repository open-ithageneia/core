import re

from django.core.exceptions import ValidationError
from django.db import models

from .base import AbstractQuiz


class FillInTheBlank(AbstractQuiz):
	INSTRUCTION_TEXT = "Συμπληρώστε τα κενά"

	show_answers_as_choices = models.BooleanField(default=False)

	class Meta:
		verbose_name_plural = "Fill in the blank"

	def has_multiple_choices(self):
		"""Whether any blank offers the candidate a choice inline.

		A stored flag per sentence, so this is a read rather than a re-parse.
		"""
		return any(text.has_multiple_choices for text in self.texts.all())

	def instruction_choices(self):
		"""The word bank shown above the question, or ``None`` when there isn't one.

		Only offered when the question asks for it and no blank already carries
		its own choices — a blank that offers options inline needs no bank, and
		mixing the two would show the same words twice. Blanks whose choices
		repeat contribute once.
		"""
		if not self.show_answers_as_choices or self.has_multiple_choices():
			return None

		choices = [choice.text for choice in self.extra_choices.all()]
		seen = set()
		for text in self.texts.all():
			for part in text.parts.all():
				if not part.is_blank:
					continue
				texts = tuple(choice.text for choice in part.choices.all())
				if texts and texts not in seen:
					seen.add(texts)
					choices.extend(texts)
		return choices

	def rebuild_parts(self):
		for text in self.texts.all():
			text.rebuild_parts()


class FillInTheBlankText(models.Model):
	"""One sentence of a fill-in-the-blank question, stored as authored.

	``text`` holds the authoring DSL and is the source of truth::

	    Η Κως συνορεύει με <{{την Τουρκία}}*>
	    Το <{{1821}}*, {{1822}}> είναι η χρονιά της επανάστασης

	``<...>`` delimits a blank, ``{{...}}`` a choice within it, and a trailing
	``*`` marks the choice that is correct. A blank with several choices becomes
	a multiple-choice blank; a blank with one becomes a free-text answer.

	Saving parses that string into ``parts`` and their ``choices``. Those rows are
	derived — never edited directly — so the sentence stays one thing to author
	while the parse tree is queryable and the serializer no longer runs a regex
	per request. ``rebuild_parts()`` re-derives them for anything that writes
	around ``save()``.
	"""

	# The markup, and the only place it is defined.
	BLANK_PATTERN = re.compile(r"<(.+?)>")
	CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")

	question = models.ForeignKey(
		FillInTheBlank,
		on_delete=models.CASCADE,
		related_name="texts",
	)
	text = models.TextField(
		help_text=(
			"Use <{{answer}}*> for a blank and mark the correct choice with *. "
			'E.g. "Η Κως συνορεύει με <{{την Τουρκία}}*>".'
		),
	)
	has_multiple_choices = models.BooleanField(
		default=False,
		editable=False,
		help_text="Derived: whether any of this sentence's blanks offers a choice.",
	)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank text"
		verbose_name_plural = "Fill in the blank texts"

	def __str__(self):
		return self.text[:80]

	def clean(self):
		super().clean()
		self.parse()

	def save(self, *args, **kwargs):
		self.full_clean(exclude=["question"])
		super().save(*args, **kwargs)
		self.rebuild_parts()

	def blanks(self):
		return self.BLANK_PATTERN.findall(self.text)

	def choices_in(self, blank):
		return [
			(choice, marker == "*")
			for choice, marker in self.CHOICE_PATTERN.findall(blank)
		]

	def correct_answer(self, blank):
		correct = [
			choice for choice, is_correct in self.choices_in(blank) if is_correct
		]
		return correct[0] if correct else "?"

	def parse(self):
		raw_blanks = self.blanks()
		if not raw_blanks:
			raise ValidationError(
				f"{self.text}: no blanks found. Use <({{{{answer}}}}*)> syntax."
			)

		has_multiple_choices = False
		for blank in raw_blanks:
			choices = self.choices_in(blank)
			if not choices:
				raise ValidationError(
					f"{blank}: invalid blank — must contain at least one {{{{choice}}}}."
				)
			for choice, _ in choices:
				if not choice.strip():
					raise ValidationError(f"{choice}: blank contains an empty choice.")

			correct = [choice for choice, is_correct in choices if is_correct]
			if not correct:
				raise ValidationError(
					f"blank '<({blank})>' has no correct answer. "
					f"Mark exactly one with *."
				)
			if len(choices) > 1 and len(correct) == 1:
				has_multiple_choices = True

		parts = []
		for index, chunk in enumerate(self.BLANK_PATTERN.split(self.text)):
			if index % 2 == 0:
				if chunk:
					parts.append({"text": chunk, "is_blank": False, "choices": []})
			else:
				parts.append(
					{
						"text": "",
						"is_blank": True,
						"choices": [
							{"text": choice, "is_correct": is_correct}
							for choice, is_correct in self.choices_in(chunk)
						],
					}
				)

		return {"parts": parts, "has_multiple_choices": has_multiple_choices}

	def rebuild_parts(self):
		parsed = self.parse()

		if self.has_multiple_choices != parsed["has_multiple_choices"]:
			self.has_multiple_choices = parsed["has_multiple_choices"]
			type(self).objects.filter(pk=self.pk).update(
				has_multiple_choices=self.has_multiple_choices
			)

		self.parts.all().delete()
		for order, part in enumerate(parsed["parts"]):
			row = FillInTheBlankPart.objects.create(
				sentence=self,
				text=part["text"],
				is_blank=part["is_blank"],
				order=order,
			)
			FillInTheBlankChoice.objects.bulk_create(
				[
					FillInTheBlankChoice(
						part=row,
						text=choice["text"],
						is_correct=choice["is_correct"],
						order=position,
					)
					for position, choice in enumerate(part["choices"])
				]
			)


class FillInTheBlankPart(models.Model):
	sentence = models.ForeignKey(
		FillInTheBlankText,
		on_delete=models.CASCADE,
		related_name="parts",
	)
	text = models.TextField(
		blank=True,
		default="",
		help_text="The literal text of this run. Empty for a blank.",
	)
	is_blank = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank part"
		verbose_name_plural = "Fill in the blank parts"

	def __str__(self):
		return "[blank]" if self.is_blank else self.text[:40]


class FillInTheBlankChoice(models.Model):
	part = models.ForeignKey(
		FillInTheBlankPart,
		on_delete=models.CASCADE,
		related_name="choices",
	)
	text = models.CharField(max_length=255)
	is_correct = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank choice"
		verbose_name_plural = "Fill in the blank choices"

	def __str__(self):
		return self.text


class FillInTheBlankExtraChoice(models.Model):
	question = models.ForeignKey(
		FillInTheBlank,
		on_delete=models.CASCADE,
		related_name="extra_choices",
	)
	text = models.CharField(max_length=255)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Fill in the blank extra choice"
		verbose_name_plural = "Fill in the blank extra choices"

	def __str__(self):
		return self.text
