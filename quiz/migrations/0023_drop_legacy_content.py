"""Drop the six ``content`` JSON columns 0022 left behind.

0022 copied every column into the content tables, verified the copy, and kept
the columns as a snapshot of what each row held beforehand. Production has now
run on the content tables, so the snapshot goes.

Reversible, but not lossless: reversing re-adds the columns empty, and reversing
0022 after it rebuilds each one from the content tables (``json_from_rows``) —
the equivalent JSON, not the original bytes. Take a database backup before
applying this if the original values might still be wanted.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0022_backfill_quiz_content"),
    ]

    operations = [
        migrations.RemoveField(model_name="draganddrop", name="content"),
        migrations.RemoveField(model_name="fillintheblank", name="content"),
        migrations.RemoveField(model_name="mappointer", name="content"),
        migrations.RemoveField(model_name="matching", name="content"),
        migrations.RemoveField(model_name="openended", name="content"),
        migrations.RemoveField(model_name="statement", name="content"),
    ]
