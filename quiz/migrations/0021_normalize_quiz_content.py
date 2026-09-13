"""Replace the JSON ``content`` columns with real tables, in one migration.

Operation order matters and is not what ``makemigrations`` produced — the
autodetector puts the ``RemoveField``s first, which would drop the JSON before
anything could read it. Here it is:

	1. add the new columns and tables (nothing reads them yet)
	2. seed ``MapArea`` from the GeoJSON the frontend draws
	3. backfill every row from its JSON
	4. verify the new rows reproduce the old content, raising if not
	5. only then drop the JSON columns

SQLite has ``can_rollback_ddl = True``, so the whole thing is one transaction:
if step 4 raises, steps 1-3 are rolled back too and the JSON is still there. That
is what makes it safe to do the drop in the same migration as the backfill.

**Everything this migration needs is frozen into this file** — the parsers, the
GeoJSON source map, the accent folding. Nothing is imported from ``quiz.schemas``
or ``quiz.models``: this migration deletes the code it would otherwise import, so
an import would break ``migrate`` on a fresh database the moment that code
changes. The duplication is deliberate.
"""

import json
import re
import unicodedata
from pathlib import Path

import django.db.models.deletion
from django.db import migrations, models

# ---------------------------------------------------------------------------
# Frozen copies of things that live in quiz/ and will change after this.
# ---------------------------------------------------------------------------

MAP_LEVEL_SOURCES = {
	1: ("gadm41_GRC_1.json", "NL_NAME_1"),
	2: ("gadm41_GRC_2.json", "NL_NAME_2"),
	3: ("greece_prefecture_units.json", "name_greek"),
	4: ("gadm41_GRC_3.json", "NL_NAME_3"),
	5: ("greece_geographic_departments.json", "name"),
}

GEO_DATA_DIR = (
	Path(__file__).resolve().parent.parent.parent / "frontend" / "js" / "geo" / "data"
)

BLANK_PATTERN = re.compile(r"<(.+?)>")
CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")


def fold_for_search(text):
	stripped = "".join(
		char
		for char in unicodedata.normalize("NFD", text or "")
		if not unicodedata.combining(char)
	)
	return unicodedata.normalize("NFC", stripped).strip().casefold()


def load_area_names(level):
	filename, name_key = MAP_LEVEL_SOURCES[level]
	with open(GEO_DATA_DIR / filename, encoding="utf-8") as f:
		data = json.load(f)
	return sorted({feat["properties"][name_key] for feat in data["features"]})


def _parse_areas(raw):
	"""Normalise a stored area reference into a list of names.

	Absorbs every shape the field has ever held: the current list, the legacy
	single ``area`` string, and the older ``{"name": ...}`` object. After this
	migration only one shape exists, so this tolerance dies here rather than
	living in the model layer forever.
	"""
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
			areas.extend(_parse_areas(item))
		return areas
	return []


def _parse_alternatives(entry):
	"""One answer group's alternatives, from any shape ``texts`` has held."""
	if isinstance(entry, dict):
		alts = entry.get("alternatives", [])
		if not alts and "text" in entry:
			# Legacy single-text dict, pre-migration 0003.
			alts = [entry["text"]]
		return list(alts)
	if isinstance(entry, list):
		return list(entry)
	if isinstance(entry, str):
		return [entry]
	return [str(entry)]


def _matching_columns(content):
	"""The two columns of a Matching row, from the object or the legacy bare list."""
	if isinstance(content, list):
		return content
	if isinstance(content, dict):
		return content.get("columns", [])
	return []


# ---------------------------------------------------------------------------
# Canonical comparison payloads.
#
# Both sides of the verification build the same structure — one from the JSON
# about to be dropped, one from the rows just written. Assets are compared by id
# rather than by resolved URL: the URL is a pure function of the id and the
# storage backend, and a migration has no business touching the filesystem.
# ---------------------------------------------------------------------------


def _statement_from_json(content):
	return {
		"prompt_text": content.get("prompt_text") or None,
		"prompt_image": content.get("prompt_asset_id") or None,
		"prompt_audio": content.get("prompt_audio_asset_id") or None,
		"choices": [
			{
				"text": choice.get("text") or None,
				"image": choice.get("asset_id") or None,
				"is_correct": bool(choice.get("is_correct", False)),
			}
			for choice in content.get("choices", [])
		],
	}


