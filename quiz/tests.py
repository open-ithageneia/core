from types import SimpleNamespace

import tablib
from django.contrib.admin.sites import site
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.utils import IntegrityError
from django.forms.models import inlineformset_factory
from django.test import RequestFactory, TestCase
from django.urls import reverse

from quiz.admin import (
	ListeningAdmin,
	ListeningPartInline,
	ListeningQuestionForm,
	ListeningQuestionFormSet,
	ListeningQuestionInline,
	MapPointerAdmin,
	StatementChoiceFormSet,
	StatementChoiceInline,
)
from importlib import import_module
from quiz.models import (
	DragAndDrop,
	DragAndDropValue,
	Listening,
	ListeningPart,
	MapArea,
	MapPointer,
	MapPointerAlternative,
	MapPointerAnswer,
	MapPointerAnswerArea,
	MatchPair,
	Matching,
	OpenEnded,
	OpenEndedAlternative,
	OpenEndedAnswer,
	QuizAsset,
	QuizCategory,
	Statement,
	StatementChoice,
)
from quiz.resources import MatchingResource, StatementResource
from quiz.serializers import (
	DragAndDropSerializer,
	ListeningSerializer,
	MapPointerSerializer,
	MatchingSerializer,
	OpenEndedSerializer,
	StatementSerializer,
)
from quiz.services import QuizService

# The migration owns the only copy of the legacy-shape parsers now. Its module
# name starts with a digit, so it can only be reached through importlib.
_0021 = import_module("quiz.migrations.0021_normalize_quiz_content")


def _true_false(*statements, **kwargs):
	"""A true/false statement with its choices, as rows."""
	statement = Statement.objects.create(
		type=Statement.StatementType.TRUE_FALSE, **kwargs
	)
	StatementChoice.objects.bulk_create(
		[
			StatementChoice(
				statement=statement, text=text, is_correct=is_correct, order=order
			)
			for order, (text, is_correct) in enumerate(statements)
		]
	)
	return statement


def _multiple_choice(prompt, **kwargs):
	statement = Statement.objects.create(
		type=Statement.StatementType.MULTIPLE_CHOICE, prompt_text=prompt, **kwargs
	)
	StatementChoice.objects.bulk_create(
		[
			StatementChoice(statement=statement, text="A", is_correct=True, order=0),
			StatementChoice(statement=statement, text="B", is_correct=False, order=1),
		]
	)
	return statement


def _areas(level, count):
	"""The first *count* areas of *level*, seeded by migration 0021."""
	return list(MapArea.objects.filter(level=int(level)).order_by("name")[:count])


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
		# The group itself has no content object of its own.
		self.assertNotIn("content", data)

	def test_a_question_carries_its_choices(self):
		data = ListeningSerializer(self.group).data

		self.assertEqual(
			data["parts"][0]["questions"][0]["content"]["choices"],
			[
				{"is_correct": True, "text": "first", "asset_url": None},
				{"is_correct": False, "text": "second", "asset_url": None},
			],
		)

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


