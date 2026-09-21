import importlib
import sys
import types

from django.contrib.admin.sites import site
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.forms.models import inlineformset_factory
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path, reverse
from types import SimpleNamespace

from quiz.admin import (
	ListeningAdmin,
	ListeningPartInline,
	ListeningQuestionForm,
	ListeningQuestionFormSet,
	ListeningQuestionInline,
	MapPointerAdmin,
	MatchingAdmin,
	StatementChoiceFormSet,
)
from quiz.models import (
	DragAndDrop,
	DragAndDropValue,
	FillInTheBlank,
	FillInTheBlankChoice,
	FillInTheBlankExtraChoice,
	FillInTheBlankPart,
	FillInTheBlankText,
	Listening,
	ListeningPart,
	MapArea,
	MapPointer,
	MapPointerAlternative,
	MapPointerAnswer,
	MapPointerAnswerArea,
	Matching,
	MatchPair,
	OpenEnded,
	OpenEndedAlternative,
	OpenEndedAnswer,
	QuizAsset,
	QuizCategory,
	Statement,
	StatementChoice,
)
from quiz.resources import (
	DragAndDropResource,
	MatchingResource,
	OpenEndedResource,
	StatementResource,
)
from quiz.serializers import (
	DragAndDropSerializer,
	FillInTheBlankSerializer,
	ListeningSerializer,
	MapPointerSerializer,
	MatchingSerializer,
	OpenEndedSerializer,
	StatementSerializer,
)
from quiz.services import QuizService

backfill = importlib.import_module("quiz.migrations.0022_backfill_quiz_content")

# A urlconf with the admin mounted somewhere other than /admin/, to prove the
# pages build their links rather than spelling them out. A real module, because
# ``reverse`` caches its resolver by the urlconf's name.
ALT_ADMIN_URLCONF = types.ModuleType("quiz.tests_alt_admin_urls")
ALT_ADMIN_URLCONF.urlpatterns = [path("backoffice/", site.urls)]
sys.modules[ALT_ADMIN_URLCONF.__name__] = ALT_ADMIN_URLCONF


# ---------------------------------------------------------------------------
# Builders. Content is rows now, so making a question takes two steps; these
# keep the tests reading as though it were still one.
# ---------------------------------------------------------------------------


def _true_false(*statements, **kwargs):
	question = Statement.objects.create(
		type=Statement.StatementType.TRUE_FALSE, **kwargs
	)
	StatementChoice.objects.bulk_create(
		[
			StatementChoice(
				statement=question, text=text, is_correct=is_correct, order=index
			)
			for index, (text, is_correct) in enumerate(statements)
		]
	)
	return question


def _multiple_choice(prompt, **kwargs):
	question = Statement.objects.create(
		type=Statement.StatementType.MULTIPLE_CHOICE, prompt_text=prompt, **kwargs
	)
	StatementChoice.objects.bulk_create(
		[
			StatementChoice(statement=question, text="A", is_correct=True, order=0),
			StatementChoice(statement=question, text="B", is_correct=False, order=1),
		]
	)
	return question


class ListeningTests(TestCase):
	def setUp(self):
		self.asset = QuizAsset.objects.create(
			title="clip", audio=ContentFile(b"audio-bytes", name="clip.mp3")
		)
		self.group = Listening.objects.create(audio=self.asset, transcript="transcript")
		# The first part holds the true/false statements, the second the
		# multiple-choice questions — the usual layout.
		self.part_a = ListeningPart.objects.create(
			listening=self.group, description="Σημειώστε σωστό ή λάθος"
		)
		self.part_b = ListeningPart.objects.create(listening=self.group)
		self.true_false = _true_false(
			("first", True),
			("second", False),
			listening=self.group,
			part=self.part_a,
			order=0,
		)
		# Created out of order, to prove ``order`` drives the output.
		self.multiple_choice = [
			_multiple_choice(
				f"question {index}",
				listening=self.group,
				part=self.part_b,
				order=index,
			)
			for index in (2, 1)
		]

	def test_serializes_audio_and_questions_grouped_by_part(self):
		data = ListeningSerializer(self.group).data

		self.assertTrue(data["audio_url"].endswith(".mp3"))
		self.assertEqual(data["max_plays"], 2)
		self.assertEqual(
			[part["id"] for part in data["parts"]], [self.part_a.id, self.part_b.id]
		)
		self.assertEqual(
			[question["id"] for question in data["parts"][0]["questions"]],
			[self.true_false.id],
		)
		self.assertEqual(
			[question["id"] for question in data["parts"][1]["questions"]],
			[self.multiple_choice[1].id, self.multiple_choice[0].id],
		)
		# The group itself has no ``content`` of its own.
		self.assertNotIn("content", data)

	def test_serializes_the_description_of_each_part(self):
		data = ListeningSerializer(self.group).data

		self.assertEqual(
			[part["description"] for part in data["parts"]],
			["Σημειώστε σωστό ή λάθος", ""],
		)

	def test_empty_parts_are_left_out(self):
		Statement.objects.filter(listening=self.group).update(part=self.part_a)

		data = ListeningSerializer(self.group).data

		self.assertEqual([part["id"] for part in data["parts"]], [self.part_a.id])

	def test_questions_without_a_part_are_left_out(self):
		"""A part-less question has no section to be shown under."""
		self.true_false.part = None
		self.true_false.save()

		data = ListeningSerializer(self.group).data

		self.assertEqual([part["id"] for part in data["parts"]], [self.part_b.id])

	def test_rejects_a_part_of_another_listening_question(self):
		other = Listening.objects.create(audio=self.asset)
		self.true_false.part = ListeningPart.objects.create(listening=other)

		with self.assertRaises(ValidationError):
			self.true_false.full_clean()

	def test_deleting_a_part_keeps_its_questions(self):
		self.part_a.delete()
		self.true_false.refresh_from_db()

		self.assertIsNone(self.true_false.part_id)

	def test_part_is_independent_of_question_type(self):
		"""The first part is usually the true/false one, but that is not enforced."""
		self.true_false.part = self.part_b
		self.true_false.save()

		self.group.full_clean()

		data = ListeningSerializer(self.group).data
		self.assertEqual([part["id"] for part in data["parts"]], [self.part_b.id])
		self.assertEqual(len(data["parts"][0]["questions"]), 3)

	def test_rejects_a_second_true_false_question(self):
		_true_false(("extra", True), listening=self.group, order=9)

		with self.assertRaises(ValidationError):
			self.group.full_clean()

	def test_rejects_a_group_without_multiple_choice_questions(self):
		Statement.objects.filter(
			listening=self.group, type=Statement.StatementType.MULTIPLE_CHOICE
		).delete()

		with self.assertRaises(ValidationError):
			self.group.full_clean()

	def test_empty_group_is_allowed(self):
		"""The clip is created first, then its questions are added."""
		Listening.objects.create(audio=self.asset).full_clean()

	def test_questions_are_never_sampled_standalone(self):
		standalone = _multiple_choice("standalone")

		sampled = QuizService.get_by_category(category="", amount=50)
		statement_ids = {
			item["id"] for item in sampled if item["quiz_type"] == "Statement"
		}

		self.assertIn(standalone.id, statement_ids)
		self.assertNotIn(self.true_false.id, statement_ids)

	def test_listening_is_kept_out_of_the_general_pool(self):
		sampled = QuizService.get_by_category(category="", amount=50)

		self.assertNotIn("Listening", {item["quiz_type"] for item in sampled})

	def test_listening_is_sampled_when_requested_by_type(self):
		sampled = QuizService.get_by_category(
			category="", amount=1, quiz_type=QuizService.LISTENING_QUIZ_TYPE
		)

		self.assertEqual(len(sampled), 1)
		self.assertEqual(sampled[0]["quiz_type"], "Listening")
		self.assertEqual(sum(len(part["questions"]) for part in sampled[0]["parts"]), 3)

	def test_deleting_a_group_deletes_its_questions(self):
		self.group.delete()

		self.assertFalse(Statement.objects.filter(listening_id=self.group.id).exists())


