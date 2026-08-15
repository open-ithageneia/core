from django.db import migrations


# The listening section was added after the categories were seeded in 0010, and
# its category has been created by hand in each environment since. The admin now
# files every clip (and every question asked about one) under it, so a database
# without the row cannot save a listening question at all — seed it.
LISTENING_CATEGORY = ("LISTENING", "Listening", 5)


def seed_listening_category(apps, schema_editor):
	QuizCategory = apps.get_model("quiz", "QuizCategory")
	code, name, order = LISTENING_CATEGORY
	QuizCategory.objects.get_or_create(
		code=code, defaults={"name": name, "order": order}
	)


def unseed_listening_category(apps, schema_editor):
	"""Left as a no-op: the row is protected by every quiz pointing at it, and
	deleting it would take the hand-made copy in the existing databases with it."""


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0017_alter_mappointer_level"),
	]

	operations = [
		migrations.RunPython(seed_listening_category, unseed_listening_category),
	]