def _statement_from_rows(statement, choices):
	return {
		"prompt_text": statement.prompt_text or None,
		"prompt_image": statement.prompt_image_id or None,
		"prompt_audio": statement.prompt_audio_id or None,
		"choices": [
			{
				"text": choice.text or None,
				"image": choice.image_id or None,
				"is_correct": choice.is_correct,
			}
			for choice in choices
		],
	}


def _dnd_from_json(content):
	return [
		{"title": col.get("title") or None, "values": list(col.get("values", []))}
		for col in content
	]


def _dnd_from_rows(question, values):
	out = []
	for side, title in (("LEFT", question.left_title), ("RIGHT", question.right_title)):
		out.append(
			{
				"title": title or None,
				"values": [v.text for v in values if v.side == side],
			}
		)
	return out


def _matching_from_json(content):
	columns = _matching_columns(content)
	left_items = columns[0].get("items", []) if len(columns) > 0 else []
	right_items = columns[1].get("items", []) if len(columns) > 1 else []
	right_by_id = {item.get("id"): item for item in right_items}

	pairs = []
	for item in left_items:
		partner = right_by_id.get(item.get("matched_id"), {})
		pairs.append(
			{
				"left_text": item.get("text") or None,
				"left_image": item.get("asset_id") or None,
				"right_text": partner.get("text") or None,
				"right_image": partner.get("asset_id") or None,
			}
		)

	return {
		"prompt_text": (
			content.get("prompt_text") if isinstance(content, dict) else None
		)
		or None,
		"left_title": (columns[0].get("title") if len(columns) > 0 else None) or None,
		"right_title": (columns[1].get("title") if len(columns) > 1 else None) or None,
		"pairs": pairs,
	}


def _matching_from_rows(question, pairs):
	return {
		"prompt_text": question.prompt_text or None,
		"left_title": question.left_title or None,
		"right_title": question.right_title or None,
		"pairs": [
			{
				"left_text": pair.left_text or None,
				"left_image": pair.left_image_id or None,
				"right_text": pair.right_text or None,
				"right_image": pair.right_image_id or None,
			}
			for pair in pairs
		],
	}


def _fitb_from_json(content):
	return {
		"show_answers_as_choices": bool(content.get("show_answers_as_choices", False)),
		"prompt_image": content.get("prompt_asset_id") or None,
		"texts": [t.get("text", "") for t in content.get("texts", [])],
		"extra_choices": list(content.get("extra_choices", [])),
	}


def _fitb_from_rows(question, texts, extra_choices):
	return {
		"show_answers_as_choices": question.show_answers_as_choices,
		"prompt_image": question.prompt_image_id or None,
		"texts": [t.text for t in texts],
		"extra_choices": [c.text for c in extra_choices],
	}


def _open_ended_from_json(content):
	return {
		"prompt_text": content.get("prompt_text") or None,
		"prompt_image": content.get("prompt_asset_id") or None,
		"min_correct_answers": content.get("min_correct_answers", 0),
		"texts": [_parse_alternatives(t) for t in content.get("texts", [])],
	}


def _open_ended_from_rows(question, answers):
	return {
		"prompt_text": question.prompt_text or None,
		"prompt_image": question.prompt_image_id or None,
		"min_correct_answers": question.min_correct_answers,
		"texts": [
			[alt.text for alt in answer.alternatives.all()] for answer in answers
		],
	}


def _map_pointer_from_json(content):
	groups = []
	for entry in content.get("texts", []):
		raw_areas = (
			entry.get("areas", entry.get("area")) if isinstance(entry, dict) else None
		)
		groups.append(
			{
				"alternatives": _parse_alternatives(entry),
				"areas": _parse_areas(raw_areas),
			}
		)
	return {
		"prompt_text": content.get("prompt_text") or None,
		"show_answers": bool(content.get("show_answers", True)),
		"min_correct_answers": content.get("min_correct_answers", 0),
		"texts": groups,
	}


def _map_pointer_from_rows(question, answers):
	return {
		"prompt_text": question.prompt_text or None,
		"show_answers": question.show_answers,
		"min_correct_answers": question.min_correct_answers,
		"texts": [
			{
				"alternatives": [alt.text for alt in answer.alternatives.all()],
				"areas": [link.area.name for link in answer.areas.all()],
			}
			for answer in answers
		],
	}


