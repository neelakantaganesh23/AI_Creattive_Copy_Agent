# CLAUDE.md — AI Creative Copy Agent

Repository conventions for this monorepo. The original build specification is kept verbatim in
`CLAUDE.md.txt`; this file records how the implementation is actually organised.

## Layout

- `backend/` — FastAPI + SQLAlchemy + Alembic (Python 3.11+)
- `frontend/` — React 18 + TypeScript + Vite + Material UI
- `docker-compose.yml` — backend + Nginx-served frontend

## Commands

```bash
# Backend (from backend/, venv active)
uvicorn app.main:app --reload
pytest
ruff check .
alembic upgrade head
python -m app.database.seed

# Frontend (from frontend/)
npm run dev
npm run lint      # eslint + tsc --noEmit
npm run test
npm run build
```

## Backend conventions

- **Layering:** route → service → repository → model. Route handlers stay thin: validate,
  delegate, return. No queries in handlers, no HTTP concepts in services.
- **Dependencies** are injected via FastAPI `Depends` (`DbSession`, `CurrentUser`,
  `RequireAdmin`, `RequireEditor` in `app/api/deps.py`).
- **Errors:** raise a subclass of `AppError` (`app/core/errors.py`). Never raise `HTTPException`
  directly — the handler in `main.py` renders the standard `{"error": {...}}` envelope.
- **Configuration** comes from `app.core.config.settings` only. No literal URLs, keys or model
  names anywhere else. Adding a setting means updating `.env.example` too.
- **Agents** (`app/agents/`) never touch the ORM. They read a plain `WorkflowContext` and report
  progress through the `WorkflowRecorder` protocol; the DB-backed recorder lives in
  `app/services/generation_service.py`.
- **AI providers** implement the `AIProvider` protocol in `app/services/ai/provider.py`. Mock and
  Gemini implementations stay in separate modules and are selected only in `factory.py`.
- **Logging:** structured, via `app.core.logging.get_logger`. Never log passwords, tokens, API
  keys or request headers; the formatter redacts credential-like keys as a backstop.
- **Style:** ruff, line length 100, `from __future__ import annotations`, full type hints.

## Frontend conventions

- **Strict TypeScript.** `any` is an ESLint error; prefer `unknown` plus narrowing.
- **Token handling** lives only in `src/api/client.ts`. The access token is in memory; the
  refresh token is an HttpOnly cookie. Never write tokens to `localStorage`.
- **API calls** go through the typed modules in `src/api/`. Components never call axios directly.
- **Components** are small and presentational; data fetching lives in hooks (`src/hooks/`) or
  pages. Business rules belong on the backend.
- **Forms** use React Hook Form with a Zod resolver from `src/schemas/forms.ts`.
- **Styling** goes through the Material UI theme (`src/theme/theme.ts`). Use theme tokens rather
  than literal colours.
- **Accessibility:** every icon-only button needs an `aria-label`; async status changes are
  announced through a polite live region; keep focus states visible.

## Testing

- Backend: pytest with a temporary SQLite file, mock AI provider, zero stage delay, and rate
  limiting disabled (`tests/conftest.py`).
- Frontend: Vitest + React Testing Library with mocked API modules. `restoreMocks` is on, so
  mock implementations must be re-established in `beforeEach`.
- Never let a test reach a real AI provider or the network.

## Non-goals

- No server-side rendering.
- No multi-tenancy; a single organisation is assumed.
- No marketing email sending or campaign delivery — the product ends at generated, exportable
  copy. Transactional account email (password reset) is the sole exception and lives behind
  the `EmailSender` interface in `app/services/email/`.