class ContentShapeTests(TestCase):
	"""The shape each serializer emits is the contract the frontend is written
	against, so it is asserted literally rather than round-tripped."""

	def test_statement_content(self):
		asset = QuizAsset.objects.create(
			title="pic", image=ContentFile(b"img", name="pic.png")
		)
		statement = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE,
			prompt_text="Ποια είναι σωστή;",
			prompt_image=asset,
		)
		StatementChoice.objects.create(
			statement=statement, text="A", is_correct=True, order=0
		)
		StatementChoice.objects.create(
			statement=statement, image=asset, is_correct=False, order=1
		)

		content = StatementSerializer(statement).data["content"]

		self.assertEqual(content["prompt_text"], "Ποια είναι σωστή;")
		self.assertTrue(content["prompt_asset_url"].endswith(".png"))
		self.assertIsNone(content["prompt_audio_url"])
		self.assertEqual(content["choices"][0]["text"], "A")
		self.assertIsNone(content["choices"][0]["asset_url"])
		# A choice with only an image reports no text, as it always has.
		self.assertIsNone(content["choices"][1]["text"])
		self.assertTrue(content["choices"][1]["asset_url"].endswith(".png"))

	def test_an_absent_prompt_is_null_not_empty(self):
		"""``prompt_text`` is a ``blank=True`` column but the client has always
		been handed ``null`` when there is no prompt."""
		statement = _true_false(("x", True))

		self.assertIsNone(StatementSerializer(statement).data["content"]["prompt_text"])

	def test_drag_and_drop_content_is_two_columns(self):
		question = DragAndDrop.objects.create(
			left_title="Ποταμοί", right_title="Λίμνες"
		)
		DragAndDropValue.objects.bulk_create(
			[
				DragAndDropValue(
					question=question,
					side=DragAndDropValue.Side.LEFT,
					text="Αλιάκμονας",
					order=0,
				),
				DragAndDropValue(
					question=question,
					side=DragAndDropValue.Side.RIGHT,
					text="Κερκίνη",
					order=0,
				),
			]
		)

		self.assertEqual(
			DragAndDropSerializer(question).data["content"],
			[
				{"title": "Ποταμοί", "values": ["Αλιάκμονας"]},
				{"title": "Λίμνες", "values": ["Κερκίνη"]},
			],
		)

	def test_matching_ids_are_regenerated_from_the_pairs(self):
		"""``id``/``matched_id`` are not stored — the pair row is the pairing, and
		the numbering the client expects is rebuilt on the way out."""
		question = Matching.objects.create(left_title="A", right_title="B")
		MatchPair.objects.bulk_create(
			[
				MatchPair(question=question, left_text="l1", right_text="r1", order=0),
				MatchPair(question=question, left_text="l2", right_text="r2", order=1),
			]
		)

		columns = MatchingSerializer(question).data["content"]["columns"]

		self.assertEqual(
			[(i["id"], i["matched_id"]) for i in columns[0]["items"]], [(1, 3), (2, 4)]
		)
		self.assertEqual(
			[(i["id"], i["matched_id"]) for i in columns[1]["items"]], [(3, 1), (4, 2)]
		)

	def test_open_ended_texts_are_lists_of_alternatives(self):
		question = OpenEnded.objects.create(
			prompt_text="Ονομάστε δύο", min_correct_answers=1
		)
		answer = OpenEndedAnswer.objects.create(question=question, order=0)
		OpenEndedAlternative.objects.bulk_create(
			[
				OpenEndedAlternative(answer=answer, text="Αθήνα", order=0),
				OpenEndedAlternative(answer=answer, text="Αθηνα", order=1),
			]
		)

		self.assertEqual(
			OpenEndedSerializer(question).data["content"]["texts"],
			[["Αθήνα", "Αθηνα"]],
		)


class StatementChoiceTests(TestCase):
	def test_a_choice_needs_text_or_an_image(self):
		"""Enforced by the database now, not by the importer quietly skipping it."""
		statement = _true_false(("x", True))

		with self.assertRaises(IntegrityError):
			StatementChoice.objects.create(statement=statement, text="", order=5)

	def test_multiple_choice_needs_a_correct_choice(self):
		statement = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE
		)
		StatementChoice.objects.create(
			statement=statement, text="A", is_correct=False, order=0
		)

		with self.assertRaises(ValidationError):
			statement.full_clean()

	def test_a_question_being_created_is_not_judged_on_choices_it_cannot_have(self):
		"""The parent is saved before its inlines, so a brand new question has no
		choices yet — the formset is what gates that case."""
		Statement.objects.create(type=Statement.StatementType.MULTIPLE_CHOICE)

	def test_deleting_a_statement_deletes_its_choices(self):
		statement = _true_false(("x", True))
		statement.delete()

		self.assertFalse(StatementChoice.objects.exists())


