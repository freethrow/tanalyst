# CLAUDE.md

## Project Overview

Django 5.2 business intelligence platform for article aggregation, AI translation, semantic search, and activity tracking. Uses MongoDB as the primary database, Redis for caching/task queue, and Celery for background processing.

**Key purpose:** Scrape Serbian business news, translate to Italian/English via LLMs, enable semantic search, generate weekly summaries, and distribute via email.

## Tech Stack

- **Backend:** Django 5.2 + Python 3.12 (local) / 3.11 (Docker)
- **Database:** MongoDB via `django-mongodb-backend` (collections are `managed=False`)
- **Cache/Broker:** Redis
- **Task Queue:** Celery + Celery Beat
- **AI/ML:** Pydantic AI, Sentence Transformers, Transformers (PyTorch CPU)
- **Scraping:** Scrapy (with Crochet for Twisted reactor integration)
- **PDF:** WeasyPrint | **Excel:** openpyxl
- **Email:** Resend API
- **Frontend:** Django templates + HTMX
- **Static Files:** WhiteNoise
- **Linting:** Ruff (defaults)

## Project Structure

```
analyst/              # Main Django project config, settings, celery, agents, scrapers, emails
articles/             # Articles app - CRUD, search, embeddings, summaries, PDF/Excel export
activities/           # Activities app - initiative tracking, todos, reports
document_rag/         # RAG module (retrieval-augmented generation)
templates/            # Base templates + partials (HTMX)
static/               # CSS, JS, fonts, images
locale/               # i18n: en, it
```

## Django Apps

1. `analyst.crochet_setup.CrochetAppConfig` — must be first in INSTALLED_APPS (Twisted reactor init)
2. `articles` — article management, search, translation, summaries
3. `activities` — initiative/activity tracking for Belgrade/Podgorica offices
4. `document_rag` — document RAG
5. `analyst.agents` — AI agents (summarizer, translator)

## Key Commands

```bash
# Run dev server
python manage.py runserver

# Run tests
python manage.py test activities --settings=analyst.test_settings

# Celery worker
celery -A analyst worker --loglevel=info

# Celery beat (scheduler)
celery -A analyst beat --loglevel=info

# Download ML models
python manage.py download_models

# Create user
python manage.py createuser

# Import/export articles
python manage.py import_articles --file articles.json
python manage.py export_articles
```

## Docker

```bash
docker-compose up -d          # Start all services (redis, web, celery worker, celery beat)
docker exec ta_web python manage.py migrate
docker exec ta_web python manage.py createuser
```

Services: Redis (6379), Web/Gunicorn (8000), Celery Worker, Celery Beat.

## Database

- MongoDB with `django-mongodb-backend`. All model collections use `managed = False`.
- Key collections: `articles`, `weekly_summaries`, `activities`, `summaries`
- MongoDB Atlas Search used for full-text search
- Models use `ObjectIdAutoField` for primary keys
- Embedded documents used for Todo items inside Activity
- Custom `MongoRouter` for DB routing

## Environment Variables

Required in `.env`:
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `MONGODB_URI`, `MONGO_DB`, `MONGO_COLLECTION`
- `REDIS_URL`
- `RESEND_API_KEY` (email)
- `OPENROUTER_API_KEY` or `GROQ_API_KEY` (LLM)
- `LLM_MODEL` (e.g. `google/gemini-2.5-flash`)

## Code Conventions

- **Style:** PEP 8, enforced by Ruff (default config)
- **Models:** PascalCase. Fields: snake_case. Some Italian field names (`tipo`, `mese`, `anno`, `citta`, `settore`, `azione`, `ufficio`, `responsabili`)
- **Views:** Mix of class-based (CBV with mixins) and function-based views
- **Permissions:** `LoginRequiredMixin`, `StaffRequiredMixin`, `@login_required`, `@staff_required` decorators
- **Status constants:** `PENDING`, `APPROVED`, `DISCARDED`, `SENT` on Article model
- **Multilingual fields:** `_en`, `_it`, `_rs` suffixes (English, Italian, Serbian)
- **Templates:** Django template language with HTMX partials in `templates/partials/`
- **i18n:** English and Italian via Django's `{% trans %}` and locale files

## Testing

- Test settings: `analyst/test_settings.py` (separate MongoDB database `activities_test`)
- Uses MD5 password hasher, in-memory email, dummy cache for speed
- Run: `python manage.py test activities --settings=analyst.test_settings`

## Key Patterns

- Scrapers are Scrapy spiders run via Crochet (Twisted reactor in Django process)
- AI translation/summarization via Pydantic AI agents with configurable LLM models
- Semantic search uses Sentence Transformers embeddings + hybrid search with ML reranking
- Celery tasks handle embedding generation, translations, and scheduled scraping
- PDF reports generated with WeasyPrint; Excel with openpyxl
- HTMX used for dynamic partial template updates without full page reloads
