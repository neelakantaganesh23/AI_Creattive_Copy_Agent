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
  `app/services/generation_service.py`. Each stage is a class with
  `run(context, recorder)`, listed in order in `orchestrator.py` and mirrored by
  `AGENT_SEQUENCE`/`AGENT_METADATA` in `app/models/enums.py` — the frontend stepper is driven
  entirely by that metadata, so adding a stage needs no frontend change.
- **Models** are Pydantic AI agents. `app/agents/runtime.py` is the only module that constructs
  one: `AI_PROVIDER=gemini` builds a `GoogleModel` from `GEMINI_FLASH_MODEL`/`GEMINI_PRO_MODEL`,
  `AI_PROVIDER=mock` builds a `FunctionModel` replaying the fixtures in `mock_content.py`. Always
  call models through `runtime.run_agent`, which maps Pydantic AI exceptions onto `AppError`
  subclasses. Prompts live in `app/agents/prompts.py`, never inline.
- **Content rules** live in the `rules` table and are the single source of truth. Machine-checkable
  types are enforced by `app/agents/rules.py`, wired as the copy agent's `output_validator`: an
  `error`-severity violation raises `ModelRetry` so the model corrects itself mid-run, a `warning`
  is recorded and accepted. `guideline` rules are natural language and are assessed by the judge in
  `app/agents/validation.py`. The `LIMIT_*` settings only seed the table on a fresh install.
- **Copy is never discarded over a rule.** When the model cannot satisfy every rule the closest
  attempt is kept, quality drops to `warning`, and the surviving violations are returned.
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

- Backend: pytest with a temporary SQLite file, mock model runtime, zero stage delay, and rate
  limiting disabled (`tests/conftest.py`).
- Frontend: Vitest + React Testing Library with mocked API modules. `restoreMocks` is on, so
  mock implementations must be re-established in `beforeEach`.
- Never let a test reach a real AI provider or the network.

## Non-goals

- No server-side rendering.
- No multi-tenancy; a single organisation is assumed.
- No campaign email delivery to third parties — the product ends at generated, exportable copy.
  The one exception beyond transactional account email (password reset) is self-test-send:
  `POST /generations/{id}/send-test-email` mails the Email-channel copy to the requesting
  user's own address only, so they can preview it in a real inbox. There is no recipient field
  on that request and no path to arbitrary or list-based recipients — sending to anyone other
  than the account holder remains out of scope pending consent and unsubscribe handling.
  All delivery, transactional or self-test, goes through the `EmailSender` interface in
  `app/services/email/`.
