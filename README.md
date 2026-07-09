# Ecommerce

Pen — Minimal Django E-commerce

A small Django-based e-commerce starter project (Persian language default).

## Quick start

```bash
cp .env.example .env
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Prerequisites

- Python 3.11+ and a virtual environment
- Install dependencies: `pip install -r requirements/base.txt`

Quick start (development)

1. Copy environment variables or create a `.env` at project root (see `program/settings.py`).
2. Apply migrations:

```bash
python manage.py migrate
```

3. Create a superuser:

```bash
python manage.py createsuperuser
```

4. Run the dev server:

```bash
python manage.py runserver
```

Notes

- Default DB is SQLite at `db.sqlite3`. To use PostgreSQL set `DB_ENGINE=postgresql` and related vars.
- Admin interface is customized using `django-unfold`.
- SMS integration keys (optional): `SMS_IR_API_KEY`, `SMS_IR_LINE_NUMBER`.

Where to look

- Django settings: [program/settings.py](program/settings.py#L1-L500)
- Main apps: `apps/accounts`, `apps/catalog`, `apps/orders`

License

- No license specified.
