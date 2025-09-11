# IPES5

Reconstrucción de IPES4 → IPES5 con Django 5 + Ninja + MySQL.

## 🚀 Setup

```bash
git clone <repo>
cd IPES5
python -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata fixtures/*.json
```

## 📂 Arquitectura

- **core/**: settings, urls, asgi, wsgi
- **apps/**: dominios (users, academics, inscriptions, api, dashboard)
- **fixtures/**: catálogos cerrados
- **templates/**: HTML
- **static/**: assets