class WireFormatTests(TestCase):
	"""The exact ``content`` object each type puts on the wire.

	``frontend/js/types/models.ts`` is written against these shapes, so they are
	asserted whole rather than key by key — a missing or renamed key is a broken
	client, not a cosmetic change. ``quiz/test_wire_format.py`` makes the same
	assertion against every legacy shape, through the real migration.
	"""

	def test_statement_content(self):
		question = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE, prompt_text="Ποια είναι;"
		)
		StatementChoice.objects.create(
			statement=question, text="Α", is_correct=True, order=0
		)
		StatementChoice.objects.create(
			statement=question, text="Β", is_correct=False, order=1
		)

		self.assertEqual(
			StatementSerializer(question).data["content"],
			{
				"choices": [
					{"is_correct": True, "text": "Α", "asset_url": None},
					{"is_correct": False, "text": "Β", "asset_url": None},
				],
				"prompt_text": "Ποια είναι;",
				"prompt_asset_url": None,
				"prompt_audio_url": None,
			},
		)

	def test_an_unset_prompt_is_reported_as_null(self):
		"""It was a JSON key that could be absent; it is a column that can be
		empty. The client has always been told ``null`` either way."""
		question = Statement.objects.create(type=Statement.StatementType.TRUE_FALSE)

		self.assertIsNone(StatementSerializer(question).data["content"]["prompt_text"])

	def test_drag_and_drop_content_is_a_bare_two_column_list(self):
		question = DragAndDrop.objects.create(
			left_title="Ποταμοί", right_title="Λίμνες"
		)
		DragAndDropValue.objects.create(
			question=question,
			side=DragAndDropValue.Side.LEFT,
			text="Αλιάκμονας",
			order=0,
		)
		DragAndDropValue.objects.create(
			question=question, side=DragAndDropValue.Side.RIGHT, text="Κερκίνη", order=0
		)

		self.assertEqual(
			DragAndDropSerializer(question).data["content"],
			[
				{"title": "Ποταμοί", "values": ["Αλιάκμονας"]},
				{"title": "Λίμνες", "values": ["Κερκίνη"]},
			],
		)

	def test_matching_ids_are_regenerated_from_the_row_order(self):
		"""Left item *i* gets id i+1 and points at i+1+n — the numbering the
		importer used to synthesise and store."""
		question = Matching.objects.create(left_title="Α", right_title="Β")
		for index, (left, right) in enumerate([("α1", "β1"), ("α2", "β2")]):
			MatchPair.objects.create(
				question=question, left_text=left, right_text=right, order=index
			)

		content = MatchingSerializer(question).data["content"]

		self.assertEqual(
			[
				(item["id"], item["matched_id"])
				for item in content["columns"][0]["items"]
			],
			[(1, 3), (2, 4)],
		)
		self.assertEqual(
			[
				(item["id"], item["matched_id"])
				for item in content["columns"][1]["items"]
			],
			[(3, 1), (4, 2)],
		)

	def test_fill_in_the_blank_parses_its_sentences_on_the_way_out(self):
		question = FillInTheBlank.objects.create(show_answers_as_choices=True)
		FillInTheBlankText.objects.create(
			question=question, text="Η Κως συνορεύει με <{{την Τουρκία}}*>", order=0
		)
		FillInTheBlankExtraChoice.objects.create(
			question=question, text="τη Βουλγαρία", order=0
		)

		content = FillInTheBlankSerializer(question).data["content"]

		self.assertEqual(content["show_answers_as_choices"], True)
		self.assertEqual(content["has_multiple_choices"], False)
		self.assertEqual(
			content["prompt_instruction_choices"], ["τη Βουλγαρία", "την Τουρκία"]
		)
		self.assertEqual(
			content["texts"],
			[
				{
					"parts": [
						{"text": "Η Κως συνορεύει με ", "is_blank": False},
						{
							"text": None,
							"is_blank": True,
							"choices": [{"text": "την Τουρκία", "is_correct": True}],
						},
					]
				}
			],
		)

	def test_open_ended_content(self):
		question = OpenEnded.objects.create(
			prompt_text="Ποιος ποταμός;", min_correct_answers=1
		)
		answer = OpenEndedAnswer.objects.create(question=question, order=0)
		OpenEndedAlternative.objects.create(answer=answer, text="Αλιάκμονας", order=0)
		OpenEndedAlternative.objects.create(answer=answer, text="Αλιακμων", order=1)

		self.assertEqual(
			OpenEndedSerializer(question).data["content"],
			{
				"min_correct_answers": 1,
				"prompt_text": "Ποιος ποταμός;",
				"texts": [["Αλιάκμονας", "Αλιακμων"]],
				"prompt_asset_url": None,
			},
		)


class MapPointerContentTests(TestCase):
	"""An answer may accept several areas — e.g. a river crossing prefectures."""

	LEVEL = MapPointer.MapLevel.PREFECTURE_UNIT

	def setUp(self):
		# ``MapArea`` is seeded from the GeoJSON by migration 0022, so the test
		# database already has every real area name.
		self.areas = list(MapArea.objects.filter(level=self.LEVEL)[:3])

	def _create(self, *groups, min_correct_answers=1):
		question = MapPointer.objects.create(
			level=self.LEVEL,
			prompt_text="Πού βρίσκεται;",
			show_answers=True,
			min_correct_answers=min_correct_answers,
		)
		for index, (alternatives, areas) in enumerate(groups):
			answer = MapPointerAnswer.objects.create(question=question, order=index)
			MapPointerAlternative.objects.bulk_create(
				[
					MapPointerAlternative(answer=answer, text=text, order=position)
					for position, text in enumerate(alternatives)
				]
			)
			MapPointerAnswerArea.objects.bulk_create(
				[
					MapPointerAnswerArea(answer=answer, area=area, order=position)
					for position, area in enumerate(areas)
				]
			)
		return question

	def test_an_answer_keeps_every_area_it_accepts(self):
		question = self._create((["Αλιάκμονας"], self.areas[:2]))

		self.assertEqual(
			MapPointerSerializer(question).data["content"]["texts"],
			[
				{
					"alternatives": ["Αλιάκμονας"],
					"areas": [area.name for area in self.areas[:2]],
				}
			],
		)

	def test_an_answer_with_no_areas_omits_the_key(self):
		"""``areas`` is left out rather than sent empty — as it always was."""
		question = self._create((["Αλιάκμονας"], []))

		self.assertEqual(
			MapPointerSerializer(question).data["content"]["texts"],
			[{"alternatives": ["Αλιάκμονας"]}],
		)

	def test_rejects_an_area_outside_the_map_level(self):
		other_level = MapArea.objects.exclude(level=self.LEVEL).first()
		question = self._create((["Αλιάκμονας"], [self.areas[0], other_level]))

		with self.assertRaises(ValidationError):
			question.full_clean()

	def test_two_answers_may_share_an_area(self):
		"""Two rivers can run through the same prefecture; the polygon accepts
		each of them and holds one label per answer placed on it."""
		question = self._create(
			(["Αλιάκμονας"], [self.areas[0], self.areas[1]]),
			(["Αξιός"], [self.areas[1], self.areas[2]]),
			min_correct_answers=2,
		)
		question.full_clean()

		self.assertEqual(
			[
				group.get("areas")
				for group in MapPointerSerializer(question).data["content"]["texts"]
			],
			[
				[self.areas[0].name, self.areas[1].name],
				[self.areas[1].name, self.areas[2].name],
			],
		)

	def test_rejects_the_same_area_twice_in_one_answer(self):
		"""One label cannot be placed on the same polygon twice, and the client
		would draw it once per link."""
		question = self._create((["Αλιάκμονας"], [self.areas[0], self.areas[0]]))

		with self.assertRaises(ValidationError):
			question.full_clean()

	def test_min_correct_answers_cannot_exceed_the_answers_available(self):
		question = self._create((["Αλιάκμονας"], self.areas[:1]), min_correct_answers=5)

		with self.assertRaises(ValidationError):
			question.full_clean()

	def test_deleting_a_question_leaves_the_areas_alone(self):
		question = self._create((["Αλιάκμονας"], self.areas[:1]))
		before = MapArea.objects.count()

		question.delete()

		self.assertEqual(MapArea.objects.count(), before)


