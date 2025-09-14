from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inscriptions", "0003_rename_created_at_to_fecha_inscripcion"),
    ]

    operations = [
        migrations.RenameField(
            model_name="inscripcionexamen",
            old_name="created_at",
            new_name="fecha_inscripcion",
        ),
    ]
