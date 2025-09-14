from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="inscripcioncursada",
            old_name="updated_at",
            new_name="fecha_estado",
        ),
    ]