class MapAreaTests(TestCase):
	"""The table that turned area names from an undeclared foreign key into a
	real one."""

	def test_the_geojson_is_seeded_by_the_migration(self):
		# One row per named area per level, for all five levels.
		self.assertEqual(
			sorted(set(MapArea.objects.values_list("level", flat=True))),
			[1, 2, 3, 4, 5],
		)
		self.assertGreater(MapArea.objects.count(), 500)

	def test_the_search_name_is_folded_for_accent_blind_matching(self):
		"""Greek is routinely typed without its tonos."""
		area = MapArea.objects.create(level=1, name="Ιωάννινα")

		self.assertEqual(area.search_name, "ιωαννινα")
		self.assertTrue(
			MapArea.objects.filter(search_name__contains="ιωαννιν").exists()
		)

	def test_an_area_an_answer_points_at_cannot_be_deleted(self):
		"""PROTECT is the whole point: a vanishing area used to break answers
		silently."""
		question = MapPointer.objects.create(level=1)
		answer = MapPointerAnswer.objects.create(question=question, order=0)
		area = MapArea.objects.filter(level=1).first()
		MapPointerAnswerArea.objects.create(answer=answer, area=area, order=0)

		from django.db.models import ProtectedError

		with self.assertRaises(ProtectedError):
			area.delete()

	def test_a_level_and_name_pair_is_unique(self):
		from django.db.utils import IntegrityError

		name = MapArea.objects.filter(level=1).first().name

		with self.assertRaises(IntegrityError):
			MapArea.objects.create(level=1, name=name)


class BlankParsingTests(TestCase):
	"""The authoring DSL stayed a parser rather than becoming tables; these are
	the rules it enforces."""

	def _sentence(self, text, question=None):
		return FillInTheBlankText(
			question=question or FillInTheBlank.objects.create(), text=text
		)

	def test_a_single_choice_blank_is_free_text(self):
		parsed = self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>").parse()

		self.assertFalse(parsed["has_multiple_choices"])
		self.assertEqual([part["is_blank"] for part in parsed["parts"]], [False, True])

	def test_several_choices_in_one_blank_make_it_multiple_choice(self):
		parsed = self._sentence("Το <{{1821}}*, {{1822}}> ήταν").parse()

		self.assertTrue(parsed["has_multiple_choices"])

	def test_a_sentence_with_no_blank_is_rejected(self):
		with self.assertRaises(ValidationError):
			self._sentence("Χωρίς κενό").parse()

	def test_a_blank_with_no_correct_choice_is_rejected(self):
		with self.assertRaises(ValidationError):
			self._sentence("Το <{{1821}}, {{1822}}> ήταν").parse()

	def test_a_blank_with_an_empty_choice_is_rejected(self):
		with self.assertRaises(ValidationError):
			self._sentence("Το <{{ }}*> ήταν").parse()

	def test_the_model_validates_by_parsing(self):
		"""``clean()`` is just ``parse()`` — there is no second copy of the rules."""
		with self.assertRaises(ValidationError):
			self._sentence("no blank here").full_clean()

	def test_no_word_bank_when_a_blank_carries_its_own_choices(self):
		"""Offering both would show the same words twice."""
		question = FillInTheBlank.objects.create(show_answers_as_choices=True)
		FillInTheBlankText.objects.create(
			question=question, text="Το <{{1821}}*, {{1822}}> ήταν"
		)

		self.assertIsNone(question.instruction_choices())

	def test_repeated_choices_contribute_to_the_word_bank_once(self):
		question = FillInTheBlank.objects.create(show_answers_as_choices=True)
		for order, text in enumerate(
			[
				"Η Κως συνορεύει με <{{την Τουρκία}}*>",
				"Το Διδυμότειχο συνορεύει με <{{την Τουρκία}}*>",
			]
		):
			FillInTheBlankText.objects.create(question=question, text=text, order=order)

		self.assertEqual(question.instruction_choices(), ["την Τουρκία"])


class StatementValidationTests(TestCase):
	def test_a_multiple_choice_question_needs_a_correct_choice(self):
		question = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE
		)
		StatementChoice.objects.create(statement=question, text="Α", is_correct=False)

		with self.assertRaises(ValidationError):
			question.full_clean()

	def test_the_rule_is_not_applied_before_there_are_choices(self):
		"""The admin saves the question before its inlines, so a question being
		created has none yet."""
		Statement(type=Statement.StatementType.MULTIPLE_CHOICE).full_clean()

	def test_deleting_a_question_deletes_its_choices(self):
		question = _multiple_choice("q")

		question.delete()

		self.assertEqual(StatementChoice.objects.count(), 0)

	def test_choice_text_is_searchable(self):
		"""Not possible through the JSON blob — there was a TODO admitting it."""
		_multiple_choice("q")

		self.assertTrue(Statement.objects.filter(choices__text="A").exists())


class StatementChoiceFormSetTests(TestCase):
	"""The admin saves a statement before its choices, so the formset — not
	``Statement.full_clean()`` — is what enforces the rule on admin saves."""

	@staticmethod
	def _formset(statement, deleted=(), correct=None):
		"""Post every existing choice back, optionally deleting some.

		*correct* defaults to the rows already flagged correct; pass a set of
		indexes to change which ones are.
		"""
		FormSet = inlineformset_factory(
			Statement,
			StatementChoice,
			formset=StatementChoiceFormSet,
			fields=["order", "text", "is_correct"],
			extra=0,
		)
		choices = list(statement.choices.all())
		data = {
			"choices-TOTAL_FORMS": str(len(choices)),
			"choices-INITIAL_FORMS": str(len(choices)),
			"choices-MIN_NUM_FORMS": "0",
			"choices-MAX_NUM_FORMS": "1000",
		}
		for index, choice in enumerate(choices):
			data[f"choices-{index}-id"] = str(choice.pk)
			data[f"choices-{index}-order"] = str(choice.order)
			data[f"choices-{index}-text"] = choice.text
			is_correct = choice.is_correct if correct is None else index in correct
			if is_correct:
				data[f"choices-{index}-is_correct"] = "on"
			if index in deleted:
				data[f"choices-{index}-DELETE"] = "on"
		return FormSet(data, instance=statement, prefix="choices")

	def test_a_multiple_choice_question_keeps_its_correct_choice(self):
		formset = self._formset(_multiple_choice("q"))

		self.assertTrue(formset.is_valid(), formset.errors or formset.non_form_errors())

	def test_rejects_deleting_the_last_correct_choice(self):
		formset = self._formset(_multiple_choice("q"), deleted={0})

		self.assertFalse(formset.is_valid())

	def test_rejects_deleting_every_choice(self):
		"""An emptied multiple-choice question used to save cleanly: the rule was
		skipped once nothing was left to check, and the model rule reads rows the
		admin writes only after the parent is saved."""
		formset = self._formset(_multiple_choice("q"), deleted={0, 1})

		self.assertFalse(formset.is_valid())

	def test_a_true_false_question_may_lose_its_choices(self):
		"""Only multiple choice carries the rule — as in ``_validate_content``."""
		formset = self._formset(_true_false(("Σωστό", True)), deleted={0})

		self.assertTrue(formset.is_valid(), formset.errors or formset.non_form_errors())


class BackfillTests(TestCase):
	"""The migration's own parsers, exercised against the legacy shapes they
	exist for. They are frozen copies inside the migration, so nothing else
	covers them."""

	def test_alternatives_read_every_shape_texts_was_ever_stored_in(self):
		self.assertEqual(
			backfill.parse_alternatives({"alternatives": ["α", "β"]}), ["α", "β"]
		)
		# The pre-0003 single-text dict.
		self.assertEqual(backfill.parse_alternatives({"text": "α"}), ["α"])
		self.assertEqual(backfill.parse_alternatives(["α", "β"]), ["α", "β"])
		self.assertEqual(backfill.parse_alternatives("α"), ["α"])

	def test_areas_read_the_legacy_single_area_forms(self):
		self.assertEqual(backfill.parse_areas(["Α", "Β"]), ["Α", "Β"])
		self.assertEqual(backfill.parse_areas("Α"), ["Α"])
		self.assertEqual(backfill.parse_areas({"name": "Α"}), ["Α"])
		self.assertEqual(backfill.parse_areas(None), [])
		self.assertEqual(backfill.parse_areas(""), [])

	def test_matching_pairs_by_stored_ids_not_position(self):
		"""Nothing ever checked that the two columns' ids agreed, so the ids win
		and position is only the fallback."""
		content = {
			"columns": [
				{"title": "Α", "items": [{"id": 1, "matched_id": 4, "text": "α1"}]},
				{"title": "Β", "items": [{"id": 4, "matched_id": 1, "text": "β1"}]},
			]
		}

		canonical = backfill.canonical_from_json("Matching", content)

		self.assertEqual(
			canonical["pairs"],
			[
				{
					"left_text": "α1",
					"left_asset_id": None,
					"right_text": "β1",
					"right_asset_id": None,
					# where that right item sat in its own column
					"right_order": 0,
				}
			],
		)

	def test_rebuilt_json_round_trips_through_the_canonical_form(self):
		"""What the reverse writes back must read as the same content going
		forward again — that is what makes ``migrate quiz 0021`` safe."""
		question = Matching.objects.create(left_title="Α", right_title="Β")
		MatchPair.objects.create(
			question=question, left_text="α1", right_text="β1", order=0
		)

		rebuilt = backfill.json_from_rows("Matching", question)

		self.assertEqual(
			backfill.canonical_from_json("Matching", rebuilt),
			backfill.canonical_from_rows("Matching", question),
		)

	def test_the_statement_round_trip_keeps_every_choice(self):
		question = _multiple_choice("q")

		rebuilt = backfill.json_from_rows("Statement", question)

		self.assertEqual(
			backfill.canonical_from_json("Statement", rebuilt),
			backfill.canonical_from_rows("Statement", question),
		)


