Informe de Progreso y Estado — IPES5
1) Hecho / Resuelto

Entorno: venv con Python 3.12.10; mysqlclient==2.2.4 instalado (wheel, sin compilar).

DB: MySQL creada (ipes5) con usuario dedicado; .env cargado con python-dotenv; manage.py migrate OK.

Modelo faltante: agregado Ciclo (ANUAL / 1C / 2C) y seed de ciclos.

API base: Django Ninja con X-API-Key (campo api_key en UserProfile), routers para:

GET /api/v1/carreras → [{id, nombre, plan_id, plan_txt}]

GET /api/v1/estudiantes → {"items":[{id, nombre_completo, dni, email}]}

GET /api/v1/materias/{id}/correlatividades → {"regulares":[...], "aprobadas":[...]}

2) Pendiente / No bloqueante

Usuarios + API keys: si aún no existen usuarios, los fixtures fallan; usar comandos idempotentes (abajo).

Grupos/roles: roles.json instala 0 objetos; reemplazar por comando idempotente.

Carga masiva de fixtures: loaddata no expande *.json; usar bucle de PowerShell si hace falta.

3) Errores habituales y cómo se resolvieron

ModuleNotFoundError: dotenv → instalar python-dotenv y load_dotenv() en settings.py.

mysqlclient en Win + Py 3.13 → cambiar a Py 3.12 (wheel binario).

Access denied (using password: NO) → .env incompleto o no cargado; usar usuario propio y DB_HOST=127.0.0.1.

ciclos.json sin modelo → se implementó Ciclo y seed de catálogo.

loaddata fixtures/*.json → usar rutas explícitas o bucle Get-ChildItem.

4) Estado actual

Proyecto IPES5 operativo, DB migrada y ciclos sembrados.

API Ninja funcional con auth por API key.

Fixtures problemáticos reemplazables por comandos idempotentes.

Pasos finales recomendados (idempotentes)

Si ya agregaste estos comandos, ejecútalos; si no, dime y te paso los archivos listos para copiar.

Grupos base (evita depender de roles.json)

python manage.py ensure_roles


Usuarios mínimos + API keys (evita fixtures de usuarios)

python manage.py seed_min_users
# La consola imprime las API keys generadas; usa cualquiera en el header X-API-Key


(Opcional) Cargar fixtures individuales

# Ejemplo: cargar un fixture concreto
python manage.py loaddata .\fixtures\ciclos.json

# O recorrer todos los .json de la carpeta
Get-ChildItem -Path .\fixtures -File -Filter *.json | ForEach-Object {
  python manage.py loaddata $_.FullName
}

Nota de consola (acentos rotos “”)

Si ves caracteres raros en Windows:

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8


Y guarda tus .ps1/.md en UTF-8.
