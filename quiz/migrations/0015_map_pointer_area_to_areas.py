"""
Data migration: convert each MapPointer answer group's single ``area`` into the
``areas`` list, so an answer can accept more than one area (e.g. a river that
crosses several prefectures).
"""

from django.db import migrations


def _to_areas(raw):
	if isinstance(raw, str):
		return [raw] if raw else []
	if isinstance(raw, dict):
		# Legacy object form: {"name": "..."}
		name = raw.get("name")
		return [name] if name else []
	return []


def forwards(apps, schema_editor):
	MapPointer = apps.get_model("quiz", "MapPointer")
	for obj in MapPointer.objects.all():
		texts = (obj.content or {}).get("texts")
		if not isinstance(texts, list):
			continue
		changed = False
		for group in texts:
			if not isinstance(group, dict) or "area" not in group:
				continue
			areas = _to_areas(group.pop("area"))
			if areas:
				group["areas"] = areas
			changed = True
		if changed:
			obj.save(update_fields=["content"])


def backwards(apps, schema_editor):
	MapPointer = apps.get_model("quiz", "MapPointer")
	for obj in MapPointer.objects.all():
		texts = (obj.content or {}).get("texts")
		if not isinstance(texts, list):
			continue
		changed = False
		for group in texts:
			if not isinstance(group, dict) or "areas" not in group:
				continue
			areas = group.pop("areas")
			# Only the first area survives — the rest have no place to go.
			if areas:
				group["area"] = areas[0]
			changed = True
		if changed:
			obj.save(update_fields=["content"])


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0014_remove_listeningpart_letter"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
