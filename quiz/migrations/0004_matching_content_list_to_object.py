"""
Data migration: convert Matching.content from the legacy list format
``[{title, items}, {title, items}]`` to the new object format
``{"columns": [{title, items}, {title, items}]}``.
"""

from django.db import migrations


def forwards(apps, schema_editor):
	Matching = apps.get_model("quiz", "Matching")
	for obj in Matching.objects.all():
		content = obj.content
		if isinstance(content, list):
			obj.content = {"columns": content}
			obj.save(update_fields=["content"])


def backwards(apps, schema_editor):
	Matching = apps.get_model("quiz", "Matching")
	for obj in Matching.objects.all():
		content = obj.content
		if isinstance(content, dict) and "columns" in content:
			obj.content = content["columns"]
			obj.save(update_fields=["content"])


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0003_openended_texts_to_alternatives"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
