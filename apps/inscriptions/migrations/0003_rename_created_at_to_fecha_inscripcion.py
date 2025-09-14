from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inscriptions", "0002_rename_updated_at_to_fecha_estado"),
    ]

    operations = [
        migrations.RenameField(
            model_name="inscripcioncursada",
            old_name="created_at",
            new_name="fecha_inscripcion",
        ),
    ]
