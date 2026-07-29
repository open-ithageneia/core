from django.db import migrations, models
import django.db.models.deletion


def create_parts_from_letters(apps, schema_editor):
	"""Turn each distinct (listening, letter) pair on the existing questions into
	a ``ListeningPart`` row, and point the question at it.

	Statements that are not part of a listening question keep no part — the old
	column defaulted to "A" for them too, which never meant anything.
	"""
	Statement = apps.get_model("quiz", "Statement")
	ListeningPart = apps.get_model("quiz", "ListeningPart")

	pairs = (
		Statement.objects.filter(listening__isnull=False)
		.values_list("listening_id", "part_letter")
		.distinct()
	)
	for listening_id, letter in pairs:
		part = ListeningPart.objects.create(
			listening_id=listening_id, letter=letter or "A"
		)
		Statement.objects.filter(listening_id=listening_id, part_letter=letter).update(
			part=part
		)


def restore_letters_from_parts(apps, schema_editor):
	Statement = apps.get_model("quiz", "Statement")

	for statement in Statement.objects.filter(part__isnull=False).select_related(
		"part"
	):
		statement.part_letter = statement.part.letter
		statement.save(update_fields=["part_letter"])


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0012_statement_part_alter_statement_order"),
	]

	operations = [
		# Keep the old letters around under a temporary name so the data can be
		# copied into the new rows before the column goes away.
		migrations.RenameField(
			model_name="statement",
			old_name="part",
			new_name="part_letter",
		),
		migrations.CreateModel(
			name="ListeningPart",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				("created_at", models.DateTimeField(auto_now_add=True)),
				("updated_at", models.DateTimeField(auto_now=True)),
				(
					"letter",
					models.CharField(
						choices=[("A", "Part A"), ("B", "Part B")],
						default="A",
						help_text="Which section of the listening question this is.",
						max_length=1,
					),
				),
				(
					"description",
					models.TextField(
						blank=True,
						default="",
						help_text="Optional text introducing the part, shown above its questions.",
					),
				),
				(
					"listening",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="parts",
						to="quiz.listening",
					),
				),
			],
			options={
				"verbose_name": "Listening part",
				"verbose_name_plural": "Listening parts",
				"ordering": ["letter"],
			},
		),
		migrations.AddConstraint(
			model_name="listeningpart",
			constraint=models.UniqueConstraint(
				fields=("listening", "letter"), name="unique_part_per_listening"
			),
		),
		migrations.AddField(
			model_name="statement",
			name="part",
			field=models.ForeignKey(
				blank=True,
				help_text="Which section of the listening question this belongs to. Must be a part of the same listening question.",
				null=True,
				on_delete=django.db.models.deletion.SET_NULL,
				related_name="questions",
				to="quiz.listeningpart",
			),
		),
		migrations.RunPython(create_parts_from_letters, restore_letters_from_parts),
		migrations.RemoveField(
			model_name="statement",
			name="part_letter",
		),
	]
