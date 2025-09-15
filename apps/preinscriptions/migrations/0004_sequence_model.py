from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("preinscriptions", "0003_cleanup_legacy"),
    ]

    operations = [
        migrations.CreateModel(
            name="PreinscripcionSequence",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("anio", models.IntegerField(unique=True)),
                ("last", models.IntegerField(default=0)),
            ],
            options={"db_table": "preinscriptions_sequence"},
        ),
    ]