_CHOICE4_COLUMNS = ["choice4_text", "choice4_image", "choice4_is_correct"]


class ResourceRoundTripTests(TestCase):
	"""Import a sheet row, export it, and get the same row back. The columns did
	not change when the storage did."""

	def _import(self, resource, row, **kwargs):
		import tablib

		dataset = tablib.Dataset(headers=list(row))
		dataset.append(list(row.values()))
		result = resource.import_data(dataset, raise_errors=True, **kwargs)
		self.assertFalse(result.has_errors())
		return result

	def test_statement_round_trip(self):
		row = {
			"id": "",
			"type": "MULTIPLE_CHOICE",
			"category": QuizCategory.GEOGRAPHY,
			"prompt_text": "Ποια είναι;",
			"prompt_image": "",
			"prompt_audio": "",
			"listening": "",
			"part": "",
			"part_description": "",
			"order": "0",
			"choice1_text": "Α",
			"choice1_image": "",
			"choice1_is_correct": "true",
			"choice2_text": "Β",
			"choice2_image": "",
			"choice2_is_correct": "false",
		}
		self._import(StatementResource(), row)

		question = Statement.objects.get()
		self.assertEqual(question.prompt_text, "Ποια είναι;")
		self.assertEqual(
			[(c.text, c.is_correct) for c in question.choices.all()],
			[("Α", True), ("Β", False)],
		)

		exported = StatementResource().export(queryset=Statement.objects.all())
		self.assertEqual(exported[0][3], "Ποια είναι;")
		self.assertEqual(exported[0][10:13], ("Α", "", "true"))

	def test_an_ordinary_export_carries_four_choice_columns(self):
		"""The usual sheet keeps the shape it always had."""
		_multiple_choice("q")

		exported = StatementResource().export(queryset=Statement.objects.all())

		self.assertEqual(exported.headers[-3:], _CHOICE4_COLUMNS)

	def test_a_question_with_more_choices_widens_the_sheet(self):
		"""Truncating to four columns would be silent data loss: nothing caps a
		question at four choices, and re-importing a sheet replaces them
		wholesale — so a choice missing from it is gone for good."""
		question = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE, prompt_text="q"
		)
		texts = ["Α", "Β", "Γ", "Δ", "Ε"]
		StatementChoice.objects.bulk_create(
			[
				StatementChoice(
					statement=question, text=text, is_correct=index == 0, order=index
				)
				for index, text in enumerate(texts)
			]
		)

		exported = StatementResource().export(queryset=Statement.objects.all())

		self.assertEqual(
			exported.headers[-3:],
			["choice5_text", "choice5_image", "choice5_is_correct"],
		)
		self.assertEqual(exported[0][10::3], tuple(texts))

		# and the widened sheet reads back as the same five choices
		result = StatementResource().import_data(exported, raise_errors=True)

		self.assertFalse(result.has_errors())
		self.assertEqual(
			[choice.text for choice in Statement.objects.get().choices.all()], texts
		)

	def test_re_importing_replaces_the_choices_rather_than_adding_to_them(self):
		question = _multiple_choice("q")
		row = {
			"id": str(question.pk),
			"type": "MULTIPLE_CHOICE",
			"category": QuizCategory.GEOGRAPHY,
			"prompt_text": "νέα",
			"prompt_image": "",
			"prompt_audio": "",
			"listening": "",
			"part": "",
			"part_description": "",
			"order": "0",
			"choice1_text": "Γ",
			"choice1_image": "",
			"choice1_is_correct": "true",
		}

		self._import(StatementResource(), row)

		question.refresh_from_db()
		self.assertEqual([c.text for c in question.choices.all()], ["Γ"])

	def test_drag_and_drop_round_trip(self):
		row = {
			"id": "",
			"category": QuizCategory.GEOGRAPHY,
			"left_title": "Ποταμοί",
			"right_title": "Λίμνες",
			"left_values": "Αλιάκμονας, Πηνειός",
			"right_values": "Κερκίνη",
		}
		self._import(DragAndDropResource(), row)

		exported = DragAndDropResource().export(queryset=DragAndDrop.objects.all())
		self.assertEqual(
			list(exported[0]),
			[
				DragAndDrop.objects.get().pk,
				QuizCategory.GEOGRAPHY,
				"Ποταμοί",
				"Λίμνες",
				"Αλιάκμονας, Πηνειός",
				"Κερκίνη",
			],
		)

	def test_matching_round_trip(self):
		row = {
			"id": "",
			"category": QuizCategory.GEOGRAPHY,
			"left_title": "Α",
			"right_title": "Β",
			"items": "α1_β1 | α2_β2",
		}
		self._import(MatchingResource(), row)

		question = Matching.objects.get()
		self.assertEqual(
			[(p.left_text, p.right_text) for p in question.pairs.all()],
			[("α1", "β1"), ("α2", "β2")],
		)

		exported = MatchingResource().export(queryset=Matching.objects.all())
		self.assertEqual(exported[0][4], "α1_β1 | α2_β2")

		# A sheet written before the column existed says nothing about the right
		# column, which means it runs parallel to the left.
		self.assertEqual(
			[(pair.order, pair.right_order) for pair in question.pairs.all()],
			[(0, 0), (1, 1)],
		)

	def test_a_shuffled_right_column_survives_export_and_re_import(self):
		"""``right_order`` is the whole reason the right column is ordered on its
		own; a round trip that flattened it would put the answers back in line
		with the questions."""
		question = Matching.objects.create(left_title="Α", right_title="Β")
		MatchPair.objects.create(
			question=question, left_text="α1", right_text="β1", order=0, right_order=1
		)
		MatchPair.objects.create(
			question=question, left_text="α2", right_text="β2", order=1, right_order=0
		)

		exported = MatchingResource().export(queryset=Matching.objects.all())
		self.assertEqual(exported[0][5], "1,0")

		result = MatchingResource().import_data(exported, raise_errors=True)

		self.assertFalse(result.has_errors())
		self.assertEqual(
			[
				(pair.left_text, pair.right_text, pair.order, pair.right_order)
				for pair in Matching.objects.get().pairs.all()
			],
			[("α1", "β1", 0, 1), ("α2", "β2", 1, 0)],
		)

	def test_rejects_a_right_order_that_does_not_cover_every_pair(self):
		"""A half-filled column would otherwise place the rest by accident."""
		from import_export.exceptions import ImportError as ImportFailed

		row = {
			"id": "",
			"category": QuizCategory.GEOGRAPHY,
			"left_title": "Α",
			"right_title": "Β",
			"items": "α1_β1 | α2_β2",
			"right_order": "1",
		}

		with self.assertRaises(ImportFailed):
			self._import(MatchingResource(), row)

		self.assertFalse(Matching.objects.exists())

	def test_a_malformed_cell_leaves_the_question_as_it_was(self):
		"""``save_content`` runs after the question is saved and its old pairs
		deleted, so a cell that first failed there would empty the question
		whenever there is no transaction to roll back."""
		from import_export.exceptions import ImportError as ImportFailed

		question = Matching.objects.create(left_title="Α", right_title="Β")
		MatchPair.objects.create(
			question=question, left_text="α1", right_text="β1", order=0
		)
		row = {
			"id": str(question.pk),
			"category": QuizCategory.GEOGRAPHY,
			"left_title": "νέο",
			"right_title": "νέο",
			# no separator between the two sides
			"items": "α1β1",
		}

		with self.assertRaises(ImportFailed):
			self._import(MatchingResource(), row, use_transactions=False)

		self.assertEqual(
			[(pair.left_text, pair.right_text) for pair in question.pairs.all()],
			[("α1", "β1")],
		)
		self.assertEqual(Matching.objects.get().left_title, "Α")

	def test_open_ended_round_trip(self):
		row = {
			"id": "",
			"category": QuizCategory.GEOGRAPHY,
			"prompt_text": "Ποιος ποταμός;",
			"prompt_image": "",
			"texts": "Αλιάκμονας|Αλιακμων, Αξιός",
			"min_correct_answers": "2",
		}
		self._import(OpenEndedResource(), row)

		question = OpenEnded.objects.get()
		self.assertEqual(
			[
				[a.text for a in answer.alternatives.all()]
				for answer in question.answers.all()
			],
			[["Αλιάκμονας", "Αλιακμων"], ["Αξιός"]],
		)

		exported = OpenEndedResource().export(queryset=OpenEnded.objects.all())
		self.assertEqual(exported[0][4], "Αλιάκμονας|Αλιακμων, Αξιός")


