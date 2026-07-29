from django.db import migrations


class Migration(migrations.Migration):
	"""Drop the part letter: nothing names a part any more. They are ordered by
	creation and the UI labels them Α, Β, … by position.
	"""

	dependencies = [
		("quiz", "0013_listeningpart"),
	]

	operations = [
		migrations.RemoveConstraint(
			model_name="listeningpart",
			name="unique_part_per_listening",
		),
		migrations.RemoveField(
			model_name="listeningpart",
			name="letter",
		),
		migrations.AlterModelOptions(
			name="listeningpart",
			options={
				"ordering": ["id"],
				"verbose_name": "Listening part",
				"verbose_name_plural": "Listening parts",
			},
		),
	]