# ---------------------------------------------------------------------------
# Step 2 — seed MapArea
# ---------------------------------------------------------------------------


def seed_map_areas(apps, schema_editor):
	MapArea = apps.get_model("quiz", "MapArea")

	# Historical models carry no custom save(), so search_name is computed here
	# rather than by the model.
	MapArea.objects.bulk_create(
		[
			MapArea(level=level, name=name, search_name=fold_for_search(name))
			for level in sorted(MAP_LEVEL_SOURCES)
			for name in load_area_names(level)
		]
	)


def unseed_map_areas(apps, schema_editor):
	# The links are PROTECTed, and on the way back they still exist here: their
	# table is not dropped until the CreateModel operations are reversed, which
	# happens after this. ``restore_json`` has already written the area names back
	# into the JSON by now, so clearing them loses nothing.
	apps.get_model("quiz", "MapPointerAnswerArea").objects.all().delete()
	apps.get_model("quiz", "MapArea").objects.all().delete()


# ---------------------------------------------------------------------------
# Step 3 — backfill
# ---------------------------------------------------------------------------


def backfill(apps, schema_editor):
	_backfill_statements(apps)
	_backfill_drag_and_drop(apps)
	_backfill_matching(apps)
	_backfill_fill_in_the_blank(apps)
	_backfill_open_ended(apps)
	_backfill_map_pointer(apps)


def _backfill_statements(apps):
	Statement = apps.get_model("quiz", "Statement")
	StatementChoice = apps.get_model("quiz", "StatementChoice")

	choices = []
	for statement in Statement.objects.all():
		content = statement.content or {}
		statement.prompt_text = content.get("prompt_text") or ""
		statement.prompt_image_id = content.get("prompt_asset_id") or None
		statement.prompt_audio_id = content.get("prompt_audio_asset_id") or None
		statement.save(update_fields=["prompt_text", "prompt_image", "prompt_audio"])

		for order, choice in enumerate(content.get("choices", [])):
			choices.append(
				StatementChoice(
					statement_id=statement.pk,
					text=choice.get("text") or "",
					image_id=choice.get("asset_id") or None,
					is_correct=bool(choice.get("is_correct", False)),
					order=order,
				)
			)

	StatementChoice.objects.bulk_create(choices)


def _backfill_drag_and_drop(apps):
	DragAndDrop = apps.get_model("quiz", "DragAndDrop")
	DragAndDropValue = apps.get_model("quiz", "DragAndDropValue")

	values = []
	for question in DragAndDrop.objects.all():
		columns = question.content or []
		question.left_title = (
			columns[0].get("title") if len(columns) > 0 else ""
		) or ""
		question.right_title = (
			columns[1].get("title") if len(columns) > 1 else ""
		) or ""
		question.save(update_fields=["left_title", "right_title"])

		for side, index in (("LEFT", 0), ("RIGHT", 1)):
			if index >= len(columns):
				continue
			for order, text in enumerate(columns[index].get("values", [])):
				values.append(
					DragAndDropValue(
						question_id=question.pk, side=side, text=text, order=order
					)
				)

	DragAndDropValue.objects.bulk_create(values)


def _backfill_matching(apps):
	Matching = apps.get_model("quiz", "Matching")
	MatchPair = apps.get_model("quiz", "MatchPair")

	pairs = []
	for question in Matching.objects.all():
		content = question.content or {}
		columns = _matching_columns(content)

		question.prompt_text = (
			content.get("prompt_text") if isinstance(content, dict) else ""
		) or ""
		question.left_title = (
			columns[0].get("title") if len(columns) > 0 else ""
		) or ""
		question.right_title = (
			columns[1].get("title") if len(columns) > 1 else ""
		) or ""
		question.save(update_fields=["prompt_text", "left_title", "right_title"])

		left_items = columns[0].get("items", []) if len(columns) > 0 else []
		right_items = columns[1].get("items", []) if len(columns) > 1 else []
		right_by_id = {item.get("id"): item for item in right_items}

		for order, item in enumerate(left_items):
			# Pair by the stored matched_id rather than by position: the two are
			# the same in every row today, but the id is what actually carried the
			# meaning, so it is what gets trusted.
			partner = right_by_id.get(item.get("matched_id"))
			if partner is None:
				raise RuntimeError(
					f"Matching {question.pk}: left item id={item.get('id')} points at "
					f"matched_id={item.get('matched_id')}, which is not in the right "
					f"column. Fix the row before migrating."
				)
			pairs.append(
				MatchPair(
					question_id=question.pk,
					left_text=item.get("text") or "",
					left_image_id=item.get("asset_id") or None,
					right_text=partner.get("text") or "",
					right_image_id=partner.get("asset_id") or None,
					order=order,
				)
			)

	MatchPair.objects.bulk_create(pairs)