class CategorySamplingTests(TestCase):
	"""The training page sends its category multi-select as one comma-separated
	value, so sampling has to honour every code in it."""

	def setUp(self):
		self.statements = {
			code: _multiple_choice(code, category_id=code)
			for code in (
				QuizCategory.GEOGRAPHY,
				QuizCategory.CIVICS,
				QuizCategory.HISTORY,
			)
		}

	def _sampled_categories(self, category):
		sampled = QuizService.get_by_category(category=category, amount=50)
		return {item["category"] for item in sampled}

	def test_a_single_category_is_honoured(self):
		self.assertEqual(
			self._sampled_categories(QuizCategory.GEOGRAPHY), {QuizCategory.GEOGRAPHY}
		)

	def test_several_categories_are_honoured(self):
		self.assertEqual(
			self._sampled_categories(f"{QuizCategory.GEOGRAPHY},{QuizCategory.CIVICS}"),
			{QuizCategory.GEOGRAPHY, QuizCategory.CIVICS},
		)

	def test_no_category_means_every_category(self):
		self.assertEqual(
			self._sampled_categories(""),
			{QuizCategory.GEOGRAPHY, QuizCategory.CIVICS, QuizCategory.HISTORY},
		)


class CategoryNameTests(TestCase):
	def setUp(self):
		QuizCategory.objects.filter(code=QuizCategory.GEOGRAPHY).update(
			name_el="Γεωγραφία"
		)

	def test_categories_are_labelled_in_greek(self):
		self.assertEqual(
			QuizService.category_labels()[QuizCategory.GEOGRAPHY], "Γεωγραφία"
		)

	def test_the_english_name_stands_in_for_a_missing_translation(self):
		QuizCategory.objects.filter(code=QuizCategory.CIVICS).update(name_el="")

		labels = QuizService.category_labels()
		self.assertEqual(labels[QuizCategory.CIVICS], "Civics")

	def test_options_carry_the_greek_name_as_their_label(self):
		options = {
			option["value"]: option["label"] for option in QuizService.categories()
		}

		self.assertEqual(options[QuizCategory.GEOGRAPHY], "Γεωγραφία")


class ListeningAdminInlineTests(TestCase):
	"""The admin saves a group before its inlines, so the formset — not
	``Listening.full_clean()`` — is what validates the shape on admin saves."""

	def setUp(self):
		self.asset = QuizAsset.objects.create(
			title="clip", audio=ContentFile(b"audio-bytes", name="clip.mp3")
		)
		self.group = Listening.objects.create(audio=self.asset)
		self.part_a = ListeningPart.objects.create(listening=self.group)
		self.part_b = ListeningPart.objects.create(listening=self.group)

	@staticmethod
	def question_fields(index, type_, position):
		"""The fields the questions inline posts for one question.

		Choices are not among them: they are rows on the statement, and Django
		has no inlines inside inlines, so they are edited on the statement's own
		page.
		"""
		return {
			f"questions-{index}-part_position": str(position) if position else "",
			f"questions-{index}-order": str(index),
			f"questions-{index}-type": type_,
			f"questions-{index}-prompt_text": "question",
			f"questions-{index}-is_active": "on",
		}

	def _formset(self, *types, with_parts=True):
		FormSet = inlineformset_factory(
			Listening,
			Statement,
			form=ListeningQuestionForm,
			formset=ListeningQuestionFormSet,
			fields=ListeningQuestionForm.Meta.fields,
			extra=0,
		)
		data = {
			"questions-TOTAL_FORMS": str(len(types)),
			"questions-INITIAL_FORMS": "0",
			"questions-MIN_NUM_FORMS": "0",
			"questions-MAX_NUM_FORMS": "1000",
		}
		for index, type_ in enumerate(types):
			# The true/false question goes in the first part, the rest in the second.
			position = 1 if type_ == Statement.StatementType.TRUE_FALSE else 2
			data.update(
				self.question_fields(index, type_, position if with_parts else None)
			)
		return FormSet(data, instance=self.group, prefix="questions")

	def test_accepts_one_true_false_plus_multiple_choice(self):
		formset = self._formset(
			Statement.StatementType.TRUE_FALSE,
			Statement.StatementType.MULTIPLE_CHOICE,
			Statement.StatementType.MULTIPLE_CHOICE,
		)

		self.assertTrue(formset.is_valid(), formset.errors or formset.non_form_errors())

	def test_rejects_two_true_false_questions(self):
		formset = self._formset(
			Statement.StatementType.TRUE_FALSE,
			Statement.StatementType.TRUE_FALSE,
			Statement.StatementType.MULTIPLE_CHOICE,
		)

		self.assertFalse(formset.is_valid())

	def test_rejects_a_group_with_no_true_false_question(self):
		formset = self._formset(Statement.StatementType.MULTIPLE_CHOICE)

		self.assertFalse(formset.is_valid())

	def test_rejects_a_true_false_question_on_its_own(self):
		formset = self._formset(Statement.StatementType.TRUE_FALSE)

		self.assertFalse(formset.is_valid())

	def test_rejects_a_question_without_a_part(self):
		formset = self._formset(
			Statement.StatementType.TRUE_FALSE,
			Statement.StatementType.MULTIPLE_CHOICE,
			with_parts=False,
		)

		self.assertFalse(formset.is_valid())


class ListeningChoicesSummaryTests(TestCase):
	"""Choices are rows on the statement, and Django has no inlines inside
	inlines, so the questions inline lists them read-only and links to the page
	where they are edited."""

	@staticmethod
	def _summary(question):
		return ListeningQuestionInline(Listening, site).choices_summary(question)

	def test_the_choices_are_listed_with_a_link_to_the_statement(self):
		question = _multiple_choice("q")

		html = self._summary(question)

		self.assertIn("A", html)
		self.assertIn(reverse("admin:quiz_statement_change", args=[question.pk]), html)

	@override_settings(ROOT_URLCONF=ALT_ADMIN_URLCONF.__name__)
	def test_the_link_follows_where_the_admin_is_mounted(self):
		question = _multiple_choice("q")

		html = self._summary(question)

		self.assertIn(f"/backoffice/quiz/statement/{question.pk}/change/", html)

	def test_an_unsaved_question_says_to_save_it_first(self):
		self.assertIn("Save the question first", self._summary(Statement()))


