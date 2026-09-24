"""Copy every ``content`` JSON column into the content tables 0021 created.

Three steps, in this order:

1. seed ``MapArea`` from the GeoJSON the frontend draws,
2. backfill every row from its JSON,
3. verify the new rows reproduce that JSON, raising if they do not.

**The ``content`` columns survive this migration.** Nothing here drops one. They
are the only record of what a row looked like beforehand, which is what makes an
error the verify step did not catch recoverable, and what lets an older image be
redeployed against a migrated database. A separate, later migration drops them.

Everything this needs — the legacy shapes, the GeoJSON source map, the accent
folding — is **frozen into this file**. It imports nothing from ``quiz.models``
or ``quiz.blanks``: a data migration that calls live code starts failing on a
fresh database the moment that code changes, and this one has to keep working
long after the shapes it knows about are gone from the codebase.

The backfill is deliberately total. It never drops a row it cannot classify and
never dedupes: ``entrypoint.sh`` runs ``migrate`` unattended on every container
start under ``set -o errexit``, so a raising migration is an outage rather than a
failed job. Anything surprising is preserved and left for ``sync_map_areas`` to
report.
"""

import json
import re
import unicodedata
from pathlib import Path

from django.db import migrations

# --------------------------------------------------------------------------
# Frozen copies of what the live code knows. Do not import these from quiz.*.
# --------------------------------------------------------------------------

MAP_LEVEL_SOURCES = {
    1: ("gadm41_GRC_1.json", "NL_NAME_1"),
    2: ("gadm41_GRC_2.json", "NL_NAME_2"),
    3: ("greece_prefecture_units.json", "name_greek"),
    4: ("gadm41_GRC_3.json", "NL_NAME_3"),
    5: ("greece_geographic_departments.json", "name"),
}

GEO_DATA_DIR = (
    Path(__file__).resolve().parents[2] / "frontend" / "js" / "geo" / "data"
)


def fold_for_search(text):
    stripped = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(char)
    )
    return unicodedata.normalize("NFC", stripped).strip().casefold()


def load_area_names(level):
    filename, name_key = MAP_LEVEL_SOURCES[level]
    with open(GEO_DATA_DIR / filename, encoding="utf-8") as handle:
        data = json.load(handle)
    return sorted({feature["properties"][name_key] for feature in data["features"]})


def parse_alternatives(raw):
    """Every shape ``texts`` has ever been stored in → a list of spellings.

    Migration 0003 moved from ``{"text": "x"}`` to ``{"alternatives": [...]}``,
    and the parser accepted bare lists and bare strings besides.
    """
    if isinstance(raw, dict):
        alternatives = raw.get("alternatives") or []
        if not alternatives and "text" in raw:
            alternatives = [raw["text"]]
        return list(alternatives)
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, str):
        return [raw]
    return [str(raw)]


def parse_areas(raw):
    """The current list form, plus the legacy single ``area`` string/object."""
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
            areas.extend(parse_areas(item))
        return areas
    return []


BLANK_PATTERN = re.compile(r"<(.+?)>")
CHOICE_PATTERN = re.compile(r"\{\{(.+?)\}\}(\*?)")


def parse_blank_text(sentence):
    """The fill-in-the-blank DSL, frozen at the shape of this migration.

    Returns ``(parts, has_multiple_choices)``, or ``(None, False)`` when the
    sentence cannot be parsed at all.

    Deliberately **does not raise**. A sentence with no blank was already broken
    before this migration — the old serializer raised on it at display time — so
    finding one here is not new damage, and refusing to migrate because of it
    would take the whole deploy down. Such a row lands with its text intact and
    no parts, and ``verify`` reports how many there were.

    ``quiz.models.FillInTheBlankText.parse`` is the live copy of these rules;
    ``BlankParserAgreementTests`` pins the two together.
    """
    raw_blanks = BLANK_PATTERN.findall(sentence)
    if not raw_blanks:
        return None, False

    has_multiple_choices = False
    for blank in raw_blanks:
        choices = CHOICE_PATTERN.findall(blank)
        if not choices:
            return None, False
        correct = [choice for choice, marker in choices if marker == "*"]
        if not correct:
            return None, False
        if len(choices) > 1 and len(correct) == 1:
            has_multiple_choices = True

    parts = []
    for index, chunk in enumerate(BLANK_PATTERN.split(sentence)):
        if index % 2 == 0:
            if chunk:
                parts.append({"text": chunk, "is_blank": False, "choices": []})
        else:
            parts.append(
                {
                    "text": "",
                    "is_blank": True,
                    "choices": [
                        {"text": choice, "is_correct": marker == "*"}
                        for choice, marker in CHOICE_PATTERN.findall(chunk)
                    ],
                }
            )
    return parts, has_multiple_choices