def _backfill_fill_in_the_blank(apps):
	FillInTheBlank = apps.get_model("quiz", "FillInTheBlank")
	FillInTheBlankText = apps.get_model("quiz", "FillInTheBlankText")
	FillInTheBlankExtraChoice = apps.get_model("quiz", "FillInTheBlankExtraChoice")

	texts = []
	extra_choices = []
	for question in FillInTheBlank.objects.all():
		content = question.content or {}
		question.show_answers_as_choices = bool(
			content.get("show_answers_as_choices", False)
		)
		question.prompt_image_id = content.get("prompt_asset_id") or None
		question.save(update_fields=["show_answers_as_choices", "prompt_image"])

		for order, entry in enumerate(content.get("texts", [])):
			texts.append(
				FillInTheBlankText(
					question_id=question.pk, text=entry.get("text", ""), order=order
				)
			)
		for order, text in enumerate(content.get("extra_choices", [])):
			extra_choices.append(
				FillInTheBlankExtraChoice(
					question_id=question.pk, text=text, order=order
				)
			)

	FillInTheBlankText.objects.bulk_create(texts)
	FillInTheBlankExtraChoice.objects.bulk_create(extra_choices)


def _backfill_open_ended(apps):
	OpenEnded = apps.get_model("quiz", "OpenEnded")
	OpenEndedAnswer = apps.get_model("quiz", "OpenEndedAnswer")
	OpenEndedAlternative = apps.get_model("quiz", "OpenEndedAlternative")

	alternatives = []
	for question in OpenEnded.objects.all():
		content = question.content or {}
		question.prompt_text = content.get("prompt_text") or ""
		question.prompt_image_id = content.get("prompt_asset_id") or None
		# Kept exactly as stored, including a 0 that the new validation would
		# reject: changing it here would change what the client is served. A row
		# like that surfaces the next time someone saves it.
		question.min_correct_answers = content.get("min_correct_answers", 0)
		question.save(
			update_fields=["prompt_text", "prompt_image", "min_correct_answers"]
		)

		for order, entry in enumerate(content.get("texts", [])):
			answer = OpenEndedAnswer.objects.create(
				question_id=question.pk, order=order
			)
			for alt_order, text in enumerate(_parse_alternatives(entry)):
				alternatives.append(
					OpenEndedAlternative(
						answer_id=answer.pk, text=text, order=alt_order
					)
				)

	OpenEndedAlternative.objects.bulk_create(alternatives)


