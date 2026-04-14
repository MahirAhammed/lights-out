# LightsOut

F1 email update service. Sends subscribers automated emails before and after every race weekend -- pre-race previews, qualifying results, sprint results, and race results. Standings and season schedule available as one-time emails with no account required.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), APScheduler |
| Database | PostgreSQL (Supabase) |
| Email | Resend |
| F1 Data | FastF1, Jolpi/Ergast API |
| Frontend | Static HTML/CSS/JS |
| Deployment | Render (backend), Vercel (frontend) |

---

## Project structure

```
init__.py             # Marks directory as a Python package
main.py               # FastAPI entry point & app initialization
├── api/                    # Route handlers (Controllers)
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── subscribers.py  # Subscriber management endpoints
├── config/                 # Settings and Core Configuration
│   ├── __init__.py
│   ├── config.py           # Pydantic Settings (BaseSettings)
│   └── database.py         # SQLAlchemy engine & session setup
├── models.py               # Database models (SQLAlchemy)
├── schemas.py              # Data validation (Pydantic)
├── services/               # Business Logic & Third-party Integrations
│   ├── __init__.py
│   ├── email_service.py    # Resend API & Jinja2 logic
│   ├── f1_data.py          # FastF1 data retrieval & processing
│   └── scheduler.py        # APScheduler tasks & race-week logic
├── templates/              # HTML Email templates (Jinja2)
└── utils/                  # Shared utility functions
    ├── __init__.py
    ├── cache.py            # Custom caching logic
    └── constants.py        # F1-specific constants (Flags, offsets)
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation
├── LICENSE                     # MIT/Open Source License
```
---

## Local setup

**1. Clone and create a virtual environment**
```bash
git clone https://github.com/MahirAhammed/lightsout.git
cd lightsout
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Run**
```bash
uvicorn main:app --reload
```
API docs at `http://localhost:8000/docs`.

---

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string (`postgresql+asyncpg://`) |
| `RESEND_API_KEY` | From resend.com |
| `EMAIL_FROM` | Sender address (must be a verified domain on Resend in production) |
| `FRONTEND_URL` | Base URL of the frontend, used in email links |
| `API_BASE_URL` | Base URL of the backend including `/api/v1` |

---

## Email schedule

| Email | Trigger |
|---|---|
| Verification | On subscribe |
| Welcome | On email verification |
| Pre-race preview | Thursday 08:00 UTC on race weeks |
| Qualifying results | 2 hours after qualifying start |
| Sprint results | 2 hours after sprint start |
| Race results | 3 hours after race start |
| Standings / Schedule | On demand, no account required |

---

## API endpoints

### Subscribers
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/subscribers/subscribe` | Subscribe |
| `GET` | `/api/v1/subscribers/verify` | Verify email (`?token=`) |
| `GET` | `/api/v1/subscribers/unsubscribe` | Unsubscribe (`?token=`) |
| `POST` | `/api/v1/subscribers/onetime` | Request a one-time email |

---
## Data sources

- **FastF1** — session schedule, track info, qualifying and race results
- **Jolpi/Ergast API** — driver and constructor standings

LightsOut is an independent fan project and is not affiliated with Formula 1, the FIA, or any F1 team. Formula 1 and F1 are trademarks of Formula One Licensing BV.