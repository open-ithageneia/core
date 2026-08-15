"""One-off: split the Lefkada municipality feature (GADM level 3) into the
municipality proper plus its two inhabited islands, Kalamos and Kastos.

Edits the feature in place as text so the rest of the minified GeoJSON file is
byte-for-byte untouched.
"""

import json
import math
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "frontend/js/geo/data/gadm41_GRC_3.json"
MARKER = '{"type":"Feature","properties":{"GID_3":"GRC.7.1.4_1"'

# Polygon indices of the three main landmasses inside the original MultiPolygon.
LEFKADA, KALAMOS, KASTOS = 6, 3, 0


def feature_span(text: str, start: int) -> int:
	"""Return the index just past the JSON object starting at ``start``."""
	depth = 0
	i = start
	in_string = False
	escaped = False
	while True:
		ch = text[i]
		if in_string:
			if escaped:
				escaped = False
			elif ch == "\\":
				escaped = True
			elif ch == '"':
				in_string = False
		elif ch == '"':
			in_string = True
		elif ch == "{":
			depth += 1
		elif ch == "}":
			depth -= 1
			if depth == 0:
				return i + 1
		i += 1


def ring_distance(a, b) -> float:
	return min(math.dist(p, q) for p in a[0] for q in b[0])


def compact(obj) -> str:
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
	text = PATH.read_text(encoding="utf-8")
	start = text.index(MARKER)
	end = feature_span(text, start)
	original = text[start:end]
	feature = json.loads(original)

	if compact(feature) != original:
		raise SystemExit("re-serialisation is not byte-identical; aborting")

	polygons = feature["geometry"]["coordinates"]
	groups = {LEFKADA: [LEFKADA], KALAMOS: [KALAMOS], KASTOS: [KASTOS]}
	for idx, polygon in enumerate(polygons):
		if idx in groups:
			continue
		nearest = min(
			groups, key=lambda main_idx: ring_distance(polygon, polygons[main_idx])
		)
		groups[nearest].append(idx)
	print({k: sorted(v) for k, v in groups.items()})

	props = feature["properties"]

	def island(
		gid: str, name_greek: str, name_latin: str, member_indices: list[int]
	) -> dict:
		return {
			"type": "Feature",
			"properties": {
				**props,
				"GID_3": gid,
				"NAME_3": name_latin,
				"VARNAME_3": "NA",
				"NL_NAME_3": name_greek,
				"TYPE_3": "Nisí",
				"ENGTYPE_3": "Island",
				"HASC_3": "NA",
			},
			"geometry": {
				"type": "MultiPolygon",
				"coordinates": [polygons[i] for i in sorted(member_indices)],
			},
		}

	lefkada = {
		"type": "Feature",
		"properties": props,
		"geometry": {
			"type": "MultiPolygon",
			"coordinates": [polygons[i] for i in sorted(groups[LEFKADA])],
		},
	}
	kalamos = island("GRC.7.1.4.1_1", "Κάλαμος", "Kalamos", groups[KALAMOS])
	kastos = island("GRC.7.1.4.2_1", "Καστός", "Kastos", groups[KASTOS])

	replacement = ",".join(compact(f) for f in (lefkada, kalamos, kastos))
	PATH.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

	total = sum(len(f["geometry"]["coordinates"]) for f in (lefkada, kalamos, kastos))
	print(f"polygons before={len(polygons)} after={total}")


if __name__ == "__main__":
	main()