class ListeningAdminSaveTests(TestCase):
	"""``ListeningAdmin.save_formset`` is what turns the position a question picked
	into its ``part`` FK, which is what lets both be created in one save."""

	def setUp(self):
		self.asset = QuizAsset.objects.create(
			title="clip", audio=ContentFile(b"audio-bytes", name="clip.mp3")
		)
		self.model_admin = ListeningAdmin(Listening, site)
		self.request = RequestFactory().post("/")
		# ``save_formset`` may warn through the messages framework. Cookie storage
		# needs no session middleware.
		self.request._messages = CookieStorage(self.request)

	def _save(self, group, formset):
		self.model_admin.save_formset(
			self.request, SimpleNamespace(instance=group), formset, change=False
		)

	def _parts_formset(self, group, descriptions):
		FormSet = inlineformset_factory(
			Listening, ListeningPart, fields=ListeningPartInline.fields, extra=0
		)
		data = {
			"parts-TOTAL_FORMS": str(len(descriptions)),
			"parts-INITIAL_FORMS": "0",
			"parts-MIN_NUM_FORMS": "0",
			"parts-MAX_NUM_FORMS": "1000",
		}
		for index, description in enumerate(descriptions):
			data[f"parts-{index}-description"] = description
		formset = FormSet(data, instance=group, prefix="parts")
		self.assertTrue(formset.is_valid(), formset.errors)
		return formset

	def _questions_formset(self, group, positions_by_type):
		FormSet = inlineformset_factory(
			Listening,
			Statement,
			form=ListeningQuestionForm,
			formset=ListeningQuestionFormSet,
			fields=ListeningQuestionForm.Meta.fields,
			extra=0,
		)
		data = {
			"questions-TOTAL_FORMS": str(len(positions_by_type)),
			"questions-INITIAL_FORMS": "0",
			"questions-MIN_NUM_FORMS": "0",
			"questions-MAX_NUM_FORMS": "1000",
		}
		for index, (type_, position) in enumerate(positions_by_type):
			data.update(
				ListeningAdminInlineTests.question_fields(index, type_, position)
			)
		formset = FormSet(data, instance=group, prefix="questions")
		self.assertTrue(formset.is_valid(), formset.errors or formset.non_form_errors())
		return formset

	def test_parts_and_their_questions_are_created_in_one_save(self):
		group = Listening.objects.create(audio=self.asset)

		self._save(
			group, self._parts_formset(group, ["Μέρος Α intro", "Μέρος Β intro"])
		)
		self._save(
			group,
			self._questions_formset(
				group,
				[
					(Statement.StatementType.TRUE_FALSE, 1),
					(Statement.StatementType.MULTIPLE_CHOICE, 2),
					(Statement.StatementType.MULTIPLE_CHOICE, 2),
				],
			),
		)

		first, second = group.parts.all()
		self.assertEqual(first.description, "Μέρος Α intro")
		self.assertEqual(
			[question.type for question in first.questions.all()], ["TRUE_FALSE"]
		)
		self.assertEqual(second.questions.count(), 2)

	def test_a_position_with_no_part_grows_one(self):
		"""Better an empty part to fill in than a question in no part at all."""
		group = Listening.objects.create(audio=self.asset)

		self._save(group, self._parts_formset(group, ["only part"]))
		self._save(
			group,
			self._questions_formset(
				group,
				[
					(Statement.StatementType.TRUE_FALSE, 1),
					(Statement.StatementType.MULTIPLE_CHOICE, 2),
				],
			),
		)

		self.assertEqual(group.parts.count(), 2)
		second = group.parts.last()
		self.assertEqual(second.description, "")
		self.assertEqual(second.questions.count(), 1)

	def test_the_add_page_creates_a_whole_listening_question_in_one_post(self):
		"""The end-to-end version: clip, parts and questions in a single POST to
		the admin add page, which is what a part being pk-less used to block."""
		admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(admin_user)

		add_page = self.client.get(reverse("admin:quiz_listening_add"))
		self.assertEqual(add_page.status_code, 200)

		payload = {
			"is_active": "on",
			"audio": str(self.asset.pk),
			"max_plays": "2",
			"transcript": "",
			"parts-TOTAL_FORMS": "2",
			"parts-INITIAL_FORMS": "0",
			"parts-MIN_NUM_FORMS": "0",
			"parts-MAX_NUM_FORMS": "1000",
			"parts-0-description": "Μέρος Α intro",
			"parts-1-description": "Μέρος Β intro",
			"questions-TOTAL_FORMS": "2",
			"questions-INITIAL_FORMS": "0",
			"questions-MIN_NUM_FORMS": "0",
			"questions-MAX_NUM_FORMS": "1000",
		}
		payload.update(
			ListeningAdminInlineTests.question_fields(
				0, Statement.StatementType.TRUE_FALSE, 1
			)
		)
		payload.update(
			ListeningAdminInlineTests.question_fields(
				1, Statement.StatementType.MULTIPLE_CHOICE, 2
			)
		)

		response = self.client.post(reverse("admin:quiz_listening_add"), payload)

		# A 200 here means the form came back with errors instead of saving.
		self.assertEqual(response.status_code, 302)
		group = Listening.objects.get()
		first, second = group.parts.all()
		self.assertEqual(
			[first.description, second.description], ["Μέρος Α intro", "Μέρος Β intro"]
		)
		self.assertEqual(first.questions.get().type, "TRUE_FALSE")
		self.assertEqual(second.questions.get().type, "MULTIPLE_CHOICE")

		change_page = self.client.get(
			reverse("admin:quiz_listening_change", args=[group.pk])
		)
		self.assertEqual(change_page.status_code, 200)

	def test_the_position_of_an_existing_question_is_prefilled(self):
		group = Listening.objects.create(audio=self.asset)
		ListeningPart.objects.create(listening=group)
		part_b = ListeningPart.objects.create(listening=group)
		question = _multiple_choice("question", listening=group, part=part_b)

		form = ListeningQuestionForm(instance=question)

		self.assertEqual(form.fields["part_position"].initial, 2)


class FixedCategoryAdminTests(TestCase):
	"""Quiz types that only ever sit in one category don't ask for it: the admin
	leaves the picker off the page and fills the value in itself."""

	def setUp(self):
		self.asset = QuizAsset.objects.create(
			title="clip", audio=ContentFile(b"audio-bytes", name="clip.mp3")
		)
		admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(admin_user)

	@staticmethod
	def _rendered_fields(model_admin):
		return flatten_fieldsets(model_admin.get_fieldsets(None))

	def test_the_listening_page_has_no_category_picker(self):
		self.assertNotIn(
			"category", self._rendered_fields(ListeningAdmin(Listening, site))
		)
		self.assertNotIn("category", ListeningQuestionInline.fields)

	def test_the_map_pointer_page_has_no_category_picker(self):
		self.assertNotIn(
			"category", self._rendered_fields(MapPointerAdmin(MapPointer, site))
		)

	def test_a_clip_and_its_questions_are_filed_under_listening(self):
		payload = {
			"is_active": "on",
			"audio": str(self.asset.pk),
			"max_plays": "2",
			"transcript": "",
			"parts-TOTAL_FORMS": "2",
			"parts-INITIAL_FORMS": "0",
			"parts-MIN_NUM_FORMS": "0",
			"parts-MAX_NUM_FORMS": "1000",
			"parts-0-description": "",
			"parts-1-description": "",
			"questions-TOTAL_FORMS": "2",
			"questions-INITIAL_FORMS": "0",
			"questions-MIN_NUM_FORMS": "0",
			"questions-MAX_NUM_FORMS": "1000",
		}
		payload.update(
			ListeningAdminInlineTests.question_fields(
				0, Statement.StatementType.TRUE_FALSE, 1
			)
		)
		payload.update(
			ListeningAdminInlineTests.question_fields(
				1, Statement.StatementType.MULTIPLE_CHOICE, 2
			)
		)

		response = self.client.post(reverse("admin:quiz_listening_add"), payload)

		self.assertEqual(response.status_code, 302)
		group = Listening.objects.get()
		self.assertEqual(group.category_id, QuizCategory.LISTENING)
		self.assertEqual(
			set(group.questions.values_list("category_id", flat=True)),
			{QuizCategory.LISTENING},
		)

	def test_a_map_question_is_filed_under_geography(self):
		level = MapPointer.MapLevel.PREFECTURE_UNIT
		area = MapArea.objects.filter(level=level).first()

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"test_number": "0",
				"question_number": "0",
				"is_active": "on",
				"level": str(int(level)),
				"show_answers": "on",
				"min_correct_answers": "1",
				"prompt_text": "Πού βρίσκεται;",
				"answers-TOTAL_FORMS": "1",
				"answers-INITIAL_FORMS": "0",
				"answers-MIN_NUM_FORMS": "0",
				"answers-MAX_NUM_FORMS": "1000",
				"answers-0-order": "0",
				"answers-0-alternatives_text": "Αλιάκμονας",
				"answers-0-areas": [str(area.pk)],
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(MapPointer.objects.get().category_id, QuizCategory.GEOGRAPHY)


