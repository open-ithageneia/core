import json
from types import SimpleNamespace

from django.contrib.admin.sites import site
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
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
)
from quiz.models import (
	Listening,
	ListeningPart,
	MapPointer,
	QuizAsset,
	QuizCategory,
	Statement,
)
from quiz.schemas import AREA_NAME_CHOICES_BY_LEVEL, MapPointerContent
from quiz.serializers import ListeningSerializer, MapPointerSerializer
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
		# The first part holds the true/false statements, the second the
		# multiple-choice questions — the usual layout.
		self.part_a = ListeningPart.objects.create(
			listening=self.group, description="Σημειώστε σωστό ή λάθος"
		)
		self.part_b = ListeningPart.objects.create(listening=self.group)
		self.true_false = Statement.objects.create(
			type=Statement.StatementType.TRUE_FALSE,
			listening=self.group,
			part=self.part_a,
			order=0,
			content=_true_false_content(("first", True), ("second", False)),
		)
		# Created out of order, to prove ``order`` drives the output.
		self.multiple_choice = [
			Statement.objects.create(
				type=Statement.StatementType.MULTIPLE_CHOICE,
				listening=self.group,
				part=self.part_b,
				order=index,
				content=_multiple_choice_content(f"question {index}"),
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
		# No JSON content column on the group itself.
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


class CategorySamplingTests(TestCase):
	"""The training page sends its category multi-select as one comma-separated
	value, so sampling has to honour every code in it."""

	def setUp(self):
		self.statements = {
			code: Statement.objects.create(
				type=Statement.StatementType.MULTIPLE_CHOICE,
				category_id=code,
				content=_multiple_choice_content(code),
			)
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
			self._sampled_categories(QuizCategory.HISTORY), {QuizCategory.HISTORY}
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

	def test_rejects_a_question_without_a_part(self):
		"""A part-less question would never be shown, so it can't be saved."""
		formset = self._formset(
			Statement.StatementType.TRUE_FALSE,
			Statement.StatementType.MULTIPLE_CHOICE,
			with_parts=False,
		)

		self.assertFalse(formset.is_valid())
		self.assertIn("part_position", formset.errors[0])


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
					f"questions-{index}-content": json.dumps(
						ListeningAdminInlineTests._posted_content()
					),
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
		content = json.dumps(ListeningAdminInlineTests._posted_content())

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
				"questions-0-content": content,
				"questions-0-is_active": "on",
				"questions-1-part_position": "2",
				"questions-1-order": "0",
				"questions-1-type": Statement.StatementType.MULTIPLE_CHOICE,
				"questions-1-content": content,
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
		question = Statement.objects.create(
			type=Statement.StatementType.MULTIPLE_CHOICE,
			listening=group,
			part=part_b,
			content=_multiple_choice_content("question"),
		)

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
		content = json.dumps(ListeningAdminInlineTests._posted_content())

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
				"questions-0-content": content,
				"questions-0-is_active": "on",
				"questions-1-part_position": "2",
				"questions-1-order": "0",
				"questions-1-type": Statement.StatementType.MULTIPLE_CHOICE,
				"questions-1-content": content,
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
		content = {
			"prompt_text": "Πού βρίσκεται;",
			"show_answers": True,
			"min_correct_answers": 1,
			"texts": [
				{
					"alternatives": ["Αλιάκμονας"],
					"areas": AREA_NAME_CHOICES_BY_LEVEL[int(level)][:1],
				}
			],
		}

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"level": str(int(level)),
				"content": json.dumps(content),
				"is_active": "on",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(MapPointer.objects.get().category_id, QuizCategory.GEOGRAPHY)


class MapPointerContentTests(TestCase):
	"""An answer may accept several areas — e.g. a river crossing prefectures."""

	LEVEL = MapPointer.MapLevel.PREFECTURE_UNIT
	# Two prefecture units the Αλιάκμονας flows through, plus an unrelated one.
	AREAS = AREA_NAME_CHOICES_BY_LEVEL[int(LEVEL)][:3]

	def _content(self, *groups, min_correct_answers=1):
		return {
			"prompt_text": "Πού βρίσκεται;",
			"show_answers": True,
			"min_correct_answers": min_correct_answers,
			"texts": [
				{"alternatives": alternatives, "areas": areas}
				for alternatives, areas in groups
			],
		}

	def _create(self, *groups, **kwargs):
		return MapPointer.objects.create(
			level=self.LEVEL, content=self._content(*groups, **kwargs)
		)

	def test_an_answer_keeps_every_area_it_accepts(self):
		quiz = self._create((["Αλιάκμονας"], self.AREAS[:2]))

		self.assertEqual(quiz.content_model.texts[0].areas, self.AREAS[:2])
		self.assertEqual(
			MapPointerSerializer(quiz).data["content"]["texts"],
			[{"alternatives": ["Αλιάκμονας"], "areas": self.AREAS[:2]}],
		)

	def test_a_legacy_single_area_is_read_as_a_one_item_list(self):
		quiz = MapPointer(
			level=self.LEVEL,
			content={
				"prompt_text": "Πού βρίσκεται;",
				"show_answers": True,
				"min_correct_answers": 1,
				"texts": [{"alternatives": ["Αλιάκμονας"], "area": self.AREAS[0]}],
			},
		)
		quiz.save()

		self.assertEqual(quiz.content_model.texts[0].areas, [self.AREAS[0]])

	def test_a_legacy_area_object_is_read_as_a_one_item_list(self):
		content = MapPointerContent.from_json(
			{
				"show_answers": True,
				"min_correct_answers": 1,
				"texts": [
					{"alternatives": ["Αλιάκμονας"], "area": {"name": self.AREAS[0]}}
				],
			}
		)

		self.assertEqual(content.texts[0].areas, [self.AREAS[0]])

	def test_rejects_an_area_outside_the_map_level(self):
		with self.assertRaises(ValidationError):
			self._create((["Αλιάκμονας"], [self.AREAS[0], "Ουτοπία"]))

	def test_rejects_the_same_area_twice_in_one_answer(self):
		with self.assertRaises(ValidationError):
			self._create((["Αλιάκμονας"], [self.AREAS[0], self.AREAS[0]]))

	def test_two_answers_may_share_an_area(self):
		"""Two rivers can run through the same prefecture; the polygon accepts
		each of them and holds one label per answer placed on it."""
		quiz = self._create(
			(["Αλιάκμονας"], [self.AREAS[0], self.AREAS[1]]),
			(["Αξιός"], [self.AREAS[1], self.AREAS[2]]),
			min_correct_answers=2,
		)

		self.assertEqual(
			[group.areas for group in quiz.content_model.texts],
			[[self.AREAS[0], self.AREAS[1]], [self.AREAS[1], self.AREAS[2]]],
		)

	def test_two_answers_may_share_their_only_area(self):
		quiz = self._create(
			(["Αλιάκμονας"], [self.AREAS[0]]),
			(["Αξιός"], [self.AREAS[0]]),
			min_correct_answers=2,
		)

		self.assertEqual(
			[group.areas for group in quiz.content_model.texts],
			[[self.AREAS[0]], [self.AREAS[0]]],
		)


class MapPointerAreaPickerTests(TestCase):
	"""The area lists run to hundreds of names, so the admin offers a
	type-to-search picker instead of a plain dropdown. django-jsonform's
	autocomplete widget fetches the matches from an endpoint as the editor
	types — it does not filter the schema's enum client-side."""

	LEVEL = MapPointer.MapLevel.PREFECTURE_UNIT

	def setUp(self):
		self.admin_user = get_user_model().objects.create_superuser(
			username="admin", email="admin@example.com", password="password"
		)
		self.client.force_login(self.admin_user)

	def _search(self, query, level=None):
		url = reverse(
			"admin:quiz_mappointer_area_options",
			kwargs={"level": int(level if level is not None else self.LEVEL)},
		)
		return self.client.get(url, {"query": query})

	def test_the_add_page_wires_the_picker_to_this_level_s_options(self):
		page = self.client.get(reverse("admin:quiz_mappointer_add"))

		self.assertEqual(page.status_code, 200)
		areas = MapPointerContent.build_schema(
			MapPointerContent.DEFAULT_LEVEL, area_options_url="/areas/4/"
		)["properties"]["texts"]["items"]["properties"]["areas"]
		self.assertEqual(areas["items"]["widget"], "multiselect-autocomplete")
		self.assertEqual(areas["items"]["handler"], "/areas/4/")
		# The saved area names still have to come from the level's own list.
		self.assertEqual(
			areas["items"]["enum"],
			AREA_NAME_CHOICES_BY_LEVEL[MapPointerContent.DEFAULT_LEVEL],
		)
		rendered = page.content.decode()
		self.assertIn("multiselect-autocomplete", rendered)
		self.assertIn(
			reverse(
				"admin:quiz_mappointer_area_options",
				kwargs={"level": MapPointerContent.DEFAULT_LEVEL},
			),
			rendered,
		)

	def test_searching_returns_the_matching_area_names(self):
		response = self._search("ΙΩΑΝΝ")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["results"], ["ΙΩΑΝΝΙΝΩΝ"])

	def test_searching_ignores_case(self):
		self.assertEqual(self._search("ιωανν").json()["results"], ["ΙΩΑΝΝΙΝΩΝ"])

	def test_searching_ignores_accents(self):
		"""Greek is routinely typed without its tonos."""
		results = self._search("αθως", level=MapPointer.MapLevel.MUNICIPALITY).json()[
			"results"
		]

		self.assertEqual(results, ["Άθως"])

	def test_a_query_matching_nothing_returns_no_options(self):
		self.assertEqual(self._search("Ουτοπίας").json()["results"], [])

	def test_a_blank_query_lists_the_whole_level(self):
		"""Nothing typed yet means "show me everything" — the picker seeds its
		search box with a space so the list can be browsed as well as searched."""
		everything = AREA_NAME_CHOICES_BY_LEVEL[int(self.LEVEL)]

		self.assertEqual(self._search(" ").json()["results"], everything)
		self.assertEqual(self._search("").json()["results"], everything)

	def test_the_typed_text_is_matched_ignoring_surrounding_space(self):
		"""The seeded space sits in front of whatever the editor types next."""
		self.assertEqual(self._search(" ιωανν ").json()["results"], ["ΙΩΑΝΝΙΝΩΝ"])

	def test_every_match_is_returned(self):
		"""A common stem matches many areas; none of them may be dropped."""
		results = self._search("αγιου", level=MapPointer.MapLevel.MUNICIPALITY).json()[
			"results"
		]

		self.assertEqual(
			results,
			[
				"ΑγίουΒασιλείου",
				"ΑγίουΔημητρίου",
				"ΑγίουΕυστρατίου",
				"ΑγίουΝικολάου",
				"Μώλου-ΑγίουΚωνσταντίνου",
				"Νίκαιας-ΑγίουΙωάννηΡέντη",
			],
		)

	def test_an_unknown_level_is_not_found(self):
		self.assertEqual(self._search("Ιωάνν", level=99).status_code, 404)

	def test_the_admin_saves_an_answer_with_several_picked_areas(self):
		"""End to end through jsonform's own validation of the picked values."""
		areas = AREA_NAME_CHOICES_BY_LEVEL[int(self.LEVEL)][:3]
		content = {
			"prompt_text": "Ποιον νομό διασχίζει ο Αλιάκμονας;",
			"show_answers": True,
			"min_correct_answers": 1,
			"texts": [{"alternatives": ["Αλιάκμονας"], "areas": areas}],
		}

		response = self.client.post(
			reverse("admin:quiz_mappointer_add"),
			{
				"level": str(int(self.LEVEL)),
				"content": json.dumps(content),
				"is_active": "on",
			},
		)

		self.assertEqual(response.status_code, 302, getattr(response, "context", None))
		quiz = MapPointer.objects.get()
		self.assertEqual(quiz.content_model.texts[0].areas, areas)

	def test_the_options_are_closed_to_non_staff(self):
		self.client.logout()

		response = self._search("Ιωάνν")

		self.assertNotEqual(response.status_code, 200)
		self.assertNotIn("Ιωάννινα", response.content.decode())