def text(value):
    """Empty and absent were the same thing in the JSON; they are here too.

    A number — an Excel cell import-export stored as a float — becomes the
    string the client displayed for it, which is JavaScript's: ``45.0`` showed
    as ``45``, and ``0`` as ``0`` rather than nothing.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    return value or ""


def matching_sequences(question):
    """A matching question's rows as its two columns, the way the serializer
    lays them out: a row with no text or image on a side has no item there."""
    pairs = list(question.pairs.order_by("order", "id"))
    left_sequence = [pair for pair in pairs if pair.left_text or pair.left_image_id]
    right_sequence = sorted(
        (pair for pair in pairs if pair.right_text or pair.right_image_id),
        key=lambda pair: (pair.right_order, pair.order, pair.pk),
    )
    return left_sequence, right_sequence


# --------------------------------------------------------------------------
# Step 1 — MapArea
# --------------------------------------------------------------------------


def seed_map_areas(apps, schema_editor):
    MapArea = apps.get_model("quiz", "MapArea")
    for level in sorted(MAP_LEVEL_SOURCES):
        existing = set(
            MapArea.objects.filter(level=level).values_list("name", flat=True)
        )
        MapArea.objects.bulk_create(
            [
                MapArea(level=level, name=name, search_name=fold_for_search(name))
                for name in load_area_names(level)
                if name not in existing
            ]
        )


def unseed_map_areas(apps, schema_editor):
    MapArea = apps.get_model("quiz", "MapArea")
    MapArea.objects.all().delete()


class AreaResolver:
    """Area name → ``MapArea`` row, creating the row when the name is unknown.

    A name that is not in the GeoJSON is exactly the breakage this table was
    added to make visible, so the migration keeps it rather than dropping the
    answer's area and silently changing what the client receives.
    ``sync_map_areas`` reports it afterwards as an area no GeoJSON defines, with
    the answers still pointing at it.
    """

    def __init__(self, MapArea):
        self.MapArea = MapArea
        self.cache = {
            (area.level, area.name): area
            for area in MapArea.objects.all()
        }

    def get(self, level, name):
        key = (level, name)
        if key not in self.cache:
            self.cache[key] = self.MapArea.objects.create(
                level=level, name=name, search_name=fold_for_search(name)
            )
        return self.cache[key]


# --------------------------------------------------------------------------
# Step 2 — the backfill, one function per type
# --------------------------------------------------------------------------


def backfill_statement(apps, question):
    StatementChoice = apps.get_model("quiz", "StatementChoice")
    content = question.content or {}

    question.prompt_text = text(content.get("prompt_text"))
    question.prompt_image_id = content.get("prompt_asset_id") or None
    question.prompt_audio_id = content.get("prompt_audio_asset_id") or None
    question.save(
        update_fields=["prompt_text", "prompt_image", "prompt_audio"]
    )

    StatementChoice.objects.bulk_create(
        [
            StatementChoice(
                statement=question,
                text=text(choice.get("text")),
                image_id=choice.get("asset_id") or None,
                is_correct=bool(choice.get("is_correct")),
                order=index,
            )
            for index, choice in enumerate(content.get("choices") or [])
        ]
    )


def backfill_drag_and_drop(apps, question):
    DragAndDropValue = apps.get_model("quiz", "DragAndDropValue")
    columns = question.content or []
    left = columns[0] if len(columns) > 0 else {}
    right = columns[1] if len(columns) > 1 else {}

    question.left_title = text(left.get("title"))
    question.right_title = text(right.get("title"))
    question.save(update_fields=["left_title", "right_title"])

    DragAndDropValue.objects.bulk_create(
        [
            DragAndDropValue(question=question, side=side, text=value, order=index)
            for side, column in (("LEFT", left), ("RIGHT", right))
            for index, value in enumerate(column.get("values") or [])
        ]
    )


def matching_columns(content):
    """The two columns of a matching question, in either stored shape."""
    # 0004 moved from a bare list of columns to {"columns": [...]}; both are read.
    columns = content.get("columns", []) if isinstance(content, dict) else content
    left_column = columns[0] if len(columns) > 0 else {}
    right_column = columns[1] if len(columns) > 1 else {}
    return left_column, right_column


def is_blank_item(item):
    """An item with neither text nor image, which a ``MatchPair`` side cannot
    hold: an empty side is how a row says that side is absent."""
    return not text(item.get("text")) and not item.get("asset_id")


def matching_partners(left_items, right_items):
    """Which right item, by index in its column, each left item points at.

    Pair by the stored ids rather than by position: nothing ever checked that
    the two columns' ids agreed, so position is the fallback, not the rule.
    ``None`` where there is nothing to point at.
    """
    right_by_id = {
        item.get("id"): position
        for position, item in enumerate(right_items)
        if "id" in item
    }
    partners = []
    for index, left in enumerate(left_items):
        found = right_by_id.get(left.get("matched_id"))
        if found is None and index < len(right_items):
            # No id to follow — fall back to the item sitting opposite.
            found = index
        partners.append(found)
    return partners


def right_slots(right_items):
    """Each carried right item's index in its column → its ``right_order``.

    Blank items are not carried (see ``is_blank_item``), so they take no slot.
    """
    slots = {}
    for position, item in enumerate(right_items):
        if not is_blank_item(item):
            slots[position] = len(slots)
    return slots


def backfill_matching(apps, question):
    """One row per left item, then one right-only row per right item no left
    item claimed.

    The columns were free to differ in length — a right-column distractor, a
    left item pointing at nothing — and one row per left item alone would drop
    the extra right items. A right item two left items both point at goes to
    the first; the second becomes a left-only row, since a row holds one
    partner. That is the one pairing this changes, and the old client could only
    ever mark one of the two correct anyway: the candidate had a single copy of
    that right item to give.
    """
    MatchPair = apps.get_model("quiz", "MatchPair")
    content = question.content or {}
    left_column, right_column = matching_columns(content)

    # The bare-list form carries no prompt; only the object form does.
    question.prompt_text = text(
        content.get("prompt_text") if isinstance(content, dict) else None
    )
    question.left_title = text(left_column.get("title"))
    question.right_title = text(right_column.get("title"))
    question.save(update_fields=["prompt_text", "left_title", "right_title"])

    left_items = left_column.get("items") or []
    right_items = right_column.get("items") or []
    slots = right_slots(right_items)

    pairs = []
    claimed = set()
    for left, partner in zip(
        left_items, matching_partners(left_items, right_items), strict=True
    ):
        if is_blank_item(left):
            continue
        pair = MatchPair(
            question=question,
            left_text=text(left.get("text")),
            left_image_id=left.get("asset_id") or None,
            order=len(pairs),
        )
        if partner in slots and partner not in claimed:
            claimed.add(partner)
            right = right_items[partner]
            pair.right_text = text(right.get("text"))
            pair.right_image_id = right.get("asset_id") or None
            # Where the right item sat in its own column, which is not
            # necessarily opposite its partner.
            pair.right_order = slots[partner]
        pairs.append(pair)
    for position, slot in slots.items():
        if position in claimed:
            continue
        right = right_items[position]
        pairs.append(
            MatchPair(
                question=question,
                right_text=text(right.get("text")),
                right_image_id=right.get("asset_id") or None,
                order=len(pairs),
                right_order=slot,
            )
        )
    MatchPair.objects.bulk_create(pairs)


def backfill_fill_in_the_blank(apps, question):
    FillInTheBlankText = apps.get_model("quiz", "FillInTheBlankText")
    FillInTheBlankExtraChoice = apps.get_model("quiz", "FillInTheBlankExtraChoice")
    content = question.content or {}

    question.show_answers_as_choices = bool(content.get("show_answers_as_choices"))
    question.prompt_image_id = content.get("prompt_asset_id") or None
    question.save(update_fields=["show_answers_as_choices", "prompt_image"])

    FillInTheBlankPart = apps.get_model("quiz", "FillInTheBlankPart")
    FillInTheBlankChoice = apps.get_model("quiz", "FillInTheBlankChoice")

    unparsed = 0
    for index, entry in enumerate(content.get("texts") or []):
        sentence = entry.get("text", "")
        parts, has_multiple_choices = parse_blank_text(sentence)
        if parts is None:
            unparsed += 1
        row = FillInTheBlankText.objects.create(
            question=question,
            text=sentence,
            has_multiple_choices=has_multiple_choices,
            order=index,
        )
        # The parts are derived from the sentence, which stays the source of
        # truth; the live model rebuilds them on every save.
        for order, part in enumerate(parts or []):
            part_row = FillInTheBlankPart.objects.create(
                sentence=row,
                text=part["text"],
                is_blank=part["is_blank"],
                order=order,
            )
            FillInTheBlankChoice.objects.bulk_create(
                [
                    FillInTheBlankChoice(
                        part=part_row,
                        text=choice["text"],
                        is_correct=choice["is_correct"],
                        order=position,
                    )
                    for position, choice in enumerate(part["choices"])
                ]
            )
    if unparsed:
        print(
            f"  warning: FillInTheBlank pk={question.pk} has {unparsed} sentence(s) "
            f"whose markup does not parse; text kept, no parts derived"
        )
    FillInTheBlankExtraChoice.objects.bulk_create(
        [
            FillInTheBlankExtraChoice(question=question, text=choice, order=index)
            for index, choice in enumerate(content.get("extra_choices") or [])
        ]
    )


def backfill_open_ended(apps, question):
    OpenEndedAnswer = apps.get_model("quiz", "OpenEndedAnswer")
    OpenEndedAlternative = apps.get_model("quiz", "OpenEndedAlternative")
    content = question.content or {}

    question.prompt_text = text(content.get("prompt_text"))
    question.prompt_image_id = content.get("prompt_asset_id") or None
    question.min_correct_answers = content.get("min_correct_answers") or 0
    question.save(
        update_fields=["prompt_text", "prompt_image", "min_correct_answers"]
    )

    for index, raw in enumerate(content.get("texts") or []):
        answer = OpenEndedAnswer.objects.create(question=question, order=index)
        OpenEndedAlternative.objects.bulk_create(
            [
                OpenEndedAlternative(answer=answer, text=value, order=position)
                for position, value in enumerate(parse_alternatives(raw))
            ]
        )


def backfill_map_pointer(apps, question, areas):
    MapPointerAnswer = apps.get_model("quiz", "MapPointerAnswer")
    MapPointerAlternative = apps.get_model("quiz", "MapPointerAlternative")
    MapPointerAnswerArea = apps.get_model("quiz", "MapPointerAnswerArea")
    content = question.content or {}

    question.prompt_text = text(content.get("prompt_text"))
    question.min_correct_answers = content.get("min_correct_answers") or 0
    question.show_answers = bool(content.get("show_answers", True))
    question.save(
        update_fields=["prompt_text", "min_correct_answers", "show_answers"]
    )

    for index, raw in enumerate(content.get("texts") or []):
        answer = MapPointerAnswer.objects.create(question=question, order=index)
        MapPointerAlternative.objects.bulk_create(
            [
                MapPointerAlternative(answer=answer, text=value, order=position)
                for position, value in enumerate(parse_alternatives(raw))
            ]
        )
        if isinstance(raw, dict):
            raw_areas = raw["areas"] if "areas" in raw else raw.get("area")
        else:
            raw_areas = None
        MapPointerAnswerArea.objects.bulk_create(
            [
                MapPointerAnswerArea(
                    answer=answer,
                    area=areas.get(question.level, name),
                    order=position,
                )
                for position, name in enumerate(parse_areas(raw_areas))
            ]
        )


def backfill_content(apps, schema_editor):
    areas = AreaResolver(apps.get_model("quiz", "MapArea"))

    for model_name, handler in (
        ("Statement", backfill_statement),
        ("DragAndDrop", backfill_drag_and_drop),
        ("Matching", backfill_matching),
        ("FillInTheBlank", backfill_fill_in_the_blank),
        ("OpenEnded", backfill_open_ended),
    ):
        for question in apps.get_model("quiz", model_name).objects.all():
            handler(apps, question)

    for question in apps.get_model("quiz", "MapPointer").objects.all():
        backfill_map_pointer(apps, question, areas)


# --------------------------------------------------------------------------
# Step 3 — verification
# --------------------------------------------------------------------------


def canonical_from_json(model_name, content):
    """The stored JSON, reduced to what the content tables can represent."""
    if model_name == "Statement":
        return {
            "prompt_text": text(content.get("prompt_text")),
            "prompt_asset_id": content.get("prompt_asset_id") or None,
            "prompt_audio_asset_id": content.get("prompt_audio_asset_id") or None,
            "choices": [
                {
                    "text": text(choice.get("text")),
                    "asset_id": choice.get("asset_id") or None,
                    "is_correct": bool(choice.get("is_correct")),
                }
                for choice in content.get("choices") or []
            ],
        }
    if model_name == "DragAndDrop":
        columns = content or []
        return [
            {
                "title": text(column.get("title")),
                "values": list(column.get("values") or []),
            }
            for column in (
                columns[0] if len(columns) > 0 else {},
                columns[1] if len(columns) > 1 else {},
            )
        ]
    if model_name == "Matching":
        # Each column is read on its own rather than through the pairing the
        # backfill builds, so a right item the rows lost is a missing entry here
        # instead of an agreement between two copies of the same mistake.
        left_column, right_column = matching_columns(content)
        left_items = left_column.get("items") or []
        right_items = right_column.get("items") or []
        slots = right_slots(right_items)
        left = []
        claimed = set()
        for item, partner in zip(
            left_items, matching_partners(left_items, right_items), strict=True
        ):
            if is_blank_item(item):
                continue
            # A right item keeps only its first claimant; see backfill_matching.
            if partner in claimed:
                partner = None
            claimed.add(partner)
            left.append(
                {
                    "text": text(item.get("text")),
                    "asset_id": item.get("asset_id") or None,
                    "partner": slots.get(partner),
                }
            )
        return {
            "prompt_text": text(
                content.get("prompt_text") if isinstance(content, dict) else None
            ),
            "left_title": text(left_column.get("title")),
            "right_title": text(right_column.get("title")),
            "left": left,
            "right": [
                {
                    "text": text(right_items[position].get("text")),
                    "asset_id": right_items[position].get("asset_id") or None,
                }
                for position in slots
            ],
        }
    if model_name == "FillInTheBlank":
        return {
            "show_answers_as_choices": bool(content.get("show_answers_as_choices")),
            "prompt_asset_id": content.get("prompt_asset_id") or None,
            "texts": [entry.get("text", "") for entry in content.get("texts") or []],
            "extra_choices": list(content.get("extra_choices") or []),
        }
    if model_name == "OpenEnded":
        return {
            "prompt_text": text(content.get("prompt_text")),
            "prompt_asset_id": content.get("prompt_asset_id") or None,
            "min_correct_answers": content.get("min_correct_answers") or 0,
            "texts": [
                parse_alternatives(raw) for raw in content.get("texts") or []
            ],
        }
    if model_name == "MapPointer":
        groups = []
        for raw in content.get("texts") or []:
            if isinstance(raw, dict):
                raw_areas = raw["areas"] if "areas" in raw else raw.get("area")
            else:
                raw_areas = None
            groups.append(
                {
                    "alternatives": parse_alternatives(raw),
                    "areas": parse_areas(raw_areas),
                }
            )
        return {
            "prompt_text": text(content.get("prompt_text")),
            "min_correct_answers": content.get("min_correct_answers") or 0,
            "show_answers": bool(content.get("show_answers", True)),
            "texts": groups,
        }
    raise ValueError(model_name)


def canonical_from_rows(model_name, question):
    """The same reduction, built from the rows the backfill wrote."""
    if model_name == "Statement":
        return {
            "prompt_text": text(question.prompt_text),
            "prompt_asset_id": question.prompt_image_id,
            "prompt_audio_asset_id": question.prompt_audio_id,
            "choices": [
                {
                    "text": text(choice.text),
                    "asset_id": choice.image_id,
                    "is_correct": choice.is_correct,
                }
                for choice in question.choices.order_by("order", "id")
            ],
        }
    if model_name == "DragAndDrop":
        values = list(question.values.order_by("side", "order", "id"))
        return [
            {
                "title": text(title),
                "values": [v.text for v in values if v.side == side],
            }
            for title, side in (
                (question.left_title, "LEFT"),
                (question.right_title, "RIGHT"),
            )
        ]
    if model_name == "Matching":
        left_sequence, right_sequence = matching_sequences(question)
        right_position = {pair.pk: index for index, pair in enumerate(right_sequence)}
        return {
            "prompt_text": text(question.prompt_text),
            "left_title": text(question.left_title),
            "right_title": text(question.right_title),
            "left": [
                {
                    "text": text(pair.left_text),
                    "asset_id": pair.left_image_id,
                    "partner": right_position.get(pair.pk),
                }
                for pair in left_sequence
            ],
            "right": [
                {"text": text(pair.right_text), "asset_id": pair.right_image_id}
                for pair in right_sequence
            ],
        }
    if model_name == "FillInTheBlank":
        return {
            "show_answers_as_choices": question.show_answers_as_choices,
            "prompt_asset_id": question.prompt_image_id,
            "texts": [t.text for t in question.texts.order_by("order", "id")],
            "extra_choices": [
                c.text for c in question.extra_choices.order_by("order", "id")
            ],
        }
    if model_name == "OpenEnded":
        return {
            "prompt_text": text(question.prompt_text),
            "prompt_asset_id": question.prompt_image_id,
            "min_correct_answers": question.min_correct_answers,
            "texts": [
                [a.text for a in answer.alternatives.order_by("order", "id")]
                for answer in question.answers.order_by("order", "id")
            ],
        }
    if model_name == "MapPointer":
        return {
            "prompt_text": text(question.prompt_text),
            "min_correct_answers": question.min_correct_answers,
            "show_answers": question.show_answers,
            "texts": [
                {
                    "alternatives": [
                        a.text for a in answer.alternatives.order_by("order", "id")
                    ],
                    "areas": [
                        link.area.name
                        for link in answer.area_links.order_by("order", "id")
                    ],
                }
                for answer in question.answers.order_by("order", "id")
            ],
        }
    raise ValueError(model_name)


MODEL_NAMES = [
    "Statement",
    "DragAndDrop",
    "Matching",
    "FillInTheBlank",
    "OpenEnded",
    "MapPointer",
]


def verify_backfill(apps, schema_editor):
    """Assert every row's new rows reproduce its JSON, and stop the deploy if not.

    Rows whose ``content`` is falsy are skipped — there is nothing to reproduce.
    That, and the fact that a dev database's shapes may not cover everything
    production holds, is the reason the JSON columns are kept rather than dropped
    in the same breath as this check.
    """
    checked = 0
    problems = []

    for model_name in MODEL_NAMES:
        for question in apps.get_model("quiz", model_name).objects.all():
            if not question.content:
                continue
            expected = canonical_from_json(model_name, question.content)
            actual = canonical_from_rows(model_name, question)
            if expected != actual:
                problems.append(
                    f"{model_name} pk={question.pk}\n"
                    f"  from JSON: {json.dumps(expected, ensure_ascii=False)[:500]}\n"
                    f"  from rows: {json.dumps(actual, ensure_ascii=False)[:500]}"
                )
            checked += 1

    if problems:
        raise RuntimeError(
            "Backfill did not reproduce the JSON content for "
            f"{len(problems)} row(s):\n" + "\n".join(problems)
        )
    print(f"  verified {checked} rows reproduce their JSON content")


# --------------------------------------------------------------------------
# Reverse — rebuild the JSON from the rows, then empty the content tables
# --------------------------------------------------------------------------


def json_from_rows(model_name, question):
    """The ``content`` value the old code would have written for this row.

    Rows authored after this migration have an empty ``content``; rebuilding it
    on the way back out is what lets the previous image serve them.
    """
    if model_name == "Statement":
        return {
            "prompt_text": question.prompt_text,
            "prompt_asset_id": question.prompt_image_id,
            "prompt_audio_asset_id": question.prompt_audio_id,
            "choices": [
                {
                    "text": choice.text,
                    "asset_id": choice.image_id,
                    "is_correct": choice.is_correct,
                }
                for choice in question.choices.order_by("order", "id")
            ],
        }
    if model_name == "DragAndDrop":
        values = list(question.values.order_by("side", "order", "id"))
        return [
            {"title": title, "values": [v.text for v in values if v.side == side]}
            for title, side in (
                (question.left_title, "LEFT"),
                (question.right_title, "RIGHT"),
            )
        ]
    if model_name == "Matching":
        left_sequence, right_sequence = matching_sequences(question)
        total = len(left_sequence)
        left_id = {pair.pk: index + 1 for index, pair in enumerate(left_sequence)}
        right_id = {
            pair.pk: index + 1 + total for index, pair in enumerate(right_sequence)
        }

        def item(pair, is_left):
            # The old schema required a ``matched_id``; an item with no partner
            # points at 0, which is no item's id.
            if is_left:
                entry = {
                    "id": left_id[pair.pk],
                    "matched_id": right_id.get(pair.pk, 0),
                }
            else:
                entry = {
                    "id": right_id[pair.pk],
                    "matched_id": left_id.get(pair.pk, 0),
                }
            image_id = pair.left_image_id if is_left else pair.right_image_id
            if image_id:
                entry["asset_id"] = image_id
            else:
                entry["text"] = pair.left_text if is_left else pair.right_text
            return entry

        return {
            "prompt_text": question.prompt_text or None,
            "columns": [
                {
                    "title": question.left_title,
                    "items": [item(pair, True) for pair in left_sequence],
                },
                {
                    "title": question.right_title,
                    "items": [item(pair, False) for pair in right_sequence],
                },
            ],
        }
    if model_name == "FillInTheBlank":
        return {
            "show_answers_as_choices": question.show_answers_as_choices,
            "prompt_asset_id": question.prompt_image_id,
            "texts": [
                {"text": t.text} for t in question.texts.order_by("order", "id")
            ],
            "extra_choices": [
                c.text for c in question.extra_choices.order_by("order", "id")
            ],
        }
    if model_name == "OpenEnded":
        return {
            "prompt_text": question.prompt_text,
            "prompt_asset_id": question.prompt_image_id,
            "min_correct_answers": question.min_correct_answers,
            "texts": [
                {
                    "alternatives": [
                        a.text for a in answer.alternatives.order_by("order", "id")
                    ]
                }
                for answer in question.answers.order_by("order", "id")
            ],
        }
    if model_name == "MapPointer":
        groups = []
        for answer in question.answers.order_by("order", "id"):
            group = {
                "alternatives": [
                    a.text for a in answer.alternatives.order_by("order", "id")
                ]
            }
            areas = [
                link.area.name for link in answer.area_links.order_by("order", "id")
            ]
            if areas:
                group["areas"] = areas
            groups.append(group)
        return {
            "prompt_text": question.prompt_text,
            "show_answers": question.show_answers,
            "min_correct_answers": question.min_correct_answers,
            "texts": groups,
        }
    raise ValueError(model_name)


#: field → value to restore, per model, so the reverse lands on exactly the state
#: migration 0021 alone produces rather than on 0021-plus-leftovers.
RESET_FIELDS = {
    "Statement": {"prompt_text": "", "prompt_image": None, "prompt_audio": None},
    "DragAndDrop": {
        "prompt_text": "",
        "prompt_image": None,
        "prompt_audio": None,
        "left_title": "",
        "right_title": "",
    },
    "Matching": {
        "prompt_text": "",
        "prompt_image": None,
        "prompt_audio": None,
        "left_title": "",
        "right_title": "",
    },
    "FillInTheBlank": {
        "prompt_text": "",
        "prompt_image": None,
        "prompt_audio": None,
        "show_answers_as_choices": False,
    },
    "OpenEnded": {
        "prompt_text": "",
        "prompt_image": None,
        "prompt_audio": None,
        "min_correct_answers": 1,
    },
    "MapPointer": {
        "prompt_text": "",
        "prompt_image": None,
        "prompt_audio": None,
        "min_correct_answers": 1,
        "show_answers": True,
    },
}


def reverse_backfill(apps, schema_editor):
    for model_name in MODEL_NAMES:
        model = apps.get_model("quiz", model_name)
        for question in model.objects.all():
            question.content = json_from_rows(model_name, question)
            for field, value in RESET_FIELDS[model_name].items():
                setattr(question, field, value)
            question.save()

    # Emptying the child tables is what makes the reverse re-runnable: the
    # backfill can then be applied again against the same database.
    for child in (
        "StatementChoice",
        "DragAndDropValue",
        "MatchPair",
        "FillInTheBlankChoice",
        "FillInTheBlankPart",
        "FillInTheBlankText",
        "FillInTheBlankExtraChoice",
        "OpenEndedAlternative",
        "OpenEndedAnswer",
        "MapPointerAnswerArea",
        "MapPointerAlternative",
        "MapPointerAnswer",
    ):
        apps.get_model("quiz", child).objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0021_quiz_content_tables"),
    ]

    operations = [
        migrations.RunPython(seed_map_areas, unseed_map_areas),
        migrations.RunPython(backfill_content, reverse_backfill),
        migrations.RunPython(verify_backfill, migrations.RunPython.noop),
    ]
