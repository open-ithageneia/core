import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import MapArea, fold_for_search

# Map "level" → (GeoJSON filename, property key holding the Greek area name).
# Filenames/keys must stay in sync with frontend geo/util.ts.
#   1 = decentralized administrations (αποκεντρωμένες διοικήσεις) — GADM level 1
#   2 = regions (περιφέρειες)                                     — GADM level 2
#   3 = prefecture units (νομοί/νησιά)                            — peterdsp greece-prefectures-and-units
#   4 = municipalities and islands (δήμοι και νησιά)              — GADM level 3
#   5 = geographic departments (γεωγραφικά διαμερίσματα)          — derived (build_geographic_departments.py)
MAP_LEVEL_SOURCES: dict[int, tuple[str, str]] = {
	1: ("gadm41_GRC_1.json", "NL_NAME_1"),
	2: ("gadm41_GRC_2.json", "NL_NAME_2"),
	3: ("greece_prefecture_units.json", "name_greek"),
	4: ("gadm41_GRC_3.json", "NL_NAME_3"),
	5: ("greece_geographic_departments.json", "name"),
}

GEO_DATA_DIR = Path(settings.BASE_DIR) / "frontend" / "js" / "geo" / "data"


def load_area_names(level: int) -> list[str]:
	"""Greek area names from the GeoJSON the frontend draws, so they match the
	region ``name`` answers are matched against in ``geo/util.ts``.

	Read here and nowhere else: the names live in the ``MapArea`` table, and are
	no longer loaded from disk on every process start.
	"""
	filename, name_key = MAP_LEVEL_SOURCES[level]
	with open(GEO_DATA_DIR / filename, encoding="utf-8") as f:
		data = json.load(f)
	return sorted({feat["properties"][name_key] for feat in data["features"]})


class Command(BaseCommand):
	help = (
		"Bring the MapArea table in line with the GeoJSON the frontend draws. "
		"Reports areas that disappeared and how many answers point at them — a "
		"rename used to break those answers silently."
	)

	def add_arguments(self, parser):
		parser.add_argument(
			"--level",
			type=int,
			choices=sorted(MAP_LEVEL_SOURCES),
			help="Only sync this map level (default: all).",
		)
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Report what would change without writing anything.",
		)

	def handle(self, *args, **options):
		levels = [options["level"]] if options["level"] else sorted(MAP_LEVEL_SOURCES)
		dry_run = options["dry_run"]

		added_total = 0
		orphaned_total = 0
		blocked_total = 0

		with transaction.atomic():
			for level in levels:
				added, orphaned, blocked = self._sync_level(level, dry_run)
				added_total += added
				orphaned_total += orphaned
				blocked_total += blocked

			if dry_run:
				transaction.set_rollback(True)

		self.stdout.write("")
		summary = (
			f"{added_total} added, {orphaned_total} removed, "
			f"{blocked_total} kept because answers still point at them"
		)
		self.stdout.write(
			self.style.WARNING(f"Dry run: {summary}")
			if dry_run
			else self.style.SUCCESS(summary)
		)
		if blocked_total:
			self.stdout.write(
				"\nThose areas no longer exist in the GeoJSON, so the answers "
				"pointing at them can never be matched. Repoint or delete those "
				"answers, then run this again."
			)

	def _sync_level(self, level, dry_run):
		wanted = set(load_area_names(level))
		existing = {area.name: area for area in MapArea.objects.filter(level=level)}

		missing = wanted - existing.keys()
		orphaned = [area for name, area in existing.items() if name not in wanted]

		if missing and not dry_run:
			MapArea.objects.bulk_create(
				[
					MapArea(level=level, name=name, search_name=fold_for_search(name))
					for name in sorted(missing)
				]
			)

		# An area an answer still points at cannot be deleted (the FK is PROTECTed)
		# and should not be: dropping it would silently discard the answer. Report
		# it instead, which is the whole point of the table existing.
		removable = []
		blocked = []
		for area in orphaned:
			if area.answers.exists():
				blocked.append(area)
			else:
				removable.append(area)

		if removable and not dry_run:
			MapArea.objects.filter(pk__in=[a.pk for a in removable]).delete()

		self.stdout.write(
			f"Level {level}: {len(wanted)} in GeoJSON, "
			f"+{len(missing)} added, -{len(removable)} removed"
		)
		for area in blocked:
			self.stdout.write(
				self.style.ERROR(
					f"  '{area.name}' is gone from the GeoJSON but "
					f"{area.answers.count()} answer(s) still point at it"
				)
			)

		return len(missing), len(removable), len(blocked)
