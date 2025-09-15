from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("preinscriptions", "0007_preinscripcion_estado"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="preinscripcion",
            name="user",
            field=models.ForeignKey(
                related_name="preinscripciones",
                null=True, blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
                help_text="Usuario dueño de esta preinscripción"
            ),
        ),
        migrations.CreateModel(
            name="PortalNotification",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField(blank=True)),
                ("url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("read_at", models.DateTimeField(null=True, blank=True)),
                ("user", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="portal_notifications"
                )),
            ],
            options={"db_table": "portal_notifications", "ordering": ["-created_at"]},
        ),
    ]