class StatementChoiceFormSetTests(TestCase):
	"""Where the "needs a correct choice" rule is enforced on admin saves, since
	the model cannot see the choices at the time the parent is saved."""

	def _formset(self, statement, *choices):
		FormSet = inlineformset_factory(
			Statement,
			StatementChoice,
			formset=StatementChoiceFormSet,
			fields=StatementChoiceInline.fields,
			extra=0,
		)
		data = {
			"choices-TOTAL_FORMS": str(len(choices)),
			"choices-INITIAL_FORMS": "0",
			"choices-MIN_NUM_FORMS": "0",
			"choices-MAX_NUM_FORMS": "1000",
		}
		for index, (text, is_correct) in enumerate(choices):
			data[f"choices-{index}-order"] = str(index)
			data[f"choices-{index}-text"] = text
			if is_correct:
				data[f"choices-{index}-is_correct"] = "on"
		return FormSet(data, instance=statement, prefix="choices")

	def test_accepts_a_multiple_choice_question_with_a_correct_choice(self):
		statement = Statement(type=Statement.StatementType.MULTIPLE_CHOICE)
		formset = self._formset(statement, ("A", True), ("B", False))

		self.assertTrue(formset.is_valid(), formset.errors)

	def test_rejects_a_multiple_choice_question_with_no_correct_choice(self):
		statement = Statement(type=Statement.StatementType.MULTIPLE_CHOICE)
		formset = self._formset(statement, ("A", False), ("B", False))

		self.assertFalse(formset.is_valid())
		self.assertIn("at least one correct choice", str(formset.non_form_errors()))

	def test_a_question_with_no_choices_yet_is_allowed(self):
		"""Choices can be added on a second pass."""
		statement = Statement(type=Statement.StatementType.MULTIPLE_CHOICE)

		self.assertTrue(self._formset(statement).is_valid())


class CategorySamplingTests(TestCase):
	"""The training page sends its category multi-select as one comma-separated
	value, so sampling has to honour every code in it."""

	def setUp(self):
		for code in (
			QuizCategory.GEOGRAPHY,
			QuizCategory.CIVICS,
			QuizCategory.HISTORY,
		):
			_multiple_choice(f"{code} question", category_id=code)

	def _sampled_categories(self, category):
		return {
			item["category"]
			for item in QuizService.get_by_category(category=category, amount=50)
		}

	def test_a_single_category_is_honoured(self):
		self.assertEqual(
			self._sampled_categories(QuizCategory.GEOGRAPHY), {QuizCategory.GEOGRAPHY}
		)

	def test_several_categories_are_honoured(self):
		self.assertEqual(
			self._sampled_categories(
				f"{QuizCategory.GEOGRAPHY},{QuizCategory.HISTORY}"
			),
			{QuizCategory.GEOGRAPHY, QuizCategory.HISTORY},
		)

	def test_no_category_means_every_category(self):
		self.assertEqual(
			self._sampled_categories(""),
			{QuizCategory.GEOGRAPHY, QuizCategory.CIVICS, QuizCategory.HISTORY},
		)