class MapPointerAdminTests(TestCase):
	"""The area picker is a real autocomplete against ``MapArea`` now — the
	hand-written level picker, its schema enum rebuilt in JavaScript and the view
	that dumped every area name into the page are all gone."""

	LEVEL = MapPointer.MapLevel.PREFECTURE_UNIT

	def setUp(self):
		self.admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(self.admin_user)

	def _autocomplete(self, term):
		return self.client.get(
			reverse("admin:autocomplete"),
			{
				"app_label": "quiz",
				"model_name": "mappointeranswerarea",
				"field_name": "area",
				"term": term,
			},
		)

	def test_searching_returns_matching_area_names(self):
		response = self._autocomplete("ΙΩΑΝΝ")

		self.assertEqual(response.status_code, 200)
		self.assertIn(
			"ΙΩΑΝΝΙΝΩΝ", [result["text"] for result in response.json()["results"]]
		)

	def test_searching_ignores_accents_through_the_folded_name(self):
		"""Greek is routinely typed without its tonos, so both the stored name and
		the typed query go through the same folding — which also settles the
		final sigma, so "Άθως" and "αθως" meet at "αθωσ"."""
		from quiz.models import fold_for_search

		self.assertEqual(fold_for_search("Άθως"), fold_for_search("αθως"))
		self.assertTrue(
			MapArea.objects.filter(
				level=MapPointer.MapLevel.MUNICIPALITY,
				search_name=fold_for_search("αθως"),
			).exists()
		)

	def test_the_options_are_closed_to_non_staff(self):
		self.client.logout()

		response = self._autocomplete("Ιωάνν")

		self.assertNotEqual(response.status_code, 200)

	def test_the_admin_saves_an_answer_with_several_picked_areas(self):
		areas = list(MapArea.objects.filter(level=self.LEVEL)[:3])

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"test_number": "0",
				"question_number": "0",
				"is_active": "on",
				"level": str(int(self.LEVEL)),
				"show_answers": "on",
				"min_correct_answers": "1",
				"prompt_text": "Ποιον νομό διασχίζει ο Αλιάκμονας;",
				"answers-TOTAL_FORMS": "1",
				"answers-INITIAL_FORMS": "0",
				"answers-MIN_NUM_FORMS": "0",
				"answers-MAX_NUM_FORMS": "1000",
				"answers-0-order": "0",
				"answers-0-alternatives_text": "Αλιάκμονας\nΑλιακμων",
				"answers-0-areas": [str(area.pk) for area in areas],
			},
		)

		self.assertEqual(response.status_code, 302)
		question = MapPointer.objects.get()
		answer = question.answers.get()
		self.assertEqual(
			[alt.text for alt in answer.alternatives.all()],
			["Αλιάκμονας", "Αλιακμων"],
		)
		self.assertEqual(
			[link.area.name for link in answer.area_links.all()],
			[area.name for area in areas],
		)

	def _add_payload(self, *answers, min_correct_answers=1, level=None):
		"""The fields the add page posts for a question and one row per answer,
		each given the areas it accepts."""
		payload = {
			"test_number": "0",
			"question_number": "0",
			"is_active": "on",
			"level": str(int(self.LEVEL if level is None else level)),
			"show_answers": "on",
			"min_correct_answers": str(min_correct_answers),
			"prompt_text": "Ποιον νομό διασχίζει ο Αλιάκμονας;",
			"answers-TOTAL_FORMS": str(len(answers)),
			"answers-INITIAL_FORMS": "0",
			"answers-MIN_NUM_FORMS": "0",
			"answers-MAX_NUM_FORMS": "1000",
		}
		for index, areas in enumerate(answers):
			payload[f"answers-{index}-order"] = str(index)
			payload[f"answers-{index}-alternatives_text"] = "Αλιάκμονας"
			payload[f"answers-{index}-areas"] = [str(area.pk) for area in areas]
		return payload

	def test_rejects_an_area_from_another_level(self):
		"""The level decides which areas the client draws, so an answer pointing
		at one from another level could never be matched — and the question would
		fail to validate ever after on the link that was let in. The model rule
		cannot catch it: the area links are written after the question is saved.
		"""
		other_level = MapArea.objects.exclude(level=self.LEVEL).first()

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"), self._add_payload([other_level])
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "are not level-")
		self.assertFalse(MapPointer.objects.exists())

	def test_rejects_an_answer_with_no_area(self):
		response = self.client.post(
			reverse("admin:quiz_mappointer_add"), self._add_payload([])
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(MapPointer.objects.exists())

	def test_rejects_more_required_answers_than_are_being_saved(self):
		areas = list(MapArea.objects.filter(level=self.LEVEL)[:2])

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			self._add_payload([areas[0]], [areas[1]], min_correct_answers=9),
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(MapPointer.objects.exists())

	def test_the_area_changelist_counts_answers_in_one_query(self):
		"""``answer_count`` used to be a COUNT per row, on a page of 100 rows."""
		from django.db import connection
		from django.test.utils import CaptureQueriesContext

		with CaptureQueriesContext(connection) as captured:
			response = self.client.get(reverse("admin:quiz_maparea_changelist"))

		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(response.context["cl"].result_count, 100)
		counting = [
			query
			for query in captured.captured_queries
			if "quiz_mappointeranswerarea" in query["sql"]
		]
		# The page's own query, plus the two counts the changelist takes of it.
		self.assertLessEqual(len(counting), 3)

	def test_map_areas_are_read_only_in_the_admin(self):
		from quiz.admin import MapAreaAdmin

		model_admin = MapAreaAdmin(MapArea, site)

		self.assertFalse(model_admin.has_add_permission(None))
		self.assertFalse(model_admin.has_change_permission(None))
		self.assertFalse(model_admin.has_delete_permission(None))


class OpenEndedAdminTests(TestCase):
	"""``min_correct_answers`` counts answers, and the admin writes those rows
	after the question itself — so on a create the model rule has nothing to
	count and waves any number through."""

	def setUp(self):
		admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(admin_user)

	@staticmethod
	def _add_payload(*answers, min_correct_answers=1):
		payload = {
			"category": QuizCategory.GEOGRAPHY,
			"test_number": "0",
			"question_number": "0",
			"is_active": "on",
			"min_correct_answers": str(min_correct_answers),
			"prompt_text": "Ποια είναι η πρωτεύουσα της Ελλάδας;",
			"answers-TOTAL_FORMS": str(len(answers)),
			"answers-INITIAL_FORMS": "0",
			"answers-MIN_NUM_FORMS": "0",
			"answers-MAX_NUM_FORMS": "1000",
		}
		for index, alternatives in enumerate(answers):
			payload[f"answers-{index}-order"] = str(index)
			payload[f"answers-{index}-alternatives_text"] = alternatives
		return payload

	def test_the_add_page_saves_a_question_and_its_answers(self):
		response = self.client.post(
			reverse("admin:quiz_openended_add"), self._add_payload("Αθήνα\nΑθηνα")
		)

		self.assertEqual(response.status_code, 302)
		answer = OpenEnded.objects.get().answers.get()
		self.assertEqual(
			[alt.text for alt in answer.alternatives.all()], ["Αθήνα", "Αθηνα"]
		)

	def test_rejects_more_required_answers_than_are_being_saved(self):
		"""Nine of one answer is unreachable, and the row it saved could not be
		edited again: the change form has the answers to count and rejects it."""
		response = self.client.post(
			reverse("admin:quiz_openended_add"),
			self._add_payload("Αθήνα", min_correct_answers=9),
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(OpenEnded.objects.exists())

	def test_a_question_may_be_created_before_its_answers(self):
		"""The model rule allows an answerless question, so the formset must too:
		the answers can be added on a second pass."""
		response = self.client.post(
			reverse("admin:quiz_openended_add"), self._add_payload()
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(OpenEnded.objects.get().min_correct_answers, 1)


class MatchingAdminPreviewTests(TestCase):
	"""The preview is the only place an author sees the two columns as the
	candidate will, so it has to sort them the way the serializer does."""

	def setUp(self):
		self.question = Matching.objects.create(left_title="Α", right_title="Β")
		MatchPair.objects.create(
			question=self.question,
			left_text="α1",
			right_text="β1",
			order=0,
			right_order=1,
		)
		MatchPair.objects.create(
			question=self.question,
			left_text="α2",
			right_text="β2",
			order=1,
			right_order=0,
		)

	@staticmethod
	def _column(html, list_type):
		"""The items of the rendered column numbered with *list_type*."""
		return html.split(f'type="{list_type}"')[1].split("</ol>")[0]

	def test_the_right_column_is_drawn_in_its_own_order(self):
		html = MatchingAdmin(Matching, site).answer_preview(self.question)

		right = self._column(html, "A")
		self.assertLess(right.index("β2"), right.index("β1"))

	def test_the_left_column_keeps_its_own_order(self):
		html = MatchingAdmin(Matching, site).answer_preview(self.question)

		left = self._column(html, "1")
		self.assertLess(left.index("α1"), left.index("α2"))

	def test_the_pairings_are_listed_whatever_the_columns_do(self):
		html = MatchingAdmin(Matching, site).answer_preview(self.question)

		self.assertIn("α1 → β1", html)
		self.assertIn("α2 → β2", html)


class AdminSmokeTests(TestCase):
	"""Load every quiz admin page with a populated row.

	The list pages render each question's answer, and those previews were all
	rewritten to read rows instead of JSON. They are the kind of code nothing
	else exercises until someone opens the page in production — which is how a
	``format_html`` call with no arguments got this far.
	"""

	def setUp(self):
		admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(admin_user)

		self.asset = QuizAsset.objects.create(
			title="pic", image=ContentFile(b"bytes", name="pic.png")
		)

		_multiple_choice("Ποια είναι;")

		drag = DragAndDrop.objects.create(left_title="Ποταμοί", right_title="Λίμνες")
		DragAndDropValue.objects.create(
			question=drag, side=DragAndDropValue.Side.LEFT, text="Αλιάκμονας"
		)
		DragAndDropValue.objects.create(
			question=drag, side=DragAndDropValue.Side.RIGHT, text="Κερκίνη"
		)

		matching = Matching.objects.create(left_title="Α", right_title="Β")
		MatchPair.objects.create(
			question=matching, left_text="α1", right_text="β1", order=0
		)
		# An image-only pair, which is how the null texts in the real data arise.
		MatchPair.objects.create(
			question=matching, left_image=self.asset, right_text="β2", order=1
		)

		blanks = FillInTheBlank.objects.create(show_answers_as_choices=True)
		FillInTheBlankText.objects.create(
			question=blanks, text="Η Κως συνορεύει με <{{την Τουρκία}}*>"
		)
		FillInTheBlankExtraChoice.objects.create(question=blanks, text="τη Βουλγαρία")

		open_ended = OpenEnded.objects.create(prompt_text="Ποιος;")
		answer = OpenEndedAnswer.objects.create(question=open_ended, order=0)
		OpenEndedAlternative.objects.create(answer=answer, text="Αλιάκμονας")

		pointer = MapPointer.objects.create(level=1, prompt_text="Πού;")
		pointer_answer = MapPointerAnswer.objects.create(question=pointer, order=0)
		MapPointerAlternative.objects.create(answer=pointer_answer, text="Αλιάκμονας")
		MapPointerAnswerArea.objects.create(
			answer=pointer_answer, area=MapArea.objects.filter(level=1).first()
		)

		listening = Listening.objects.create(
			audio=QuizAsset.objects.create(
				title="clip", audio=ContentFile(b"audio", name="clip.mp3")
			)
		)
		part = ListeningPart.objects.create(listening=listening)
		_true_false(("first", True), listening=listening, part=part)
		_multiple_choice("q", listening=listening, part=part)

	MODELS = [
		"statement",
		"draganddrop",
		"matching",
		"fillintheblank",
		"openended",
		"mappointer",
		"listening",
		"maparea",
		"quizasset",
		"quizcategory",
	]

	def test_every_changelist_renders(self):
		for model in self.MODELS:
			with self.subTest(model=model):
				response = self.client.get(reverse(f"admin:quiz_{model}_changelist"))
				self.assertEqual(response.status_code, 200)

	def test_every_change_page_renders(self):
		# ``maparea`` is read-only and ``quizcategory`` has nothing to show here.
		for model in self.MODELS:
			with self.subTest(model=model):
				from django.apps import apps as django_apps

				instance = django_apps.get_model("quiz", model).objects.first()
				if instance is None:
					continue
				response = self.client.get(
					reverse(f"admin:quiz_{model}_change", args=[instance.pk])
				)
				self.assertEqual(response.status_code, 200)

	def test_every_add_page_renders(self):
		for model in self.MODELS:
			if model == "maparea":
				continue  # generated by sync_map_areas, never added by hand
			with self.subTest(model=model):
				response = self.client.get(reverse(f"admin:quiz_{model}_add"))
				self.assertEqual(response.status_code, 200)


class DerivedBlankRowsTests(TestCase):
	"""The parse tree is rows, derived from the authored sentence on save.

	The sentence stays the source of truth; these rows are its parsed form, which
	is what makes the content queryable and keeps the regex out of the request.
	"""

	def setUp(self):
		self.question = FillInTheBlank.objects.create(show_answers_as_choices=True)

	def _sentence(self, text, order=0):
		return FillInTheBlankText.objects.create(
			question=self.question, text=text, order=order
		)

	def test_saving_a_sentence_derives_its_parts(self):
		sentence = self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>")

		self.assertEqual(
			[(part.text, part.is_blank) for part in sentence.parts.all()],
			[("Η Κως συνορεύει με ", False), ("", True)],
		)
		blank = sentence.parts.get(is_blank=True)
		self.assertEqual(
			[(choice.text, choice.is_correct) for choice in blank.choices.all()],
			[("την Τουρκία", True)],
		)

	def test_editing_a_sentence_replaces_its_parts(self):
		"""Wholesale, not incremental — anything no longer in the string is gone."""
		sentence = self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>")
		before = set(sentence.parts.values_list("pk", flat=True))

		sentence.text = "Το <{{1821}}*, {{1822}}> ήταν"
		sentence.save()

		self.assertFalse(
			FillInTheBlankPart.objects.filter(pk__in=before).exists(),
			"the old parts should have been replaced",
		)
		self.assertEqual(
			[choice.text for choice in FillInTheBlankChoice.objects.all()],
			["1821", "1822"],
		)

	def test_has_multiple_choices_is_stored_and_queryable(self):
		"""It used to be re-derived on every read; now it is a column."""
		self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>", order=0)
		self._sentence("Το <{{1821}}*, {{1822}}> ήταν", order=1)

		self.assertEqual(
			FillInTheBlankText.objects.filter(has_multiple_choices=True).count(), 1
		)
		self.assertTrue(self.question.has_multiple_choices())

	def test_the_content_is_now_searchable(self):
		"""The point of the exercise: a blank's choices are rows, so they can be
		queried instead of hiding inside a string."""
		self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>")

		self.assertTrue(
			FillInTheBlank.objects.filter(
				texts__parts__choices__text="την Τουρκία"
			).exists()
		)

	def test_deleting_a_sentence_deletes_its_parts_and_choices(self):
		sentence = self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>")

		sentence.delete()

		self.assertEqual(FillInTheBlankPart.objects.count(), 0)
		self.assertEqual(FillInTheBlankChoice.objects.count(), 0)

	def test_malformed_markup_never_reaches_the_table(self):
		with self.assertRaises(ValidationError):
			self._sentence("no blank here")

		self.assertEqual(FillInTheBlankText.objects.count(), 0)
		self.assertEqual(FillInTheBlankPart.objects.count(), 0)

	def test_rebuild_parts_recovers_from_a_write_that_skipped_save(self):
		"""``bulk_create`` and friends go around ``save()``, so the rebuild has to
		be callable by hand — the importer relies on this."""
		sentence = self._sentence("Η Κως συνορεύει με <{{την Τουρκία}}*>")
		sentence.parts.all().delete()

		self.question.rebuild_parts()

		self.assertEqual(sentence.parts.count(), 2)


class BlankParserAgreementTests(TestCase):
	"""Migration 0022 carries its own frozen copy of the blank parser, because a
	data migration that calls live code breaks on a fresh database the moment that
	code changes. This is what stops the two drifting apart unnoticed."""

	VALID = [
		"Η Κως συνορεύει με <{{την Τουρκία}}*>",
		"Το <{{1821}}*, {{1822}}> είναι η χρονιά",
		"<{{Α}}*> στην αρχή",
		"Δύο <{{ένα}}*> κενά <{{δύο}}*> εδώ",
		"Το Διδυμότειχο συνορεύει με  <{{την Τουρκία}}*> ",
	]

	INVALID = [
		"χωρίς κενό",
		"Το <{{1821}}, {{1822}}> ήταν",
		"Το <χωρίς επιλογές> ήταν",
	]

	def test_the_two_parsers_agree_on_valid_sentences(self):
		question = FillInTheBlank.objects.create()
		for sentence in self.VALID:
			with self.subTest(sentence=sentence):
				live = FillInTheBlankText(question=question, text=sentence).parse()
				parts, has_multiple = backfill.parse_blank_text(sentence)

				self.assertEqual(parts, live["parts"])
				self.assertEqual(has_multiple, live["has_multiple_choices"])

	def test_the_frozen_parser_reports_rather_than_raises(self):
		"""The live model rejects bad markup; the migration must not, or one bad
		legacy row takes the whole deploy down."""
		question = FillInTheBlank.objects.create()
		for sentence in self.INVALID:
			with self.subTest(sentence=sentence):
				parts, has_multiple = backfill.parse_blank_text(sentence)
				self.assertIsNone(parts)
				self.assertFalse(has_multiple)

				with self.assertRaises(ValidationError):
					FillInTheBlankText(question=question, text=sentence).parse()
