import json
import unicodedata
from pathlib import Path

from django.db import models


def fold_for_search(text):
	"""Lowercase and strip accents so a name matches however it is typed — Greek
	is routinely typed without its tonos."""
	stripped = "".join(
		char
		for char in unicodedata.normalize("NFD", text)
		if not unicodedata.combining(char)
	)
	return unicodedata.normalize("NFC", stripped).strip().casefold()


class MapLevel(models.IntegerChoices):
	"""Administrative division levels the map can be drawn at.

	Here rather than nested in ``MapPointer`` because ``MapArea`` needs it
	too, and ``map_pointer`` imports this module rather than the other way
	round. ``MapPointer.MapLevel`` stays as an alias.
	"""

	DECENTRALIZED_ADMIN = 1, "Decentralized administration (Αποκεντρωμένη διοίκηση)"
	REGION = 2, "Region (Περιφέρεια)"
	PREFECTURE_UNIT = 3, "Prefecture unit (Νομός / Νησί)"
	MUNICIPALITY = 4, "Municipality and islands (Δήμος και νησιά)"
	GEOGRAPHIC_DEPARTMENT = 5, "Geographic department (Γεωγραφικό διαμέρισμα)"


class MapArea(models.Model):
	"""One named area of the map, at one administrative level.

	Rows are generated from the GeoJSON the frontend draws, by
	``manage.py sync_map_areas`` — never by hand. ``name`` has to stay
	byte-identical to the property the client matches an answer against in
	``geo/util.ts``, so editing it here would silently break that match.

	The table exists so that a renamed or removed GeoJSON feature becomes a
	report — ``sync()`` names the areas that vanished and counts the answers
	still pointing at them — instead of what it used to be: answers that quietly
	stopped being correct, with no way to find them.
	"""

	# level → (GeoJSON filename, property key holding the Greek area name).
	#   1 = decentralized administrations (αποκεντρωμένες διοικήσεις) — GADM level 1
	#   2 = regions (περιφέρειες)                                     — GADM level 2
	#   3 = prefecture units (νομοί/νησιά)                            — peterdsp greece-prefectures-and-units
	#   4 = municipalities and islands (δήμοι και νησιά)              — GADM level 3
	#   5 = geographic departments (γεωγραφικά διαμερίσματα)          — derived (build_geographic_departments.py)
	LEVEL_SOURCES = {
		1: ("gadm41_GRC_1.json", "NL_NAME_1"),
		2: ("gadm41_GRC_2.json", "NL_NAME_2"),
		3: ("greece_prefecture_units.json", "name_greek"),
		4: ("gadm41_GRC_3.json", "NL_NAME_3"),
		5: ("greece_geographic_departments.json", "name"),
	}

	GEO_DATA_DIR = (
		Path(__file__).resolve().parents[2] / "frontend" / "js" / "geo" / "data"
	)

	level = models.PositiveSmallIntegerField(choices=MapLevel.choices)
	name = models.CharField(
		max_length=255,
		help_text="Greek name, exactly as it appears in the GeoJSON.",
	)
	search_name = models.CharField(
		max_length=255,
		db_index=True,
		editable=False,
		help_text="Accent-folded, casefolded form of the name, for the picker.",
	)

	class Meta:
		ordering = ["level", "name"]
		verbose_name = "Map area"
		verbose_name_plural = "Map areas"
		constraints = [
			models.UniqueConstraint(
				fields=["level", "name"], name="unique_map_area_per_level"
			),
		]

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		self.search_name = fold_for_search(self.name)
		super().save(*args, **kwargs)

	@classmethod
	def geojson_names(cls, level):
		"""The distinct area names the GeoJSON for *level* defines, sorted.

		Read on demand, never at import time: building a validation enum out of
		five GeoJSON files on every process start is what this table replaced.
		"""
		filename, name_key = cls.LEVEL_SOURCES[level]
		with open(cls.GEO_DATA_DIR / filename, encoding="utf-8") as handle:
			data = json.load(handle)
		return sorted({feature["properties"][name_key] for feature in data["features"]})

	@classmethod
	def sync(cls, level):
		"""Bring one level into line with its GeoJSON.

		Returns ``(added, deleted, blocked)`` — the names gained, the orphans
		removed, and ``(name, answer_count)`` for orphans an answer still points
		at. **Those are kept, not deleted**: an area that vanished from the
		GeoJSON while answers still reference it is the breakage this table
		exists to surface, so it is reported rather than quietly dropped.
		"""
		expected = set(cls.geojson_names(level))
		existing = {area.name: area for area in cls.objects.filter(level=level)}

		added = sorted(expected - set(existing))
		cls.objects.bulk_create(
			[
				cls(level=level, name=name, search_name=fold_for_search(name))
				for name in added
			]
		)

		deleted, blocked = [], []
		for name in sorted(set(existing) - expected):
			references = existing[name].answer_links.count()
			if references:
				blocked.append((name, references))
			else:
				deleted.append(name)
		if deleted:
			cls.objects.filter(level=level, name__in=deleted).delete()

		return added, deleted, blocked
