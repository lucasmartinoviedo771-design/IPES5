from django.db import migrations


FORWARD_SQL = """
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN loc_nacimiento;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN prov_nacimiento;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN pais_nacimiento;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN secu_titulo;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN secu_institucion;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN secu_promedio;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN secu_anio_egreso;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN sup1_titulo;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN sup1_institucion;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN sup2_titulo;
ALTER TABLE preinscriptions_preinscripcion DROP COLUMN sup2_institucion;
"""


# Reversa: re-crea las columnas como NULLables para no romper rollback
BACKWARD_SQL = """
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN loc_nacimiento varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN prov_nacimiento varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN pais_nacimiento varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN secu_titulo varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN secu_institucion varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN secu_promedio varchar(32) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN secu_anio_egreso varchar(16) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN sup1_titulo varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN sup1_institucion varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN sup2_titulo varchar(255) NULL;
ALTER TABLE preinscriptions_preinscripcion ADD COLUMN sup2_institucion varchar(255) NULL;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("preinscriptions", "0002_alter_preinscripcion_options_preinscripcion_anio_and_more"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=BACKWARD_SQL),
    ]
