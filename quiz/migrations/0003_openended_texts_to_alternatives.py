"""
Data migration: convert OpenEnded.content.texts entries from the legacy
``{"text": "word"}`` format to the new ``{"alternatives": ["word"]}`` format.
"""

from django.db import migrations


def forwards(apps, schema_editor):
	OpenEnded = apps.get_model("quiz", "OpenEnded")
	for obj in OpenEnded.objects.all():
		content = obj.content
		if not isinstance(content, dict):
			continue

		raw_texts = content.get("texts", [])
		new_texts = []
		changed = False

		for t in raw_texts:
			if isinstance(t, dict) and "text" in t and "alternatives" not in t:
				# Legacy format: {"text": "word"} → {"alternatives": ["word"]}
				new_texts.append({"alternatives": [t["text"]]})
				changed = True
			elif isinstance(t, str):
				# Plain string → {"alternatives": ["word"]}
				new_texts.append({"alternatives": [t]})
				changed = True
			else:
				new_texts.append(t)

		if changed:
			content["texts"] = new_texts
			# Use update() to bypass full_clean / model validation
			OpenEnded.objects.filter(pk=obj.pk).update(content=content)


def backwards(apps, schema_editor):
	OpenEnded = apps.get_model("quiz", "OpenEnded")
	for obj in OpenEnded.objects.all():
		content = obj.content
		if not isinstance(content, dict):
			continue

		raw_texts = content.get("texts", [])
		new_texts = []
		changed = False

		for t in raw_texts:
			if isinstance(t, dict) and "alternatives" in t:
				# New format → legacy: take the first alternative
				alts = t["alternatives"]
				new_texts.append({"text": alts[0] if alts else ""})
				changed = True
			else:
				new_texts.append(t)

		if changed:
			content["texts"] = new_texts
			OpenEnded.objects.filter(pk=obj.pk).update(content=content)


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0002_openended"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