def _backfill_map_pointer(apps):
	MapPointer = apps.get_model("quiz", "MapPointer")
	MapPointerAnswer = apps.get_model("quiz", "MapPointerAnswer")
	MapPointerAlternative = apps.get_model("quiz", "MapPointerAlternative")
	MapPointerAnswerArea = apps.get_model("quiz", "MapPointerAnswerArea")
	MapArea = apps.get_model("quiz", "MapArea")

	# (level, name) → pk, so resolving an answer's areas is not a query per area.
	area_ids = {
		(level, name): pk
		for pk, level, name in MapArea.objects.values_list("pk", "level", "name")
	}

	alternatives = []
	links = []
	for question in MapPointer.objects.all():
		content = question.content or {}
		question.prompt_text = content.get("prompt_text") or ""
		question.show_answers = bool(content.get("show_answers", True))
		question.min_correct_answers = content.get("min_correct_answers", 0)
		question.save(
			update_fields=["prompt_text", "show_answers", "min_correct_answers"]
		)

		for order, entry in enumerate(content.get("texts", [])):
			answer = MapPointerAnswer.objects.create(
				question_id=question.pk, order=order
			)
			for alt_order, text in enumerate(_parse_alternatives(entry)):
				alternatives.append(
					MapPointerAlternative(
						answer_id=answer.pk, text=text, order=alt_order
					)
				)

			raw_areas = (
				entry.get("areas", entry.get("area"))
				if isinstance(entry, dict)
				else None
			)
			seen = set()
			for area_order, name in enumerate(_parse_areas(raw_areas)):
				area_id = area_ids.get((question.level, name))
				if area_id is None:
					# The answer points at an area name that no longer exists in the
					# GeoJSON — exactly the silent breakage this refactor exists to
					# make visible. Failing here rolls the whole migration back and
					# leaves the JSON intact, which is better than dropping the
					# answer on the floor.
					raise RuntimeError(
						f"MapPointer {question.pk}: area '{name}' does not exist at "
						f"level {question.level}. Fix the row (or re-run the area "
						f"sync) before migrating."
					)
				if area_id in seen:
					continue
				seen.add(area_id)
				links.append(
					MapPointerAnswerArea(
						answer_id=answer.pk, area_id=area_id, order=area_order
					)
				)

	MapPointerAlternative.objects.bulk_create(alternatives)
	MapPointerAnswerArea.objects.bulk_create(links)


# ---------------------------------------------------------------------------
# Step 4 — verify, while the JSON is still there to compare against
# ---------------------------------------------------------------------------


def verify(apps, schema_editor):
	"""Rebuild each row's content from the new tables and compare it to the JSON
	that is about to be dropped.

	Raising here aborts the transaction, which on SQLite takes the schema changes
	with it — the database ends up untouched, JSON column included. Rows whose
	JSON is empty are skipped: they could not be serialized before this migration
	either (the old parsers raised on them), so there is nothing to preserve.
	"""
	checks = [
		("Statement", _statement_from_json, _verify_statement),
		("DragAndDrop", _dnd_from_json, _verify_dnd),
		("Matching", _matching_from_json, _verify_matching),
		("FillInTheBlank", _fitb_from_json, _verify_fitb),
		("OpenEnded", _open_ended_from_json, _verify_open_ended),
		("MapPointer", _map_pointer_from_json, _verify_map_pointer),
	]

	mismatches = []
	compared = 0
	for model_name, from_json, from_rows in checks:
		model = apps.get_model("quiz", model_name)
		for instance in model.objects.all():
			if not instance.content:
				continue
			compared += 1
			expected = from_json(instance.content)
			actual = from_rows(apps, instance)
			if expected != actual:
				mismatches.append(
					f"{model_name} pk={instance.pk}\n"
					f"    from JSON: {json.dumps(expected, ensure_ascii=False)}\n"
					f"    from rows: {json.dumps(actual, ensure_ascii=False)}"
				)

	if mismatches:
		raise RuntimeError(
			"Backfill did not reproduce the stored content; rolling back.\n"
			+ "\n".join(mismatches)
		)

	print(f"  verified {compared} rows reproduce their JSON content")


def _verify_statement(apps, instance):
	choices = (
		apps.get_model("quiz", "StatementChoice")
		.objects.filter(statement_id=instance.pk)
		.order_by("order", "id")
	)
	return _statement_from_rows(instance, choices)


def _verify_dnd(apps, instance):
	values = (
		apps.get_model("quiz", "DragAndDropValue")
		.objects.filter(question_id=instance.pk)
		.order_by("order", "id")
	)
	return _dnd_from_rows(instance, values)


def _verify_matching(apps, instance):
	pairs = (
		apps.get_model("quiz", "MatchPair")
		.objects.filter(question_id=instance.pk)
		.order_by("order", "id")
	)
	return _matching_from_rows(instance, pairs)


def _verify_fitb(apps, instance):
	texts = (
		apps.get_model("quiz", "FillInTheBlankText")
		.objects.filter(question_id=instance.pk)
		.order_by("order", "id")
	)
	extra = (
		apps.get_model("quiz", "FillInTheBlankExtraChoice")
		.objects.filter(question_id=instance.pk)
		.order_by("order", "id")
	)
	return _fitb_from_rows(instance, texts, extra)


