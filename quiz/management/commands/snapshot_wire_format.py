import json
from pathlib import Path

from django.core.management.base import BaseCommand

from quiz.models import (
	DragAndDrop,
	FillInTheBlank,
	Listening,
	MapPointer,
	Matching,
	OpenEnded,
	Statement,
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

DEFAULT_PATH = Path("quiz/golden/wire_format.json")

# Every (model, serializer) pair the frontend can receive. Listening is included
# even though it has no JSON content — it nests StatementSerializer output, so a
# change to statements shows up here too.
PAIRS = [
	(Statement, StatementSerializer),
	(DragAndDrop, DragAndDropSerializer),
	(Matching, MatchingSerializer),
	(FillInTheBlank, FillInTheBlankSerializer),
	(OpenEnded, OpenEndedSerializer),
	(MapPointer, MapPointerSerializer),
	(Listening, ListeningSerializer),
]

# Timestamps move on every save; comparing them would make the golden file
# useless for verifying a refactor that rewrites rows.
VOLATILE_FIELDS = {"created_at", "updated_at"}


def _strip_volatile(value):
	if isinstance(value, dict):
		return {
			k: _strip_volatile(v) for k, v in value.items() if k not in VOLATILE_FIELDS
		}
	if isinstance(value, list):
		return [_strip_volatile(v) for v in value]
	return value


def build_snapshot() -> dict:
	"""Serialize every row through the real serializers, keyed by model name and
	pk. This is the exact JSON the frontend consumes, so an empty diff against it
	means the refactor is invisible to the client."""
	snapshot = {}
	for model, serializer_class in PAIRS:
		rows = {}
		for instance in model.objects.all().order_by("pk"):
			rows[str(instance.pk)] = _strip_volatile(serializer_class(instance).data)
		snapshot[model.__name__] = rows
	return snapshot


class Command(BaseCommand):
	help = (
		"Write (or verify) a golden snapshot of the JSON every serializer emits. "
		"Run it before a content refactor, then again after, and diff."
	)

	def add_arguments(self, parser):
		parser.add_argument(
			"--path",
			default=str(DEFAULT_PATH),
			help=f"Where to read/write the snapshot (default: {DEFAULT_PATH}).",
		)
		parser.add_argument(
			"--check",
			action="store_true",
			help="Compare against the existing file instead of overwriting it; "
			"exits non-zero on any difference.",
		)

	def handle(self, *args, **options):
		path = Path(options["path"])
		snapshot = build_snapshot()
		serialized = json.dumps(
			snapshot, ensure_ascii=False, indent="\t", sort_keys=True
		)

		if options["check"]:
			if not path.exists():
				self.stderr.write(f"No snapshot at {path}; run without --check first.")
				raise SystemExit(1)
			expected = path.read_text(encoding="utf-8")
			if expected == serialized:
				total = sum(len(rows) for rows in snapshot.values())
				self.stdout.write(
					self.style.SUCCESS(f"Wire format unchanged ({total} rows).")
				)
				return
			self.stderr.write(self.style.ERROR(f"Wire format differs from {path}."))
			self._report_diff(json.loads(expected), snapshot)
			raise SystemExit(1)

		path.parent.mkdir(parents=True, exist_ok=True)
		# Explicit LF: Python translates newlines to CRLF on Windows by default, so
		# a snapshot written on a dev machine would never match one written in CI,
		# and --check would fail on line endings rather than on content.
		with open(path, "w", encoding="utf-8", newline="\n") as handle:
			handle.write(serialized)
		total = sum(len(rows) for rows in snapshot.values())
		self.stdout.write(self.style.SUCCESS(f"Wrote {total} rows to {path}."))
		for name, rows in snapshot.items():
			self.stdout.write(f"  {name}: {len(rows)}")

	def _report_diff(self, expected: dict, actual: dict):
		"""Point at the first differing row per model — the full JSON of 48 rows
		is unreadable in a terminal, and the pk is enough to go look."""
		for name in sorted(set(expected) | set(actual)):
			exp_rows = expected.get(name, {})
			act_rows = actual.get(name, {})
			for pk in sorted(set(exp_rows) | set(act_rows), key=lambda p: int(p)):
				if exp_rows.get(pk) != act_rows.get(pk):
					self.stderr.write(f"  {name} pk={pk}")
					self.stderr.write(
						f"    expected: {json.dumps(exp_rows.get(pk), ensure_ascii=False)[:300]}"
					)
					self.stderr.write(
						f"    actual:   {json.dumps(act_rows.get(pk), ensure_ascii=False)[:300]}"
					)
