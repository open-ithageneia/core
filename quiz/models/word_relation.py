import re

from django.core.exceptions import ValidationError
from django.db import models

from .base import AbstractQuiz

# The one ``{…}`` span in a word relation sentence: the word or phrase the
# candidate has to find the synonym/antonym of, shown underlined.
UNDERLINE_PATTERN = re.compile(r"\{([^{}]*)\}")


def split_sentence(sentence):
	"""Split *sentence* around its ``{…}`` marker.

	Returns ``(before, underlined, after)``, or ``None`` when the sentence does
	not mark exactly one non-empty word or phrase.
	"""
	matches = list(UNDERLINE_PATTERN.finditer(sentence))
	if len(matches) != 1:
		return None
	match = matches[0]
	before, after = sentence[: match.start()], sentence[match.end() :]
	underlined = match.group(1).strip()
	# A stray brace outside the marker is a typo, not text to show.
	if not underlined or any(brace in before + after for brace in "{}"):
		return None
	return before, underlined, after


class WordRelation(AbstractQuiz):

	INSTRUCTION_TEXT = {
		"SYNONYM": "Να βρείτε το συνώνυμο της υπογραμμισμένης λέξης/φράσης",
		"ANTONYM": "Να βρείτε το αντώνυμο της υπογραμμισμένης λέξης/φράσης",
	}

	class WordRelationType(models.TextChoices):
		SYNONYM = "SYNONYM", "Synonym"
		ANTONYM = "ANTONYM", "Antonym"

	type = models.CharField(
		max_length=15,
		choices=WordRelationType,
		default=WordRelationType.SYNONYM,
	)

	prompt_text = models.TextField(
		verbose_name="sentence",
		help_text=(
			"The sentence, with the word or phrase to underline in curly braces, "
			"e.g. «Η τιμή του εισιτηρίου ήταν {προσιτή}.»"
		),
	)

	class Meta:
		verbose_name_plural = "Word relations (Synonyms/Antonyms)"

	def __str__(self):
		return f"id: {self.id}, {self.type} - {self.category}"

	@property
	def instruction(self):
		return self.INSTRUCTION_TEXT[self.type]

	def sentence_parts(self):
		return split_sentence(self.prompt_text)

	def clean(self):
		super().clean()
		if self.prompt_text and self.sentence_parts() is None:
			raise ValidationError(
				{
					"prompt_text": (
						"Mark exactly one word or phrase to underline with curly "
						"braces, e.g. «Η τιμή ήταν {προσιτή}.»"
					)
				}
			)
		# ``_state.adding`` rather than ``pk``: an import can create a question
		# under an id taken from the sheet, so it has a pk before any choices.
		if self._state.adding:
			return
		if self.choices.filter(is_correct=True).count() != 1:
			raise ValidationError(
				"Word relation questions must have exactly one correct choice."
			)


class WordRelationChoice(models.Model):
	question = models.ForeignKey(
		WordRelation,
		on_delete=models.CASCADE,
		related_name="choices",
	)
	text = models.CharField(max_length=255)
	is_correct = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["order", "id"]
		verbose_name = "Word relation choice"
		verbose_name_plural = "Word relation choices"

	def __str__(self):
		return self.text
