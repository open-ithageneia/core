from django.db import migrations, models


# Greek names of the categories, which until now lived in the frontend as the
# hardcoded ``QUIZ_CATEGORY_LABELS`` map. Seeded here so the database is the one
# place that names a category; the admin can edit them from now on.
GREEK_NAMES = {
	"GEOGRAPHY": "Γεωγραφία",
	"CIVICS": "Θεσμοί του Πολιτεύματος",
	"HISTORY": "Ιστορία",
	"CULTURE": "Πολιτισμός",
	"LISTENING": "Ακουστικό",
}


def seed_greek_names(apps, schema_editor):
	QuizCategory = apps.get_model("quiz", "QuizCategory")
	for category in QuizCategory.objects.filter(code__in=GREEK_NAMES):
		category.name_el = GREEK_NAMES[category.code]
		category.save(update_fields=["name_el"])


def unseed_greek_names(apps, schema_editor):
	"""Nothing to undo beyond the column itself, which the AddField reverses."""


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0018_seed_listening_category"),
	]

	operations = [
		migrations.AddField(
			model_name="quizcategory",
			name="name_el",
			field=models.CharField(
				blank=True,
				default="",
				help_text="Name shown to the user. Falls back to the English name when empty.",
				max_length=64,
				verbose_name="Greek name",
			),
		),
		migrations.RunPython(seed_greek_names, unseed_greek_names),
	]
