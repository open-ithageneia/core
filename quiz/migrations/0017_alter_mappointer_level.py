from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("quiz", "0016_draganddrop_question_number_and_more"),
	]

	operations = [
		migrations.AlterField(
			model_name="mappointer",
			name="level",
			field=models.PositiveSmallIntegerField(
				choices=[
					(1, "Decentralized administration (Αποκεντρωμένη διοίκηση)"),
					(2, "Region (Περιφέρεια)"),
					(3, "Prefecture unit (Νομός / Νησί)"),
					(4, "Municipality and islands (Δήμος και νησιά)"),
					(5, "Geographic department (Γεωγραφικό διαμέρισμα)"),
				],
				default=4,
				help_text="Administrative division level used for the map.",
			),
		),
	]
