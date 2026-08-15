# -*- coding: utf-8 -*-
"""
Build a GeoJSON layer for the traditional Greek *geographic departments*
(γεωγραφικά διαμερίσματα) used in school geography exams.

No such layer is published by any authoritative portal (geodata.gov.gr, GADM,
Eurostat all stop at the 13 modern περιφέρειες), so we derive it by grouping the
modern regional units in ``greece_prefecture_units.json`` into departments.

Each department feature's geometry is a MultiPolygon that simply collects the
member units' polygons. Island departments are disjoint so this is exact; a few
mainland departments will show faint interior lines between merged units — that
is cosmetic and does not affect click targets or answer matching.

The unit -> department mapping below is the reviewable part: adjust it to match
your curriculum's exact division, then re-run:

    python scripts/build_geographic_departments.py

Output: frontend/js/geo/data/greece_geographic_departments.json
"""

import io
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "frontend" / "js" / "geo" / "data"
SRC = DATA / "greece_prefecture_units.json"
OUT = DATA / "greece_geographic_departments.json"

# department id -> (Greek name, Latin name, [member unit name_greek, ...])
# Member strings must match `properties.name_greek` in the source file exactly.
DEPARTMENTS = {
	"thrace": (
		"Θράκη",
		"Thrace",
		[
			"ΕΒΡΟΥ",
			"ΣΑΜΟΘΡΑΚΗΣ",
			"ΞΑΝΘΗΣ",
			"ΡΟΔΟΠΗΣ",
		],
	),
	"macedonia": (
		"Μακεδονία",
		"Macedonia",
		[
			"ΔΡΑΜΑΣ",
			"ΘΑΣΟΥ",
			"ΚΑΒΑΛΑΣ",
			"ΣΕΡΡΩΝ",
			"ΘΕΣΣΑΛΟΝΙΚΗΣ",
			"ΗΜΑΘΙΑΣ",
			"ΚΙΛΚΙΣ",
			"ΠΕΛΛΑΣ",
			"ΠΙΕΡΙΑΣ",
			"ΧΑΛΚΙΔΙΚΗΣ",
			"ΓΡΕΒΕΝΩΝ",
			"ΚΑΣΤΟΡΙΑΣ",
			"ΚΟΖΑΝΗΣ",
			"ΦΛΩΡΙΝΑΣ",
		],
	),
	"epirus": (
		"Ήπειρος",
		"Epirus",
		[
			"ΑΡΤΑΣ",
			"ΘΕΣΠΡΩΤΙΑΣ",
			"ΙΩΑΝΝΙΝΩΝ",
			"ΠΡΕΒΕΖΑΣ",
		],
	),
	"thessaly": (
		"Θεσσαλία",
		"Thessaly",
		[
			"ΚΑΡΔΙΤΣΑΣ",
			"ΛΑΡΙΣΑΣ",
			"ΜΑΓΝΗΣΙΑΣ",
			"ΤΡΙΚΑΛΩΝ",
			"ΣΠΟΡΑΔΩΝ",
		],
	),
	"central_greece": (
		"Στερεά Ελλάδα",
		"Central Greece",
		[
			"ΑΙΤΩΛΟΑΚΑΡΝΑΝΙΑΣ",
			"ΒΟΙΩΤΙΑΣ",
			"ΕΥΒΟΙΑΣ",
			"ΕΥΡΥΤΑΝΙΑΣ",
			"ΦΘΙΩΤΙΔΑΣ",
			"ΦΩΚΙΔΑΣ",
			"ΑΝΑΤΟΛΙΚΗΣ ΑΤΤΙΚΗΣ",
			"ΔΥΤΙΚΗΣ ΑΤΤΙΚΗΣ",
			"ΒΟΡΕΙΟΥ ΤΟΜΕΑ ΑΘΗΝΩΝ",
			"ΔΥΤΙΚΟΥ ΤΟΜΕΑ ΑΘΗΝΩΝ",
			"ΚΕΝΤΡΙΚΟΥ ΤΟΜΕΑ ΑΘΗΝΩΝ",
			"ΝΟΤΙΟΥ ΤΟΜΕΑ ΑΘΗΝΩΝ",
			"ΠΕΙΡΑΙΩΣ",
			"ΝΗΣΩΝ",
		],
	),
	"peloponnese": (
		"Πελοπόννησος",
		"Peloponnese",
		[
			"ΑΡΓΟΛΙΔΑΣ",
			"ΑΡΚΑΔΙΑΣ",
			"ΚΟΡΙΝΘΙΑΣ",
			"ΛΑΚΩΝΙΑΣ",
			"ΜΕΣΣΗΝΙΑΣ",
			"ΑΧΑΪΑΣ",
			"ΗΛΕΙΑΣ",
		],
	),
	"ionian_islands": (
		"Νησιά Ιονίου",
		"Ionian Islands",
		[
			"ΚΕΡΚΥΡΑΣ",
			"ΚΕΦΑΛΛΗΝΙΑΣ",
			"ΖΑΚΥΝΘΟΥ",
			"ΛΕΥΚΑΔΑΣ",
			"ΙΘΑΚΗΣ",
		],
	),
	"crete": (
		"Κρήτη",
		"Crete",
		[
			"ΗΡΑΚΛΕΙΟΥ",
			"ΛΑΣΙΘΙΟΥ",
			"ΡΕΘΥΜΝΟΥ",
			"ΧΑΝΙΩΝ",
		],
	),
	"dodecanese": (
		"Δωδεκάνησα",
		"Dodecanese",
		[
			"ΚΑΛΥΜΝΟΥ",
			"ΚΑΡΠΑΘΟΥ",
			"ΚΩ",
			"ΡΟΔΟΥ",
		],
	),
	"cyclades": (
		"Κυκλάδες",
		"Cyclades",
		[
			"ΑΝΔΡΟΥ",
			"ΘΗΡΑΣ",
			"ΚΕΑΣ - ΚΥΘΝΟΥ",
			"ΜΗΛΟΥ",
			"ΜΥΚΟΝΟΥ",
			"ΝΑΞΟΥ",
			"ΠΑΡΟΥ",
			"ΣΥΡΟΥ",
			"ΤΗΝΟΥ",
		],
	),
	"north_aegean": (
		"Νησιά Βορείου Αιγαίου",
		"North Aegean Islands",
		[
			"ΛΕΣΒΟΥ",
			"ΛΗΜΝΟΥ",
			"ΙΚΑΡΙΑΣ",
			"ΣΑΜΟΥ",
			"ΧΙΟΥ",
		],
	),
}


