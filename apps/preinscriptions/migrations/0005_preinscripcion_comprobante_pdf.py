from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("preinscriptions", "0004_sequence_model")]
    operations = [
        migrations.AddField(
            model_name="preinscripcion",
            name="comprobante_pdf",
            field=models.FileField(
                upload_to="preinscripciones/%Y/", null=True, blank=True
            ),
        )
    ]
