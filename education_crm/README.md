Education CRM (Flask + PostgreSQL)
=================================

Quick start
-----------

1. Create and configure PostgreSQL database

```
createdb education_crm
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/education_crm
export JWT_SECRET_KEY=change-me
export SECRET_KEY=change-me
```

2. Install dependencies

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

3. Apply schema

```
psql "$DATABASE_URL" -f database/schema.sql
```

4. Run app

```
python app.py
```

5. Health check

GET http://localhost:8000/health