def _verify_open_ended(apps, instance):
	answers = (
		apps.get_model("quiz", "OpenEndedAnswer")
		.objects.filter(question_id=instance.pk)
		.order_by("order", "id")
		.prefetch_related("alternatives")
	)
	return _open_ended_from_rows(instance, answers)


def _verify_map_pointer(apps, instance):
	answers = (
		apps.get_model("quiz", "MapPointerAnswer")
		.objects.filter(question_id=instance.pk)
		.order_by("order", "id")
		.prefetch_related("alternatives", "areas__area")
	)
	return _map_pointer_from_rows(instance, answers)


# ---------------------------------------------------------------------------
# Reverse — rebuild the JSON from the rows.
#
# Runs after RemoveField has been reversed (so ``content`` exists again, empty)
# and before the tables are dropped. Emits the canonical shape only: the legacy
# variants absorbed on the way forward are not recreated.
# ---------------------------------------------------------------------------


def restore_json(apps, schema_editor):
	_restore_statements(apps)
	_restore_drag_and_drop(apps)
	_restore_matching(apps)
	_restore_fill_in_the_blank(apps)
	_restore_open_ended(apps)
	_restore_map_pointer(apps)


def _restore_statements(apps):
	Statement = apps.get_model("quiz", "Statement")
	for statement in Statement.objects.prefetch_related("choices"):
		statement.content = {
			"prompt_text": statement.prompt_text or None,
			"prompt_asset_id": statement.prompt_image_id,
			"prompt_audio_asset_id": statement.prompt_audio_id,
			"choices": [
				{
					"text": choice.text or None,
					"asset_id": choice.image_id,
					"is_correct": choice.is_correct,
				}
				for choice in statement.choices.all()
			],
		}
		statement.save(update_fields=["content"])


def _restore_drag_and_drop(apps):
	DragAndDrop = apps.get_model("quiz", "DragAndDrop")
	for question in DragAndDrop.objects.prefetch_related("values"):
		values = list(question.values.all())
		question.content = [
			{
				"title": question.left_title,
				"values": [v.text for v in values if v.side == "LEFT"],
			},
			{
				"title": question.right_title,
				"values": [v.text for v in values if v.side == "RIGHT"],
			},
		]
		question.save(update_fields=["content"])


def _restore_matching(apps):
	Matching = apps.get_model("quiz", "Matching")
	for question in Matching.objects.prefetch_related("pairs"):
		pairs = list(question.pairs.all())
		count = len(pairs)
		question.content = {
			"prompt_text": question.prompt_text or None,
			"columns": [
				{
					"title": question.left_title or None,
					"items": [
						{
							"id": index + 1,
							"matched_id": index + 1 + count,
							"text": pair.left_text or None,
							"asset_id": pair.left_image_id,
						}
						for index, pair in enumerate(pairs)
					],
				},
				{
					"title": question.right_title or None,
					"items": [
						{
							"id": index + 1 + count,
							"matched_id": index + 1,
							"text": pair.right_text or None,
							"asset_id": pair.right_image_id,
						}
						for index, pair in enumerate(pairs)
					],
				},
			],
		}
		question.save(update_fields=["content"])


def _restore_fill_in_the_blank(apps):
	FillInTheBlank = apps.get_model("quiz", "FillInTheBlank")
	for question in FillInTheBlank.objects.prefetch_related("texts", "extra_choices"):
		question.content = {
			"show_answers_as_choices": question.show_answers_as_choices,
			"prompt_asset_id": question.prompt_image_id,
			"texts": [{"text": t.text} for t in question.texts.all()],
			"extra_choices": [c.text for c in question.extra_choices.all()],
		}
		question.save(update_fields=["content"])


def _restore_open_ended(apps):
	OpenEnded = apps.get_model("quiz", "OpenEnded")
	for question in OpenEnded.objects.prefetch_related("answers__alternatives"):
		question.content = {
			"prompt_text": question.prompt_text or None,
			"prompt_asset_id": question.prompt_image_id,
			"min_correct_answers": question.min_correct_answers,
			"texts": [
				{"alternatives": [alt.text for alt in answer.alternatives.all()]}
				for answer in question.answers.all()
			],
		}
		question.save(update_fields=["content"])


