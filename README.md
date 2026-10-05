# Aiss Road Backend

FastAPI backend for the Adiss Road safety application.

Run locally:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Health check: `http://127.0.0.1:8001/health`

Configure `.env` from `.env.example`. For Gmail SMTP, use a Google App Password rather than the normal account password.

Admin dashboard: `http://127.0.0.1:8001/admin/`
