"""Keep ``MapArea`` in step with the GeoJSON the frontend draws.

The syncing itself is ``MapArea.sync()``; this is the command around it —
argument parsing, the dry run, and the report.

The client decides whether an answer was placed correctly by comparing the area
name it holds against a property of the GeoJSON feature under the pointer. That
made every area name an undeclared foreign key into files nothing checked: a
renamed or split feature — which ``scripts/rename_features.py`` and
``scripts/split_islands.py`` do on purpose — silently invalidated every answer
pointing at the old name, with no way to find them. This is the check that was
missing.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from quiz.models import MapArea, MapLevel


class _Rollback(Exception):
	"""Raised to undo a dry run's transaction."""


class Command(BaseCommand):
	help = "Sync the MapArea table with the GeoJSON files the frontend uses."

	def add_arguments(self, parser):
		parser.add_argument(
			"--level",
			type=int,
			choices=sorted(MapArea.LEVEL_SOURCES),
			help="Only sync this administrative level (default: all of them).",
		)
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Report what would change without keeping any of it.",
		)

	def handle(self, *args, **options):
		levels = (
			[options["level"]] if options["level"] else sorted(MapArea.LEVEL_SOURCES)
		)

		try:
			# A dry run does the real work inside a transaction it then rolls
			# back, so what it reports is what would actually happen rather than
			# a second implementation that can drift from the first.
			with transaction.atomic():
				blocked = self._report(levels)
				if options["dry_run"]:
					raise _Rollback
		except _Rollback:
			self.stdout.write(self.style.WARNING("dry run — nothing was written"))
			return

		if blocked:
			raise CommandError(
				f"{blocked} area(s) no longer in the GeoJSON are still referenced "
				f"by answers and were kept. Fix those answers, then run again."
			)

	def _report(self, levels):
		blocked_total = 0

		for level in levels:
			added, deleted, blocked = MapArea.sync(level)
			blocked_total += len(blocked)

			self.stdout.write(
				f"level {level} ({MapLevel(level).label}): "
				f"{len(added)} added, {len(deleted)} removed, "
				f"{MapArea.objects.filter(level=level).count()} total"
			)
			for name in added:
				self.stdout.write(self.style.SUCCESS(f"  + {name}"))
			for name in deleted:
				self.stdout.write(f"  - {name}")

			for name, references in blocked:
				self.stdout.write(
					self.style.ERROR(
						f"  ! {name} is no longer in the GeoJSON but "
						f"{references} answer(s) still point at it — kept"
					)
				)
				links = MapArea.objects.get(level=level, name=name).answer_links
				for link in links.select_related("answer__question"):
					first = link.answer.alternatives.first()
					self.stdout.write(
						f"      MapPointer #{link.answer.question_id}, "
						f"answer {first.text if first else link.answer_id!r}"
					)

		return blocked_total