class CategoryNameTests(TestCase):
	def setUp(self):
		self.geography = QuizCategory.objects.get(code=QuizCategory.GEOGRAPHY)

	def test_categories_are_labelled_in_greek(self):
		self.geography.name_el = "Γεωγραφία"
		self.geography.save()

		self.assertEqual(
			QuizService.category_labels()[QuizCategory.GEOGRAPHY], "Γεωγραφία"
		)

	def test_the_english_name_stands_in_for_a_missing_translation(self):
		self.geography.name_el = ""
		self.geography.save()

		self.assertEqual(
			QuizService.category_labels()[QuizCategory.GEOGRAPHY], self.geography.name
		)

	def test_options_carry_the_greek_name_as_their_label(self):
		self.geography.name_el = "Γεωγραφία"
		self.geography.save()

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

	def _formset(self, *types, with_parts=True):
		FormSet = inlineformset_factory(
			Listening,
			Statement,
			form=ListeningQuestionForm,
			formset=ListeningQuestionFormSet,
			fields=ListeningQuestionInline.fields,
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
				{
					f"questions-{index}-part_position": (
						str(position) if with_parts else ""
					),
					f"questions-{index}-order": str(index),
					f"questions-{index}-type": type_,
					f"questions-{index}-prompt_text": "question",
					f"questions-{index}-is_active": "on",
				}
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
		self.assertIn("exactly one True/False question", str(formset.non_form_errors()))

	def test_rejects_a_group_with_no_true_false_question(self):
		formset = self._formset(Statement.StatementType.MULTIPLE_CHOICE)

		self.assertFalse(formset.is_valid())
		self.assertIn("exactly one True/False question", str(formset.non_form_errors()))

	def test_rejects_a_true_false_question_on_its_own(self):
		formset = self._formset(Statement.StatementType.TRUE_FALSE)

		self.assertFalse(formset.is_valid())
		self.assertIn(
			"at least one multiple-choice question", str(formset.non_form_errors())
		)

	def test_rejects_a_question_without_a_part(self):
		"""A part-less question would never be shown, so it can't be saved."""
		formset = self._formset(
			Statement.StatementType.TRUE_FALSE,
			Statement.StatementType.MULTIPLE_CHOICE,
			with_parts=False,
		)

		self.assertFalse(formset.is_valid())
		self.assertIn("part_position", formset.errors[0])

	def test_choices_are_not_edited_on_the_inline(self):
		"""Django has no nested inlines, so a listening question's choices are
		edited on the question's own page — the inline links to it instead."""
		self.assertNotIn("choices", ListeningQuestionInline.fields)


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
			fields=ListeningQuestionInline.fields,
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
				{
					f"questions-{index}-part_position": str(position),
					f"questions-{index}-order": str(index),
					f"questions-{index}-type": type_,
					f"questions-{index}-prompt_text": "question",
					f"questions-{index}-is_active": "on",
				}
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

		response = self.client.post(
			reverse("admin:quiz_listening_add"),
			{
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
				"questions-0-part_position": "1",
				"questions-0-order": "0",
				"questions-0-type": Statement.StatementType.TRUE_FALSE,
				"questions-0-prompt_text": "σωστό ή λάθος",
				"questions-0-is_active": "on",
				"questions-1-part_position": "2",
				"questions-1-order": "0",
				"questions-1-type": Statement.StatementType.MULTIPLE_CHOICE,
				"questions-1-prompt_text": "επιλέξτε",
				"questions-1-is_active": "on",
			},
		)

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
		response = self.client.post(
			reverse("admin:quiz_listening_add"),
			{
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
				"questions-0-part_position": "1",
				"questions-0-order": "0",
				"questions-0-type": Statement.StatementType.TRUE_FALSE,
				"questions-0-prompt_text": "σωστό ή λάθος",
				"questions-0-is_active": "on",
				"questions-1-part_position": "2",
				"questions-1-order": "0",
				"questions-1-type": Statement.StatementType.MULTIPLE_CHOICE,
				"questions-1-prompt_text": "επιλέξτε",
				"questions-1-is_active": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		group = Listening.objects.get()
		self.assertEqual(group.category_id, QuizCategory.LISTENING)
		self.assertEqual(
			set(group.questions.values_list("category_id", flat=True)),
			{QuizCategory.LISTENING},
		)

	def test_a_map_question_is_filed_under_geography(self):
		level = MapPointer.MapLevel.PREFECTURE_UNIT
		area = _areas(level, 1)[0]

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"level": str(int(level)),
				"prompt_text": "Πού βρίσκεται;",
				"min_correct_answers": "1",
				"show_answers": "on",
				"test_number": "0",
				"question_number": "0",
				"is_active": "on",
				"answers-TOTAL_FORMS": "1",
				"answers-INITIAL_FORMS": "0",
				"answers-MIN_NUM_FORMS": "0",
				"answers-MAX_NUM_FORMS": "1000",
				"answers-0-order": "0",
				"answers-0-alternatives": "Αλιάκμονας",
				"answers-0-areas": [str(area.pk)],
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(MapPointer.objects.get().category_id, QuizCategory.GEOGRAPHY)


class MapPointerContentTests(TestCase):
	"""An answer may accept several areas — e.g. a river crossing prefectures."""

	LEVEL = MapPointer.MapLevel.PREFECTURE_UNIT

	def setUp(self):
		# Three prefecture units: two the river runs through, plus an unrelated one.
		self.areas = _areas(self.LEVEL, 3)
		self.names = [area.name for area in self.areas]

	def _create(self, *groups, min_correct_answers=1):
		quiz = MapPointer.objects.create(
			level=self.LEVEL,
			prompt_text="Πού βρίσκεται;",
			show_answers=True,
			min_correct_answers=min_correct_answers,
		)
		for order, (alternatives, areas) in enumerate(groups):
			answer = MapPointerAnswer.objects.create(question=quiz, order=order)
			MapPointerAlternative.objects.bulk_create(
				[
					MapPointerAlternative(answer=answer, text=text, order=index)
					for index, text in enumerate(alternatives)
				]
			)
			for index, area in enumerate(areas):
				MapPointerAnswerArea.objects.create(
					answer=answer, area=area, order=index
				)
		quiz.full_clean()
		return quiz

	def test_an_answer_keeps_every_area_it_accepts(self):
		quiz = self._create((["Αλιάκμονας"], self.areas[:2]))

		self.assertEqual(
			MapPointerSerializer(quiz).data["content"]["texts"],
			[{"alternatives": ["Αλιάκμονας"], "areas": self.names[:2]}],
		)

	def test_rejects_an_area_outside_the_map_level(self):
		other_level = _areas(MapPointer.MapLevel.REGION, 1)[0]

		with self.assertRaises(ValidationError):
			self._create((["Αλιάκμονας"], [self.areas[0], other_level]))

	def test_rejects_the_same_area_twice_in_one_answer(self):
		"""A unique constraint now, rather than a Python loop looking for dupes."""
		with self.assertRaises(IntegrityError):
			self._create((["Αλιάκμονας"], [self.areas[0], self.areas[0]]))

	def test_rejects_more_required_answers_than_exist(self):
		with self.assertRaises(ValidationError):
			self._create((["Αλιάκμονας"], self.areas[:1]), min_correct_answers=2)

	def test_two_answers_may_share_an_area(self):
		"""Two rivers can run through the same prefecture; the polygon accepts
		each of them and holds one label per answer placed on it."""
		quiz = self._create(
			(["Αλιάκμονας"], [self.areas[0], self.areas[1]]),
			(["Αξιός"], [self.areas[1], self.areas[2]]),
			min_correct_answers=2,
		)

		self.assertEqual(
			[g["areas"] for g in MapPointerSerializer(quiz).data["content"]["texts"]],
			[[self.names[0], self.names[1]], [self.names[1], self.names[2]]],
		)

	def test_two_answers_may_share_their_only_area(self):
		quiz = self._create(
			(["Αλιάκμονας"], [self.areas[0]]),
			(["Αξιός"], [self.areas[0]]),
			min_correct_answers=2,
		)

		self.assertEqual(
			[g["areas"] for g in MapPointerSerializer(quiz).data["content"]["texts"]],
			[[self.names[0]], [self.names[0]]],
		)

	def test_deleting_a_question_deletes_its_answers(self):
		quiz = self._create((["Αλιάκμονας"], self.areas[:1]))
		quiz.delete()

		self.assertFalse(MapPointerAnswer.objects.exists())
		self.assertFalse(MapPointerAnswerArea.objects.exists())

	def test_an_area_in_use_cannot_be_deleted(self):
		"""The point of the table: a rename or a split can no longer silently
		invalidate the answers pointing at it."""
		self._create((["Αλιάκμονας"], self.areas[:1]))

		with self.assertRaises(Exception):
			self.areas[0].delete()


class MapAreaTests(TestCase):
	def test_areas_are_seeded_for_every_level(self):
		"""Migration 0021 seeds them, so a fresh database already has them."""
		for level in MapPointer.MapLevel:
			self.assertTrue(
				MapArea.objects.filter(level=int(level)).exists(), f"level {level}"
			)

	def test_the_search_name_is_folded(self):
		"""Greek is routinely typed without its tonos, so the picker matches on a
		folded copy of the name."""
		area = MapArea.objects.filter(name="Άθως").first()

		self.assertIsNotNone(area)
		# casefold() also normalises the final sigma, which is fine: the typed
		# query goes through the same folding, so the two still meet.
		self.assertEqual(area.search_name, "αθωσ")

	def test_a_name_is_unique_within_its_level(self):
		area = MapArea.objects.first()

		with self.assertRaises(IntegrityError):
			MapArea.objects.create(level=area.level, name=area.name)


class MapPointerAreaPickerTests(TestCase):
	"""The area lists run to hundreds of names, so the picker is a real queryset
	scoped to the question's map level — which is what replaced the JSON-schema
	enum and the client-side script that used to rewrite it."""

	LEVEL = MapPointer.MapLevel.PREFECTURE_UNIT

	def setUp(self):
		self.admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(self.admin_user)

	def _answer_formset(self, obj=None):
		request = RequestFactory().get("/")
		request.user = self.admin_user
		inline = MapPointerAdmin(MapPointer, site).get_inline_instances(request, obj)[0]
		return inline.get_formset(request, obj)

	def test_the_add_page_offers_the_default_level_s_areas(self):
		formset = self._answer_formset()

		# An unbound formset with extra=0 has no forms, so the empty form — the one
		# the "add another" button clones — is what carries the picker.
		areas = formset(instance=MapPointer()).empty_form.fields["areas"].queryset
		default_level = MapPointer._meta.get_field("level").default

		self.assertEqual(
			set(areas.values_list("level", flat=True)), {int(default_level)}
		)

	def test_the_change_page_offers_that_question_s_level(self):
		quiz = MapPointer.objects.create(level=self.LEVEL, min_correct_answers=1)

		formset = self._answer_formset(quiz)
		areas = formset(instance=quiz).empty_form.fields["areas"].queryset

		self.assertEqual(set(areas.values_list("level", flat=True)), {int(self.LEVEL)})

	def test_searching_is_accent_and_case_insensitive(self):
		"""Greek is routinely typed without its tonos; the folded column is what
		the admin search matches on."""
		response = self.client.get(
			reverse("admin:quiz_maparea_changelist"), {"q": "αθως"}
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn("Άθως", response.content.decode())

	def test_the_admin_saves_an_answer_with_several_picked_areas(self):
		areas = _areas(self.LEVEL, 3)

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"level": str(int(self.LEVEL)),
				"prompt_text": "Ποιον νομό διασχίζει ο Αλιάκμονας;",
				"min_correct_answers": "1",
				"show_answers": "on",
				"test_number": "0",
				"question_number": "0",
				"is_active": "on",
				"answers-TOTAL_FORMS": "1",
				"answers-INITIAL_FORMS": "0",
				"answers-MIN_NUM_FORMS": "0",
				"answers-MAX_NUM_FORMS": "1000",
				"answers-0-order": "0",
				"answers-0-alternatives": "Αλιάκμονας",
				"answers-0-areas": [str(area.pk) for area in areas],
			},
		)

		self.assertEqual(response.status_code, 302, getattr(response, "context", None))
		quiz = MapPointer.objects.get()
		self.assertEqual(
			MapPointerSerializer(quiz).data["content"]["texts"][0]["areas"],
			[area.name for area in areas],
		)

	def test_alternatives_are_saved_one_per_line(self):
		area = _areas(self.LEVEL, 1)[0]

		self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"level": str(int(self.LEVEL)),
				"prompt_text": "Πού;",
				"min_correct_answers": "1",
				"show_answers": "on",
				"test_number": "0",
				"question_number": "0",
				"is_active": "on",
				"answers-TOTAL_FORMS": "1",
				"answers-INITIAL_FORMS": "0",
				"answers-MIN_NUM_FORMS": "0",
				"answers-MAX_NUM_FORMS": "1000",
				"answers-0-order": "0",
				"answers-0-alternatives": "Αλιάκμονας\nαλιακμονας\n",
				"answers-0-areas": [str(area.pk)],
			},
		)

		quiz = MapPointer.objects.get()
		self.assertEqual(
			MapPointerSerializer(quiz).data["content"]["texts"][0]["alternatives"],
			["Αλιάκμονας", "αλιακμονας"],
		)

	def test_the_area_list_is_closed_to_non_staff(self):
		self.client.logout()

		response = self.client.get(reverse("admin:quiz_maparea_changelist"))

		self.assertNotEqual(response.status_code, 200)


