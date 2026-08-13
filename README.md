# AI Creative Copy Agent

Generate audience-specific marketing copy for **Email**, **Mobile** and **SMS** through a
six-stage AI workflow. Full-stack application: React 18 + TypeScript + Material UI frontend,
FastAPI + SQLAlchemy backend, JWT authentication, SQLite persistence, Alembic migrations,
structured logging, tests and Docker support.

The application runs end to end **without any AI credentials** using a deterministic mock
provider, and switches to Google Gemini through configuration alone.

---

## Contents

- [Quick start](#quick-start)
- [Development login credentials](#development-login-credentials)
- [Project structure](#project-structure)
- [The generation workflow](#the-generation-workflow)
- [API summary](#api-summary)
- [Database and migrations](#database-and-migrations)
- [Configuring Gemini](#configuring-gemini)
- [Testing and quality](#testing-and-quality)
- [Docker](#docker)
- [Security notes](#security-notes)
- [Known limitations](#known-limitations)
- [Recommended production steps](#recommended-production-steps)

---

## Quick start

### Windows PowerShell

Backend:

```powershell
cd backend; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt; Copy-Item .env.example .env; uvicorn app.main:app --reload
```

Frontend (a second terminal):

```powershell
cd frontend; npm install; Copy-Item .env.example .env; npm run dev
```

### macOS / Linux

Backend:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --reload
```

Frontend (a second terminal):

```bash
cd frontend && npm install && cp .env.example .env && npm run dev
```

### URLs

| Service | URL |
| --- | --- |
| Frontend | <http://localhost:5173> |
| Backend | <http://localhost:8000> |
| OpenAPI docs | <http://localhost:8000/docs> |
| Health / readiness | <http://localhost:8000/health>, <http://localhost:8000/ready> |

On first start the backend creates the SQLite schema and inserts the development seed data
(users, brands, products, audience segments, CTA rules and templates). Both behaviours are
controlled by `AUTO_CREATE_TABLES` and `SEED_ON_STARTUP`, which must be `false` in production.

---

## Development login credentials

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@example.com` | `ChangeMe123!` |
| Marketer | `marketer@example.com` | `ChangeMe123!` |

> **These accounts exist for local development only.** They are created by
> `backend/app/database/seed.py` and are inserted only while `SEED_ON_STARTUP=true`. Set
> `SEED_ON_STARTUP=false` and change `SEED_ADMIN_PASSWORD` / `SEED_MARKETER_PASSWORD` before any
> deployment. `APP_ENV=production` refuses to boot with seeding enabled.

### Roles

| Role | Permissions |
| --- | --- |
| `admin` | Manage brands, products, audience segments, CTA rules and templates; read every generation and log; create generations. |
| `marketer` | Create, regenerate and delete their own generations; read taxonomies. |
| `viewer` | Read-only: may view generations and logs, may not create or modify anything. |

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/           # The six workflow agents + orchestrator
│   │   ├── api/routes/       # Thin HTTP handlers
│   │   ├── core/             # Config, security, logging, errors, middleware, rate limiting
│   │   ├── database/         # Engine, session, declarative base, seed data
│   │   ├── models/           # SQLAlchemy models and enums
│   │   ├── repositories/     # Data access
│   │   ├── schemas/          # Pydantic request/response/AI-output schemas
│   │   ├── services/         # Auth, generation orchestration, dashboard
│   │   │   └── ai/           # AIProvider protocol, mock, Gemini, grounding, factory
│   │   ├── utils/            # Text similarity, JSON repair
│   │   └── main.py           # App factory, middleware, exception handlers
│   ├── alembic/versions/     # 0001_initial_schema.py
│   ├── tests/                # 85 pytest tests
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pyproject.toml        # ruff + pytest configuration
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios client, interceptors, typed endpoints
│   │   ├── components/       # auth/ common/ dashboard/ generate/ layout/
│   │   ├── config/           # Typed environment access
│   │   ├── contexts/         # AuthContext + AuthProvider
│   │   ├── hooks/            # useAuth, useTaxonomy, useGenerationRunner
│   │   ├── layouts/          # AppLayout (sidebar + header shell)
│   │   ├── pages/            # Login, Register, Dashboard, Generate, History, ...
│   │   ├── routes/           # AppRoutes, ProtectedRoute
│   │   ├── schemas/          # Zod form schemas
│   │   ├── services/         # Clipboard and download helpers
│   │   ├── styles/           # Global CSS
│   │   ├── theme/            # Material UI theme and design tokens
│   │   ├── types/            # API model types
│   │   └── utils/            # Formatting helpers
│   ├── tests/                # 48 Vitest + React Testing Library tests
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── eslint.config.js
│   ├── vite.config.ts
│   └── .env.example
├── docker-compose.yml
├── CLAUDE.md
└── README.md
```

---

## The generation workflow

`POST /api/v1/generations` persists a queued generation with six pending stage rows and returns
`202 Accepted` immediately. The workflow then runs as a background task while the frontend polls
`GET /api/v1/generations/{id}/status`, which is what drives the live stepper.

| # | Agent | Responsibility |
| --- | --- | --- |
| 1 | Data Extraction | Brand, products, SKUs, features, tone, campaign goal, key message. Public figures are extracted **only** when the brief names them explicitly. |
| 2 | Web Search Grounding | Searches only for extracted entities, records sources separately, and never injects unsupported claims. Disabled by default; a failure is recoverable and marks the run "not externally grounded". |
| 3 | Copy Generation | Produces Email, Mobile and SMS copy in one structured call, given audience profile, brand guidelines, channel limits and previously generated copy. |
| 4 | Repetition Fix | Compares against recent generations for the same brand/product using combined sequence + token similarity. Rewrites only above `REPETITION_SIMILARITY_THRESHOLD`, and never touches the CTA. |
| 5 | CTA Optimization | Fully deterministic. No model involved — see below. |
| 6 | Output Parsing & Logging | Validates the final structure with Pydantic, records per-agent duration, model names and status, then persists the result. |

### CTA rules

Stored in the `cta_rules` table. A rule matches when each of `brand_id`, `product_id` and
`channel` is either NULL (wildcard) or equal to the generation's value. Among the matches, the
highest `priority` rule whose placeholders can all be resolved wins. Placeholders: `{product}`,
`{brand}`, `{channel}`, `{audience}`.

Seeded defaults:

| Priority | Template | Applies when |
| --- | --- | --- |
| 100 | `SHOP {product}` | A product is selected |
| 50 | `EXPLORE {brand}` | A brand but no product is selected |
| 10 | `SHOP THE COLLECTION` | Neither is selected |

### Output schema and limits

```jsonc
{
  "email":  { "headline": "…", "sub_heading": "…", "cta": "…" },
  "mobile": { "superline": "…", "pre_heading": "…", "headline": "…", "sub_heading": "…", "cta": "…" },
  "sms":    { "description": "…" }
}
```

Character limits (all configurable via `LIMIT_*` environment variables): email 80/160/40;
mobile 30/50/70/140/40; SMS 160. Exceeding a limit produces a visible quality **warning** rather
than discarding otherwise valid copy. Malformed model JSON gets one deterministic repair pass
(fences, prose, trailing commas), then one model-side repair attempt; if it still fails, the API
returns a structured `AI_INVALID_OUTPUT` error and the payload stays in the internal logs only.

---

## API summary

Base path `/api/v1`. Full interactive documentation at `/docs`.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` |
| Generations | `POST /generations`, `GET /generations`, `GET /generations/{id}`, `GET /generations/{id}/status`, `POST /generations/{id}/regenerate`, `DELETE /generations/{id}` |
| Dashboard | `GET /dashboard/summary`, `GET /dashboard/recent` |
| Brands | `GET/POST /brands`, `GET/PUT/DELETE /brands/{id}` |
| Products | `GET/POST /products`, `GET/PUT/DELETE /products/{id}` |
| Audience segments | `GET/POST /audience-segments`, `GET/PUT/DELETE /audience-segments/{id}` |
| CTA rules | `GET/POST /cta-rules`, `GET/PUT/DELETE /cta-rules/{id}` |
| Templates | `GET/POST /templates`, `GET/PUT/DELETE /templates/{id}` |
| Logs | `GET /execution-logs`, `GET /execution-logs/{id}` |
| System (unversioned) | `GET /health`, `GET /ready`, `GET /system/info` |

List endpoints support `page`, `page_size` and resource-specific filters. Every error uses one
shape:

```json
{
  "error": {
    "code": "GENERATION_FAILED",
    "message": "Unable to generate campaign copy.",
    "details": null,
    "request_id": "0b1f…"
  }
}
```

The same request id is returned in the `X-Request-ID` header and attached to every log line.

---

## Database and migrations

Ten tables: `users`, `refresh_tokens`, `brands`, `products`, `audience_segments`, `cta_rules`,
`templates`, `generations`, `agent_executions`, `grounding_sources`. All timestamps are UTC.

```bash
cd backend
alembic upgrade head      # apply migrations
alembic downgrade -1      # roll back one revision
alembic revision --autogenerate -m "describe change"
python -m app.database.seed   # apply seed data explicitly
```

For local convenience `AUTO_CREATE_TABLES=true` creates the schema at startup instead. Use
Alembic — not that flag — anywhere the data matters.

---

## Configuring Gemini

The mock provider is the default. To use a real model:

1. Create an API key in Google AI Studio.
2. Set the following in `backend/.env`:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_FLASH_MODEL=<low-latency model id from Google AI Studio>
GEMINI_PRO_MODEL=<higher-quality model id from Google AI Studio>
```

3. Restart the backend.

**Model identifiers are never hard-coded.** Copy the exact ids from the provider's model list —
the application refuses to start with `AI_PROVIDER=gemini` unless both are set, rather than
guessing a name. The flash model handles extraction, the pro model handles copy generation and
rewrites.

To enable grounding, set `GROUNDING_ENABLED=true` and `GROUNDING_PROVIDER=gemini` (or `mock` for
deterministic local sources). If grounding fails, the run continues from the brief alone and is
labelled "not externally grounded".

---

## Testing and quality

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest

# Frontend
cd frontend
npm run lint     # eslint + tsc --noEmit
npm run test
npm run build
```

Backend coverage spans registration, login, invalid login, token refresh and rotation, protected
routes, role enforcement, generation creation and persistence, schema validation, CTA override
behaviour, repetition detection, history filters, AI provider failure, invalid-JSON repair, rate
limiting and log redaction. Frontend coverage spans login validation and redirect, auth errors,
protected routes, brief validation, channel and audience selection, loading and workflow states,
output rendering, copy actions, API failure states and mobile navigation.

Gemini is never called during tests: the suite pins `AI_PROVIDER=mock`, and frontend tests mock
the API modules.

---

## Docker

```bash
docker compose config
docker compose build
docker compose up --build
```

- Frontend (Nginx): <http://localhost:8080>
- Backend: <http://localhost:8000>

Nginx proxies `/api` to the backend, so the browser sees one origin and the refresh cookie stays
first-party. The SQLite file lives on the named `backend_data` volume. Both services define
health checks and `restart: unless-stopped`.

Set `JWT_SECRET_KEY` (and `GEMINI_*` if used) in the shell or an `.env` file next to
`docker-compose.yml` before starting.

---

## Security notes

- Passwords are hashed with bcrypt (cost 12). Raw passwords are never stored or logged.
- Access tokens are short-lived JWTs held **in memory** by the frontend; refresh tokens are
  opaque, stored only as SHA-256 hashes, delivered as `HttpOnly` cookies, and rotated on every
  use (the presented token is revoked immediately).
- Login errors are deliberately generic and constant-time, so the endpoint cannot be used to
  enumerate accounts.
- Rate limiting protects the login and generation routes (`10/minute` and `20/hour` by default).
- CORS origins, request size limits, and cookie `Secure`/`SameSite` flags are environment driven.
- The log formatter redacts any field whose key looks like a credential; request headers are
  never logged.
- Stack traces never reach the client — internal errors return a generic message plus a request
  id for correlation.
- Security headers are set by both the API middleware and the Nginx configuration.

---

## Known limitations

1. **Rate limiting is in-process.** The fixed-window limiter lives in a single worker's memory;
   a multi-process or multi-instance deployment needs a shared store such as Redis.
2. **Background tasks are in-process.** Generations run via FastAPI `BackgroundTasks`. A restart
   mid-run leaves that generation in `running`. A durable queue (Celery, RQ, Arq) is the
   production answer.
3. **SQLite is the default.** Fine for development and single-node use; switch `DATABASE_URL` to
   PostgreSQL for concurrent writers. The models and migration are portable.
4. **Progress is polled, not streamed.** The status endpoint is polled every ~900 ms. Server-sent
   events or WebSockets would remove the latency floor.
5. **Google sign-in is a placeholder.** The button is present and disabled until an OAuth client
   is configured; no OAuth flow is implemented.
6. **Forgot-password has no flow.** The link is rendered for layout parity but is inert.
7. **Passlib was replaced with `bcrypt` directly.** Passlib 1.7.4 (2020, unmaintained) crashes
   during backend detection against bcrypt ≥ 4.1 — `module 'bcrypt' has no attribute '__about__'`.
   The algorithm and cost factor are unchanged; the wrapper is isolated in `app/core/security.py`.
8. **Gemini paths are untested against the live API.** The provider, prompts, JSON repair and
   grounding code are complete, but no API key was available here, so only the mock path has been
   executed end to end.
9. **Docker was not built or validated in this environment** — Docker is not installed on this
   machine, so `docker compose config` and `docker compose build` could not be run.
10. **The mock provider is template-based.** It is deliberately deterministic, which makes the
    repetition-fix stage predictable rather than genuinely creative.

---

## Recommended production steps

1. Move refresh sessions and rate-limit counters to Redis; run several Uvicorn workers behind a
   load balancer.
2. Replace `BackgroundTasks` with a durable job queue, add a reaper for runs stuck in `running`,
   and make generation idempotent per request id.
3. Migrate to managed PostgreSQL; run `alembic upgrade head` as a deploy step with
   `AUTO_CREATE_TABLES=false` and `SEED_ON_STARTUP=false`.
4. Terminate TLS at the edge, set `COOKIE_SECURE=true`, and pin `CORS_ORIGINS` to the real domain.
5. Ship logs to a central store, add request tracing, and alert on generation failure rate and
   p95 latency.
6. Add a secrets manager for `JWT_SECRET_KEY` and `GEMINI_API_KEY`, with rotation.
7. Add per-tenant quotas and cost tracking per generation once the Gemini provider is live.
8. Implement the real Google OAuth flow and a password-reset flow with expiring single-use tokens.
9. Add an approval workflow before generated copy can be exported to a sending platform.
10. Run an accessibility audit with real assistive technology, and add end-to-end tests
    (Playwright) over the critical login → generate → export path.
