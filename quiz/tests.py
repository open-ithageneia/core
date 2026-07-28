import json

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.forms.models import inlineformset_factory
from django.test import TestCase

from quiz.admin import ListeningQuestionFormSet, ListeningQuestionInline
from quiz.models import Listening, ListeningPart, QuizAsset, Statement
from quiz.serializers import ListeningSerializer
from quiz.services import QuizService


def _true_false_content(*statements):
	return {
		"choices": [
			{"text": text, "is_correct": is_correct} for text, is_correct in statements
		]
	}


def _multiple_choice_content(prompt):
	return {
		"prompt_text": prompt,
		"choices": [
			{"text": "A", "is_correct": True},
			{"text": "B", "is_correct": False},
		],
	}


class ListeningTests(TestCase):
	def setUp(self):
		self.asset = QuizAsset.objects.create(
			title="clip", audio=ContentFile(b"audio-bytes", name="clip.mp3")
		)
		self.group = Listening.objects.create(audio=self.asset, transcript="transcript")
		# Part A holds the true/false statements, part B the multiple-choice
		# questions — the usual layout.
		self.true_false = Statement.objects.create(
			type=Statement.StatementType.TRUE_FALSE,
			listening=self.group,
			part=ListeningPart.A,
			order=0,
			content=_true_false_content(("first", True), ("second", False)),
		)
		# Created out of order, to prove ``order`` drives the output.
		self.multiple_choice = [
			Statement.objects.create(
				type=Statement.StatementType.MULTIPLE_CHOICE,
				listening=self.group,
				part=ListeningPart.B,
				order=index,
				content=_multiple_choice_content(f"question {index}"),
			)
			for index in (2, 1)
		]

	def test_serializes_audio_and_questions_grouped_by_part(self):
		data = ListeningSerializer(self.group).data

		self.assertTrue(data["audio_url"].endswith(".mp3"))
		self.assertEqual(data["max_plays"], 2)
		self.assertEqual([part["part"] for part in data["parts"]], ["A", "B"])
		self.assertEqual(
			[question["id"] for question in data["parts"][0]["questions"]],
			[self.true_false.id],
		)
		self.assertEqual(
			[question["id"] for question in data["parts"][1]["questions"]],
			[self.multiple_choice[1].id, self.multiple_choice[0].id],
		)
		# No JSON content column on the group itself.
		self.assertNotIn("content", data)

	def test_empty_parts_are_left_out(self):
		Statement.objects.filter(listening=self.group).update(part=ListeningPart.A)

		data = ListeningSerializer(self.group).data

		self.assertEqual([part["part"] for part in data["parts"]], ["A"])

	def test_part_is_independent_of_question_type(self):
		"""Part A is usually the true/false one, but that is not enforced."""
		self.true_false.part = ListeningPart.B
		self.true_false.save()

		self.group.full_clean()

		data = ListeningSerializer(self.group).data
		self.assertEqual([part["part"] for part in data["parts"]], ["B"])
		self.assertEqual(len(data["parts"][0]["questions"]), 3)

	def test_rejects_a_second_true_false_question(self):
		Statement.objects.create(
			type=Statement.StatementType.TRUE_FALSE,
			listening=self.group,
			order=9,
			content=_true_false_content(("extra", True)),
		)

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
		standalone = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE,
			content=_multiple_choice_content("standalone"),
		)

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


class ListeningAdminInlineTests(TestCase):
	"""The admin saves a group before its inlines, so the formset — not
	``Listening.full_clean()`` — is what validates the shape on admin saves."""

	def setUp(self):
		self.asset = QuizAsset.objects.create(
			title="clip", audio=ContentFile(b"audio-bytes", name="clip.mp3")
		)
		self.group = Listening.objects.create(audio=self.asset)

	@staticmethod
	def _posted_content():
		"""Content in the shape the admin posts it: django-jsonform's form
		validator requires every key declared in the schema to be present, which
		is more than the stored shape needs. Both question types share the schema.
		"""
		choice_count = 2
		return {
			"prompt_text": "question",
			"prompt_asset_id": None,
			"prompt_audio_asset_id": None,
			"choices": [
				{"text": f"choice {index}", "asset_id": None, "is_correct": index == 0}
				for index in range(choice_count)
			],
		}

	def _formset(self, *types):
		FormSet = inlineformset_factory(
			Listening,
			Statement,
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
			part = (
				ListeningPart.A
				if type_ == Statement.StatementType.TRUE_FALSE
				else ListeningPart.B
			)
			data.update(
				{
					f"questions-{index}-part": part,
					f"questions-{index}-order": str(index),
					f"questions-{index}-type": type_,
					f"questions-{index}-category": "GEOGRAPHY",
					f"questions-{index}-content": json.dumps(self._posted_content()),
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
