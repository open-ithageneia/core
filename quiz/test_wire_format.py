"""Proof that the move to content tables did not change what the client receives.

The obvious approach — snapshotting a developer's database and diffing it — only
covers the rows that happen to be on that machine. Production holds more rows
and, crucially, *older shapes*: the legacy formats every ``from_json`` grew a
branch for. Those are exactly where a backfill goes wrong, and exactly what a dev
snapshot cannot see. (It also could not tell a real regression from the
``id``/``matched_id`` renumbering that ``MatchPair`` does on purpose.)

So nothing here reads an existing database. Instead:

1. ``CONTENT_CORPUS`` lists content JSON by hand, including every legacy shape
   the deleted ``quiz/schemas.py`` accepted. It is committed, so it is reviewable
   and it runs in CI.
2. ``reference_content()`` is the **deleted serializer, vendored verbatim** — the
   ``to_dict()`` chain exactly as it was before this refactor. It is the oracle.
3. ``BackfillEquivalenceTests`` seeds each corpus entry as a pre-migration row,
   runs **the real migration** through Django's migration executor, then
   serializes the result with the real serializer and asserts it equals the
   oracle's output.

If that passes, the refactor is invisible for every shape in the corpus,
whatever database it is applied to. Add a shape here when you find one the
corpus does not cover.
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from quiz.models import (
	DragAndDrop,
	FillInTheBlank,
	MapPointer,
	Matching,
	OpenEnded,
	QuizAsset,
	Statement,
)
from quiz.serializers import (
	DragAndDropSerializer,
	FillInTheBlankSerializer,
	MapPointerSerializer,
	MatchingSerializer,
	OpenEndedSerializer,
	StatementSerializer,
)

# ---------------------------------------------------------------------------
# The oracle: quiz/schemas.py as it was, reduced to the output path.
#
# Copied rather than imported, because the module it came from is deleted — that
# is the point. Do not "fix" anything in here to match new behaviour; if this
# and the serializer disagree, the serializer changed the contract.
# ---------------------------------------------------------------------------


def _asset_url(asset_id):
	asset = QuizAsset.objects.filter(id=asset_id).first()
	if asset and asset.image:
		return asset.image.url
	return None


def _audio_asset_url(asset_id):
	asset = QuizAsset.objects.filter(id=asset_id).first()
	if asset and asset.audio:
		return asset.audio.url
	return None


def _statement_content(data):
	return {
		"choices": [
			{
				"is_correct": choice.get("is_correct", False),
				"text": choice.get("text"),
				"asset_url": _asset_url(choice.get("asset_id")),
			}
			for choice in data["choices"]
		],
		"prompt_text": data.get("prompt_text"),
		"prompt_asset_url": _asset_url(data.get("prompt_asset_id")),
		"prompt_audio_url": _audio_asset_url(data.get("prompt_audio_asset_id")),
	}


def _drag_and_drop_content(data):
	return [
		{"title": column["title"], "values": column.get("values", [])}
		for column in data
	]


def _matching_content(data):
	# The legacy bare-list form was still accepted when this was deleted.
	if isinstance(data, list):
		columns_data, prompt_text = data, None
	else:
		columns_data, prompt_text = data["columns"], data.get("prompt_text")

	return {
		"prompt_text": prompt_text,
		"columns": [
			{
				"title": column["title"],
				"items": [
					{
						"text": item.get("text"),
						"asset_url": _asset_url(item.get("asset_id")),
						"id": item.get("id"),
						"matched_id": item.get("matched_id"),
					}
					for item in column.get("items", [])
				],
			}
			for column in columns_data
		],
	}


def _fill_in_the_blank_content(data):
	import re

	blank_pattern = re.compile(r"<(.+?)>")
	choice_pattern = re.compile(r"\{\{(.+?)\}\}(\*?)")

	texts, any_multiple = [], False
	for entry in data.get("texts", []):
		text = entry["text"]
		raw_blanks = blank_pattern.findall(text)
		has_multiple = False
		for blank in raw_blanks:
			choices = choice_pattern.findall(blank)
			correct = [c for c, marker in choices if marker == "*"]
			if len(choices) > 1 and len(correct) == 1:
				has_multiple = True
		any_multiple = any_multiple or has_multiple

		parts = []
		for index, chunk in enumerate(blank_pattern.split(text)):
			if index % 2 == 0:
				if chunk:
					parts.append({"text": chunk, "is_blank": False})
			else:
				parts.append(
					{
						"text": None,
						"is_blank": True,
						"choices": [
							{"text": c, "is_correct": marker == "*"}
							for c, marker in choice_pattern.findall(chunk)
						],
					}
				)
		texts.append({"parts": parts, "_has_multiple": has_multiple})

	def build_choices():
		if not data.get("show_answers_as_choices", False) or any_multiple:
			return None
		choices = list(data.get("extra_choices", []))
		visited = set()
		for text in texts:
			for part in text["parts"]:
				if not part["is_blank"] or not part.get("choices"):
					continue
				key = tuple(c["text"] for c in part["choices"])
				if key not in visited:
					visited.add(key)
					choices.extend(key)
		return choices

	return {
		"show_answers_as_choices": data.get("show_answers_as_choices", False),
		"has_multiple_choices": any_multiple,
		"prompt_instruction_choices": build_choices(),
		"texts": [{"parts": text["parts"]} for text in texts],
		"prompt_asset_url": _asset_url(data.get("prompt_asset_id")),
	}


def _legacy_alternatives(raw):
	if isinstance(raw, dict):
		alternatives = raw.get("alternatives", [])
		if not alternatives and "text" in raw:
			alternatives = [raw["text"]]
		return alternatives
	if isinstance(raw, list):
		return raw
	if isinstance(raw, str):
		return [raw]
	return [str(raw)]


def _legacy_areas(raw):
	if raw is None:
		return []
	if isinstance(raw, str):
		return [raw] if raw else []
	if isinstance(raw, dict):
		name = raw.get("name")
		return [name] if name else []
	if isinstance(raw, list):
		areas = []
		for item in raw:
			areas.extend(_legacy_areas(item))
		return areas
	return []


def _open_ended_content(data):
	return {
		"min_correct_answers": data.get("min_correct_answers", 0),
		"prompt_text": data.get("prompt_text"),
		"texts": [_legacy_alternatives(raw) for raw in data.get("texts", [])],
		"prompt_asset_url": _asset_url(data.get("prompt_asset_id")),
	}


def _map_pointer_content(data):
	groups = []
	for raw in data.get("texts", []):
		if isinstance(raw, dict):
			raw_areas = raw["areas"] if "areas" in raw else raw.get("area")
		else:
			raw_areas = None
		group = {"alternatives": _legacy_alternatives(raw)}
		areas = _legacy_areas(raw_areas)
		if areas:
			group["areas"] = areas
		groups.append(group)

	return {
		"show_answers": data.get("show_answers", True),
		"min_correct_answers": data.get("min_correct_answers", 0),
		"prompt_text": data.get("prompt_text"),
		"texts": groups,
	}


REFERENCE = {
	"Statement": _statement_content,
	"DragAndDrop": _drag_and_drop_content,
	"Matching": _matching_content,
	"FillInTheBlank": _fill_in_the_blank_content,
	"OpenEnded": _open_ended_content,
	"MapPointer": _map_pointer_content,
}


def reference_content(model_name, content):
	"""What the client used to receive for this stored ``content``."""
	return REFERENCE[model_name](content)


def matching_relation(content):
	"""A matching question with its bookkeeping ids reduced to what they mean.

	``id``/``matched_id`` are regenerated rather than stored — see ``MatchPair``
	— so the integers legitimately differ from whatever a legacy row happened to
	hold. What must not differ is everything they encode: the order of each
	column, and which item each one is paired with. That is what this compares,
	by replacing the two numbers with the partner's index in the other column.
	"""
	left, right = content["columns"]
	left_index = {item["id"]: position for position, item in enumerate(left["items"])}
	right_index = {item["id"]: position for position, item in enumerate(right["items"])}

	def column(items, partner_index):
		return [
			{
				"text": item["text"],
				"asset_url": item["asset_url"],
				"partner": partner_index.get(item["matched_id"]),
			}
			for item in items
		]

	return {
		"prompt_text": content["prompt_text"],
		"columns": [
			{"title": left["title"], "items": column(left["items"], right_index)},
			{"title": right["title"], "items": column(right["items"], left_index)},
		],
	}


# ---------------------------------------------------------------------------
# The corpus. One entry per shape worth proving, legacy ones included.
# ---------------------------------------------------------------------------

# Real level-3 (prefecture unit) names, so the seeded MapArea rows match.
AREA_A = "ΑΙΤΩΛΟΑΚΑΡΝΑΝΙΑΣ"
AREA_B = "ΑΡΓΟΛΙΔΑΣ"

#: ``(label, model, content, extra_column_values)``
CONTENT_CORPUS = [
	(
		"statement: the current shape",
		"Statement",
		{
			"prompt_text": "Ποια είναι;",
			"prompt_asset_id": None,
			"prompt_audio_asset_id": None,
			"choices": [
				{"text": "Α", "asset_id": None, "is_correct": True},
				{"text": "Β", "asset_id": None, "is_correct": False},
			],
		},
		{"type": "MULTIPLE_CHOICE"},
	),
	(
		"statement: keys absent rather than null",
		"Statement",
		{"choices": [{"text": "Α", "is_correct": True}]},
		{"type": "TRUE_FALSE"},
	),
	(
		"statement: no choices at all",
		"Statement",
		{"prompt_text": "Ορφανή", "choices": []},
		{"type": "TRUE_FALSE"},
	),
	(
		"statement: a choice that is an image with no text",
		"Statement",
		{
			"prompt_text": "Διάλεξε",
			"choices": [
				{"asset_id": "IMAGE", "is_correct": True},
				{"text": "Β", "is_correct": False},
			],
		},
		{"type": "MULTIPLE_CHOICE"},
	),
	(
		"drag and drop: the only shape",
		"DragAndDrop",
		[
			{"title": "Ποταμοί", "values": ["Αλιάκμονας", "Πηνειός"]},
			{"title": "Λίμνες", "values": ["Κερκίνη"]},
		],
		{},
	),
	(
		"drag and drop: a column with no values",
		"DragAndDrop",
		[{"title": "Γεμάτη", "values": ["Α"]}, {"title": "Άδεια", "values": []}],
		{},
	),
	(
		"matching: the current object shape",
		"Matching",
		{
			"prompt_text": "Αντιστοιχίστε",
			"columns": [
				{
					"title": "Α",
					"items": [
						{"id": 1, "matched_id": 3, "text": "α1"},
						{"id": 2, "matched_id": 4, "text": "α2"},
					],
				},
				{
					"title": "Β",
					"items": [
						{"id": 3, "matched_id": 1, "text": "β1"},
						{"id": 4, "matched_id": 2, "text": "β2"},
					],
				},
			],
		},
		{},
	),
	(
		"matching: LEGACY bare list of two columns (pre-0004)",
		"Matching",
		[
			{"title": "Α", "items": [{"id": 1, "matched_id": 2, "text": "α1"}]},
			{"title": "Β", "items": [{"id": 2, "matched_id": 1, "text": "β1"}]},
		],
		{},
	),
	(
		"matching: null titles and an image-only item",
		"Matching",
		{
			"prompt_text": None,
			"columns": [
				{
					"title": None,
					"items": [{"id": 1, "matched_id": 2, "asset_id": "IMAGE"}],
				},
				{"title": None, "items": [{"id": 2, "matched_id": 1, "text": "β1"}]},
			],
		},
		{},
	),
	(
		"matching: ids that are not positional",
		"Matching",
		{
			"columns": [
				{
					"title": "Α",
					"items": [
						{"id": 41, "matched_id": 92, "text": "α1"},
						{"id": 42, "matched_id": 91, "text": "α2"},
					],
				},
				{
					"title": "Β",
					"items": [
						{"id": 91, "matched_id": 42, "text": "β2"},
						{"id": 92, "matched_id": 41, "text": "β1"},
					],
				},
			]
		},
		{},
	),
	(
		# The schema never required the columns to be the same length.
		"matching: a right-column distractor no left item points at",
		"Matching",
		{
			"columns": [
				{
					"title": "Α",
					"items": [
						{"id": 1, "matched_id": 4, "text": "α1"},
						{"id": 2, "matched_id": 5, "text": "α2"},
					],
				},
				{
					"title": "Β",
					"items": [
						{"id": 3, "matched_id": 0, "text": "β-extra"},
						{"id": 4, "matched_id": 1, "text": "β1"},
						{"id": 5, "matched_id": 2, "text": "β2"},
					],
				},
			]
		},
		{},
	),
	(
		"matching: a left item whose partner is not in the right column",
		"Matching",
		{
			"columns": [
				{
					"title": "Α",
					"items": [
						{"id": 1, "matched_id": 3, "text": "α1"},
						{"id": 2, "matched_id": 99, "text": "α2"},
					],
				},
				{"title": "Β", "items": [{"id": 3, "matched_id": 1, "text": "β1"}]},
			]
		},
		{},
	),
	(
		"fill in the blank: single-choice blanks with a word bank",
		"FillInTheBlank",
		{
			"prompt_asset_id": None,
			"show_answers_as_choices": True,
			"texts": [
				{"text": "Η Κως συνορεύει με <{{την Τουρκία}}*>"},
				{"text": "Το Διδυμότειχο συνορεύει με  <{{την Τουρκία}}*> "},
			],
			"extra_choices": ["τη Βουλγαρία"],
		},
		{},
	),
	(
		"fill in the blank: a multiple-choice blank suppresses the word bank",
		"FillInTheBlank",
		{
			"show_answers_as_choices": True,
			"texts": [{"text": "Το <{{1821}}*, {{1822}}> ήταν"}],
			"extra_choices": [],
		},
		{},
	),
	(
		"fill in the blank: no word bank asked for",
		"FillInTheBlank",
		{"show_answers_as_choices": False, "texts": [{"text": "Α <{{β}}*> γ"}]},
		{},
	),
	(
		"open ended: the current alternatives shape",
		"OpenEnded",
		{
			"prompt_text": "Ποιος ποταμός;",
			"prompt_asset_id": None,
			"min_correct_answers": 2,
			"texts": [
				{"alternatives": ["Αλιάκμονας", "Αλιακμων"]},
				{"alternatives": ["Αξιός"]},
			],
		},
		{},
	),
	(
		"open ended: LEGACY single-text dicts (pre-0003)",
		"OpenEnded",
		{
			"prompt_text": "Ποιος;",
			"min_correct_answers": 1,
			"texts": [{"text": "Αλιάκμονας"}, {"text": "Αξιός"}],
		},
		{},
	),
	(
		"open ended: LEGACY bare lists and bare strings",
		"OpenEnded",
		{
			"prompt_text": "Ποιος;",
			"min_correct_answers": 1,
			"texts": [["Α", "Β"], "Γ"],
		},
		{},
	),
	(
		"map pointer: the current areas list",
		"MapPointer",
		{
			"prompt_text": "Πού;",
			"show_answers": True,
			"min_correct_answers": 1,
			"texts": [{"alternatives": ["Αλιάκμονας"], "areas": [AREA_A, AREA_B]}],
		},
		{"level": 3},
	),
	(
		"map pointer: LEGACY single area as a string (pre-0015)",
		"MapPointer",
		{
			"prompt_text": "Πού;",
			"show_answers": True,
			"min_correct_answers": 1,
			"texts": [{"alternatives": ["Αλιάκμονας"], "area": AREA_A}],
		},
		{"level": 3},
	),
	(
		"map pointer: LEGACY single area as an object",
		"MapPointer",
		{
			"prompt_text": "Πού;",
			"show_answers": True,
			"min_correct_answers": 1,
			"texts": [{"alternatives": ["Αλιάκμονας"], "area": {"name": AREA_B}}],
		},
		{"level": 3},
	),
	(
		"map pointer: an answer with no areas omits the key",
		"MapPointer",
		{
			"prompt_text": "Πού;",
			"show_answers": False,
			"min_correct_answers": 1,
			"texts": [{"alternatives": ["Αλιάκμονας"]}],
		},
		{"level": 3},
	),
	(
		"map pointer: two answers sharing an area",
		"MapPointer",
		{
			"prompt_text": "Πού;",
			"show_answers": True,
			"min_correct_answers": 2,
			"texts": [
				{"alternatives": ["Αλιάκμονας"], "areas": [AREA_A, AREA_B]},
				{"alternatives": ["Αξιός"], "areas": [AREA_A]},
			],
		},
		{"level": 3},
	),
]

SERIALIZERS = {
	"Statement": (Statement, StatementSerializer),
	"DragAndDrop": (DragAndDrop, DragAndDropSerializer),
	"Matching": (Matching, MatchingSerializer),
	"FillInTheBlank": (FillInTheBlank, FillInTheBlankSerializer),
	"OpenEnded": (OpenEnded, OpenEndedSerializer),
	"MapPointer": (MapPointer, MapPointerSerializer),
}

MIGRATE_FROM = [("quiz", "0021_quiz_content_tables")]
MIGRATE_TO = [("quiz", "0022_backfill_quiz_content")]


class BackfillEquivalenceTests(TransactionTestCase):
	"""Seed legacy rows, run the real migration, compare to the old serializer.

	``TransactionTestCase`` because this migrates the database, which cannot
	happen inside the transaction ``TestCase`` wraps each test in.
	"""

	# Recreate the categories the rows point at after the rollback truncates.
	serialized_rollback = True

	def _migrate(self, targets):
		executor = MigrationExecutor(connection)
		executor.loader.build_graph()
		executor.migrate(targets)
		executor.loader.build_graph()
		return executor

	def test_every_corpus_shape_survives_the_migration_unchanged(self):
		# 1. back to the state before any content was copied
		executor = self._migrate(MIGRATE_FROM)
		old_apps = executor.loader.project_state(MIGRATE_FROM).apps

		OldQuizAsset = old_apps.get_model("quiz", "QuizAsset")
		image_asset = OldQuizAsset.objects.create(title="pic", image="quizzes/pic.png")

		def resolve(content):
			"""Swap the ``"IMAGE"`` placeholder for the real asset id."""
			if isinstance(content, dict):
				return {key: resolve(value) for key, value in content.items()}
			if isinstance(content, list):
				return [resolve(item) for item in content]
			return image_asset.pk if content == "IMAGE" else content

		# 2. seed one pre-migration row per corpus entry, through historical
		#    models, so nothing validates or normalises them on the way in
		seeded = []
		for label, model_name, content, extra in CONTENT_CORPUS:
			content = resolve(content)
			row = old_apps.get_model("quiz", model_name).objects.create(
				category_id="GEOGRAPHY", content=content, **extra
			)
			seeded.append((label, model_name, content, row.pk))

		# 3. run the migration for real — backfill and its verify step
		self._migrate(MIGRATE_TO)

		# 4. the live serializer must agree with the deleted one, per shape
		failures = []
		for label, model_name, content, pk in seeded:
			model, serializer_class = SERIALIZERS[model_name]
			actual = serializer_class(model.objects.get(pk=pk)).data["content"]
			expected = reference_content(model_name, content)
			if model_name == "Matching":
				actual = matching_relation(actual)
				expected = matching_relation(expected)
			if actual != expected:
				failures.append(f"{label}\n  was: {expected}\n  now: {actual}")

		self.assertEqual(
			failures,
			[],
			"the content tables changed what the client receives:\n\n"
			+ "\n\n".join(failures),
		)

	def test_the_corpus_covers_every_type_that_had_a_content_column(self):
		"""A type missing from the corpus is a type nothing above proves."""
		self.assertEqual(
			sorted({model_name for _, model_name, _, _ in CONTENT_CORPUS}),
			sorted(SERIALIZERS),
		)


class KnownDeviationTests(TransactionTestCase):
	"""The places the output deliberately differs, asserted rather than hidden.

	A JSON key that was absent came back as ``null``; a column cannot be absent,
	so empty stands in for unset and is reported the same way. A value
	deliberately stored as ``""`` therefore now reports as ``null`` too. Both are
	falsy to the client, and the original JSON is still on the row — but it is a
	difference, so it is written down.
	"""

	serialized_rollback = True

	def test_an_explicitly_empty_prompt_becomes_null(self):
		executor = MigrationExecutor(connection)
		executor.loader.build_graph()
		executor.migrate(MIGRATE_FROM)
		old_apps = executor.loader.project_state(MIGRATE_FROM).apps

		content = {"prompt_text": "", "choices": [{"text": "Α", "is_correct": True}]}
		pk = (
			old_apps.get_model("quiz", "Statement")
			.objects.create(category_id="GEOGRAPHY", type="TRUE_FALSE", content=content)
			.pk
		)

		executor.loader.build_graph()
		executor.migrate(MIGRATE_TO)

		# The old serializer passed the empty string straight through.
		self.assertEqual(reference_content("Statement", content)["prompt_text"], "")
		# The new one reports it the way it reports an absent key.
		actual = StatementSerializer(Statement.objects.get(pk=pk)).data["content"]
		self.assertIsNone(actual["prompt_text"])
		# Everything else about the row is untouched.
		self.assertEqual(
			actual["choices"],
			reference_content("Statement", content)["choices"],
		)

	def test_a_numeric_choice_becomes_the_string_the_client_displayed(self):
		"""Excel imports stored some choices as JSON numbers; a column holds text.

		The old serializer sent the number and the client printed it the way
		JavaScript does, so that printed form is what the row now holds.
		"""
		executor = MigrationExecutor(connection)
		executor.loader.build_graph()
		executor.migrate(MIGRATE_FROM)
		old_apps = executor.loader.project_state(MIGRATE_FROM).apps

		content = {
			"prompt_text": "Πόσες;",
			"choices": [
				{"text": 45.0, "is_correct": False},
				{"text": 0.05, "is_correct": False},
				{"text": 0, "is_correct": False},
				{"text": 1952, "is_correct": True},
				{"text": "καμία", "is_correct": False},
			],
		}
		pk = (
			old_apps.get_model("quiz", "Statement")
			.objects.create(
				category_id="GEOGRAPHY", type="MULTIPLE_CHOICE", content=content
			)
			.pk
		)

		executor.loader.build_graph()
		executor.migrate(MIGRATE_TO)

		actual = StatementSerializer(Statement.objects.get(pk=pk)).data["content"]
		self.assertEqual(
			[choice["text"] for choice in actual["choices"]],
			["45", "0.05", "0", "1952", "καμία"],
		)