def _restore_map_pointer(apps):
	MapPointer = apps.get_model("quiz", "MapPointer")
	for question in MapPointer.objects.prefetch_related(
		"answers__alternatives", "answers__areas__area"
	):
		question.content = {
			"prompt_text": question.prompt_text or None,
			"show_answers": question.show_answers,
			"min_correct_answers": question.min_correct_answers,
			"texts": [
				{
					"alternatives": [alt.text for alt in answer.alternatives.all()],
					"areas": [link.area.name for link in answer.areas.all()],
				}
				for answer in question.answers.all()
			],
		}
		question.save(update_fields=["content"])


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0020_draganddrop_test_number_fillintheblank_test_number_and_more"),
	]

	operations = [
		# --- 1. new columns -------------------------------------------------
		migrations.AddField(
			model_name="draganddrop",
			name="left_title",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="draganddrop",
			name="right_title",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="draganddrop",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="draganddrop",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="draganddrop",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="fillintheblank",
			name="show_answers_as_choices",
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name="fillintheblank",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="fillintheblank",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="fillintheblank",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="listening",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="listening",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="listening",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="mappointer",
			name="min_correct_answers",
			field=models.PositiveSmallIntegerField(default=1),
		),
		migrations.AddField(
			model_name="mappointer",
			name="show_answers",
			field=models.BooleanField(default=True),
		),
		migrations.AddField(
			model_name="mappointer",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="mappointer",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="mappointer",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="matching",
			name="left_title",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="matching",
			name="right_title",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="matching",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="matching",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="matching",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="openended",
			name="min_correct_answers",
			field=models.PositiveSmallIntegerField(default=1),
		),
		migrations.AddField(
			model_name="openended",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="openended",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="openended",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="statement",
			name="prompt_text",
			field=models.TextField(blank=True, default=""),
		),
		migrations.AddField(
			model_name="statement",
			name="prompt_image",
			field=models.ForeignKey(
				blank=True,
				help_text="Image shown with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		migrations.AddField(
			model_name="statement",
			name="prompt_audio",
			field=models.ForeignKey(
				blank=True,
				help_text="Audio played with the question.",
				null=True,
				on_delete=django.db.models.deletion.PROTECT,
				related_name="+",
				to="quiz.quizasset",
			),
		),
		# --- 1b. new tables -------------------------------------------------
		migrations.CreateModel(
			name="MapArea",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				(
					"level",
					models.PositiveSmallIntegerField(
						choices=[
							(
								1,
								"Decentralized administration (Αποκεντρωμένη διοίκηση)",
							),
							(2, "Region (Περιφέρεια)"),
							(3, "Prefecture unit (Νομός / Νησί)"),
							(4, "Municipality and islands (Δήμος και νησιά)"),
							(5, "Geographic department (Γεωγραφικό διαμέρισμα)"),
						]
					),
				),
				("name", models.CharField(max_length=255)),
				(
					"search_name",
					models.CharField(
						db_index=True,
						editable=False,
						help_text="Accent-stripped, casefolded name, for the area picker.",
						max_length=255,
					),
				),
			],
			options={
				"verbose_name": "Map area",
				"verbose_name_plural": "Map areas",
				"ordering": ["level", "name"],
				"constraints": [
					models.UniqueConstraint(
						fields=("level", "name"), name="unique_map_area_per_level"
					)
				],
			},
		),
		migrations.CreateModel(
			name="StatementChoice",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("text", models.TextField(blank=True, default="")),
				("is_correct", models.BooleanField(default=False)),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"image",
					models.ForeignKey(
						blank=True,
						null=True,
						on_delete=django.db.models.deletion.PROTECT,
						related_name="+",
						to="quiz.quizasset",
					),
				),
				(
					"statement",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="choices",
						to="quiz.statement",
					),
				),
			],
			options={
				"verbose_name": "Statement choice",
				"verbose_name_plural": "Statement choices",
				"ordering": ["order", "id"],
				"constraints": [
					models.CheckConstraint(
						condition=models.Q(
							models.Q(("text", ""), _negated=True),
							("image__isnull", False),
							_connector="OR",
						),
						name="statement_choice_has_text_or_image",
					)
				],
			},
		),
		migrations.CreateModel(
			name="DragAndDropValue",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				(
					"side",
					models.CharField(
						choices=[("LEFT", "Left"), ("RIGHT", "Right")], max_length=5
					),
				),
				("text", models.TextField()),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"question",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="values",
						to="quiz.draganddrop",
					),
				),
			],
			options={
				"verbose_name": "Drag and drop value",
				"verbose_name_plural": "Drag and drop values",
				"ordering": ["side", "order", "id"],
			},
		),
		migrations.CreateModel(
			name="MatchPair",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("left_text", models.TextField(blank=True, default="")),
				("right_text", models.TextField(blank=True, default="")),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"left_image",
					models.ForeignKey(
						blank=True,
						null=True,
						on_delete=django.db.models.deletion.PROTECT,
						related_name="+",
						to="quiz.quizasset",
					),
				),
				(
					"question",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="pairs",
						to="quiz.matching",
					),
				),
				(
					"right_image",
					models.ForeignKey(
						blank=True,
						null=True,
						on_delete=django.db.models.deletion.PROTECT,
						related_name="+",
						to="quiz.quizasset",
					),
				),
			],
			options={
				"verbose_name": "Match pair",
				"verbose_name_plural": "Match pairs",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="FillInTheBlankText",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				(
					"text",
					models.TextField(
						help_text="Use <{{answer1}}*, {{answer2}}> for blanks, marking the correct one with *. E.g. Η Κως συνορεύει με <{{την Τουρκία}}*>"
					),
				),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"question",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="texts",
						to="quiz.fillintheblank",
					),
				),
			],
			options={
				"verbose_name": "Fill in the blank text",
				"verbose_name_plural": "Fill in the blank texts",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="FillInTheBlankExtraChoice",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("text", models.TextField()),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"question",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="extra_choices",
						to="quiz.fillintheblank",
					),
				),
			],
			options={
				"verbose_name": "Fill in the blank extra choice",
				"verbose_name_plural": "Fill in the blank extra choices",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="OpenEndedAnswer",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"question",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="answers",
						to="quiz.openended",
					),
				),
			],
			options={
				"verbose_name": "Open ended answer",
				"verbose_name_plural": "Open ended answers",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="OpenEndedAlternative",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("text", models.TextField()),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"answer",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="alternatives",
						to="quiz.openendedanswer",
					),
				),
			],
			options={
				"verbose_name": "Open ended alternative",
				"verbose_name_plural": "Open ended alternatives",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="MapPointerAnswer",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"question",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="answers",
						to="quiz.mappointer",
					),
				),
			],
			options={
				"verbose_name": "Map pointer answer",
				"verbose_name_plural": "Map pointer answers",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="MapPointerAlternative",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("text", models.TextField()),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"answer",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="alternatives",
						to="quiz.mappointeranswer",
					),
				),
			],
			options={
				"verbose_name": "Map pointer alternative",
				"verbose_name_plural": "Map pointer alternatives",
				"ordering": ["order", "id"],
			},
		),
		migrations.CreateModel(
			name="MapPointerAnswerArea",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("order", models.PositiveSmallIntegerField(default=0)),
				(
					"answer",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="areas",
						to="quiz.mappointeranswer",
					),
				),
				(
					"area",
					models.ForeignKey(
						on_delete=django.db.models.deletion.PROTECT,
						related_name="answers",
						to="quiz.maparea",
					),
				),
			],
			options={
				"verbose_name": "Map pointer answer area",
				"verbose_name_plural": "Map pointer answer areas",
				"ordering": ["order", "id"],
				"constraints": [
					models.UniqueConstraint(
						fields=("answer", "area"),
						name="unique_area_per_map_pointer_answer",
					)
				],
			},
		),
		# --- 2. seed, 3. backfill, 4. verify --------------------------------
		migrations.RunPython(seed_map_areas, unseed_map_areas),
		migrations.RunPython(backfill, restore_json),
		migrations.RunPython(verify, migrations.RunPython.noop),
		# --- 5. and only now, drop the JSON ---------------------------------
		migrations.RemoveField(model_name="draganddrop", name="content"),
		migrations.RemoveField(model_name="fillintheblank", name="content"),
		migrations.RemoveField(model_name="mappointer", name="content"),
		migrations.RemoveField(model_name="matching", name="content"),
		migrations.RemoveField(model_name="openended", name="content"),
		migrations.RemoveField(model_name="statement", name="content"),
	]