class LegacyContentParsingTests(TestCase):
	"""The shapes ``content`` accumulated over the years are absorbed by migration
	0021 and then gone. These assert the migration's own frozen parsers, which is
	where that tolerance now lives and dies."""

	def test_a_legacy_single_area_string_becomes_a_one_item_list(self):
		self.assertEqual(_0021._parse_areas("Ιωαννίνων"), ["Ιωαννίνων"])

	def test_a_legacy_area_object_becomes_a_one_item_list(self):
		self.assertEqual(_0021._parse_areas({"name": "Ιωαννίνων"}), ["Ιωαννίνων"])

	def test_a_missing_area_becomes_an_empty_list(self):
		self.assertEqual(_0021._parse_areas(None), [])

	def test_a_legacy_single_text_answer_becomes_one_alternative(self):
		self.assertEqual(_0021._parse_alternatives({"text": "Αθήνα"}), ["Αθήνα"])

	def test_a_bare_string_answer_becomes_one_alternative(self):
		self.assertEqual(_0021._parse_alternatives("Αθήνα"), ["Αθήνα"])

	def test_a_legacy_bare_list_of_columns_is_read_as_columns(self):
		columns = [{"title": "A", "items": []}, {"title": "B", "items": []}]

		self.assertEqual(_0021._matching_columns(columns), columns)
		self.assertEqual(_0021._matching_columns({"columns": columns}), columns)