def polygons_of(geometry):
	"""Return a list of Polygon coordinate arrays from a Polygon/MultiPolygon."""
	if geometry["type"] == "Polygon":
		return [geometry["coordinates"]]
	if geometry["type"] == "MultiPolygon":
		return list(geometry["coordinates"])
	raise ValueError(f"Unexpected geometry type: {geometry['type']}")


def main():
	with io.open(SRC, encoding="utf-8") as f:
		src = json.load(f)

	by_name = {feat["properties"]["name_greek"]: feat for feat in src["features"]}

	# Validate mapping covers every unit exactly once.
	assigned = [u for _, _, units in DEPARTMENTS.values() for u in units]
	assigned_set = set(assigned)
	if len(assigned) != len(assigned_set):
		dupes = sorted({u for u in assigned if assigned.count(u) > 1})
		raise SystemExit(f"Units assigned to more than one department: {dupes}")
	unknown = sorted(assigned_set - set(by_name))
	if unknown:
		raise SystemExit(f"Mapping references units not in source: {unknown}")
	unassigned = sorted(set(by_name) - assigned_set)
	if unassigned:
		raise SystemExit(f"Units not assigned to any department: {unassigned}")

	features = []
	for dept_id, (name_gr, name_lat, units) in DEPARTMENTS.items():
		multi = []
		for unit in units:
			multi.extend(polygons_of(by_name[unit]["geometry"]))
		features.append(
			{
				"type": "Feature",
				"properties": {
					"id": f"geodept:{dept_id}",
					"name": name_gr,
					"name_latin": name_lat,
				},
				"geometry": {"type": "MultiPolygon", "coordinates": multi},
			}
		)

	out = {"type": "FeatureCollection", "features": features}
	with io.open(OUT, "w", encoding="utf-8") as f:
		json.dump(out, f, ensure_ascii=False)
	print(f"Wrote {len(features)} departments -> {OUT}")


if __name__ == "__main__":
	main()