class ImportExportRoundTripTests(TestCase):
	"""The importer writes child rows in ``after_save_instance`` now, and a
	re-import rewrites them wholesale. Exporting what was just imported is the
	cheapest way to catch a row that went missing on the way through."""

	def _import(self, resource, headers, row):
		dataset = tablib.Dataset(headers=headers)
		dataset.append(row)
		result = resource.import_data(dataset, raise_errors=True)
		self.assertFalse(result.has_errors(), result.row_errors())
		return result

	def test_a_statement_survives_import_then_export(self):
		resource = StatementResource()
		headers = [
			"id",
			"type",
			"category",
			"prompt_text",
			"choice1_text",
			"choice1_is_correct",
			"choice2_text",
			"choice2_is_correct",
		]
		row = [
			"",
			Statement.StatementType.MULTIPLE_CHOICE,
			QuizCategory.GEOGRAPHY,
			"Ποια είναι σωστή;",
			"A",
			"true",
			"B",
			"false",
		]

		self._import(resource, headers, row)

		statement = Statement.objects.get()
		self.assertEqual(
			[(c.text, c.is_correct) for c in statement.choices.all()],
			[("A", True), ("B", False)],
		)

		exported = resource.export(queryset=Statement.objects.all())
		self.assertEqual(exported[0][3], "Ποια είναι σωστή;")
		self.assertEqual(exported[0][10:16], ("A", "", "true", "B", "", "false"))

	def test_reimporting_replaces_the_choices_rather_than_adding_to_them(self):
		resource = StatementResource()
		headers = ["id", "type", "category", "choice1_text", "choice1_is_correct"]
		self._import(
			resource,
			headers,
			[
				"",
				Statement.StatementType.TRUE_FALSE,
				QuizCategory.GEOGRAPHY,
				"A",
				"true",
			],
		)
		statement = Statement.objects.get()

		self._import(
			resource,
			headers,
			[
				str(statement.pk),
				Statement.StatementType.TRUE_FALSE,
				QuizCategory.GEOGRAPHY,
				"B",
				"true",
			],
		)

		self.assertEqual([c.text for c in Statement.objects.get().choices.all()], ["B"])

	def test_a_matching_question_survives_import_then_export(self):
		resource = MatchingResource()
		headers = ["id", "category", "left_title", "right_title", "items"]
		row = [
			"",
			QuizCategory.GEOGRAPHY,
			"Ποταμοί",
			"Νομοί",
			"Αλιάκμονας_Ημαθίας | Αξιός_Πέλλας",
		]

		self._import(resource, headers, row)

		question = Matching.objects.get()
		self.assertEqual(
			[(p.left_text, p.right_text) for p in question.pairs.all()],
			[("Αλιάκμονας", "Ημαθίας"), ("Αξιός", "Πέλλας")],
		)

		exported = resource.export(queryset=Matching.objects.all())
		self.assertEqual(exported[0][4], "Αλιάκμονας_Ημαθίας | Αξιός_Πέλλας")

	def test_an_imported_matching_question_serializes_with_matching_ids(self):
		resource = MatchingResource()
		self._import(
			resource,
			["id", "category", "left_title", "right_title", "items"],
			["", QuizCategory.GEOGRAPHY, "A", "B", "l1_r1 | l2_r2"],
		)

		columns = MatchingSerializer(Matching.objects.get()).data["content"]["columns"]

		self.assertEqual([i["id"] for i in columns[0]["items"]], [1, 2])
		self.assertEqual([i["matched_id"] for i in columns[0]["items"]], [3, 4])
