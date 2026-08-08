# AI Marketing OS — CLAUDE.md

Agentic marketing platform for Indian D2C apparel brands (demo brand: fictional "Urban
Thread"). Phase 1: 4-agent LangGraph pipeline (strategy → creative → compliance → publish),
human-in-the-loop approval, email (Brevo) + web push (FCM) delivery, full React frontend,
deployed on Render + Vercel. Full spec: see project brief in PLAN.md history / repo owner.

## Stack

- Backend: Python 3.12, `uv`, FastAPI, Pydantic v2, LangGraph (`PostgresSaver` checkpointer)
- DB: Supabase Postgres + `pgvector`, Supabase Auth (JWT), RLS on every table
- LLM: provider abstraction (Gemini / Groq / Cerebras) with router, token-bucket rate
  limiting, automatic failover, dev-only response cache — see `backend/llm/`
- Observability: Langfuse Cloud (agent-node + LLM-call spans only)
- Frontend: Vite, React 19, TypeScript strict, Tailwind v4, shadcn/ui, `motion` v12+,
  TanStack Query + Router, Zod (kept in sync with backend Pydantic schemas)
- Delivery: Brevo (email, 300/day free), Firebase Cloud Messaging (web push)
- Infra: Render free (backend), Vercel Hobby (frontend), Docker Compose (local Postgres)

## Commands

- `make dev` — run backend (uvicorn) + frontend (vite) together
- `make test` — backend pytest + frontend test runner
- `make lint` — ruff + mypy (backend), eslint + tsc --noEmit (frontend)
- `make migrate` — apply SQL migrations to local/dev Postgres

## Directory map

```
/backend
  /agents      campaign_manager.py, strategy.py, creative.py, compliance.py, publish.py, graph.py
  /llm         providers/, router.py, rate_limiter.py, cache.py
  /schemas     brief.py, strategy.py, copy.py, compliance.py, publish.py
  /api         routes/, deps.py, sse.py
  /services    brevo.py, fcm.py
  /db          client.py, models.py, migrations/
  /core        config.py, langfuse.py, errors.py
  /tests       unit/, integration/, fixtures/
/frontend
  /src/styles      tokens.css   <- single source of design truth, no hardcoded hex elsewhere
  /src/routes      login, dashboard, campaigns.new, runs.$id, runs.$id.approve
  /src/components  agent-timeline/, brief-form/, previews/, ui/
  /src/lib         api.ts, schemas.ts, sse.ts, motion.ts
/infra           docker/, .github/workflows/, seed/
```

## Conventions

- No agent code calls a vendor LLM SDK directly — always through `LLMRouter`.
- Inter-agent payloads are Pydantic models validated via structured-output/JSON-schema mode.
  No regex-parsing of model output.
- Every inter-agent schema in `backend/schemas/` has a matching Zod schema in
  `frontend/src/lib/schemas.ts`; checked for parity in CI.
- Commit per task (conventional commits), not per milestone.
- Long-running agent graph execution happens via FastAPI `BackgroundTask` + `run_events`
  table — never inside the synchronous request/response cycle (Render free has no workers).
- Approval flow uses LangGraph `interrupt()` + `PostgresSaver` only — never the in-memory
  checkpointer.
- Idempotent publish: unique constraint on `(campaign_id, channel, recipient_hash)`.
- No silent mocks — missing keys / unreachable APIs fail loudly at startup or call time.
- Never hardcode a model ID; read from config/env.

## Non-goals (Phase 1)

No Kubernetes/Celery/queue broker · no separate vector DB (pgvector only) ·
no Prometheus/Grafana · no auth beyond Supabase Auth · no image generation ·
no in-app MCP servers · no SMS/WhatsApp · no A2A/Google ADK · no microservices ·
no personalization/analytics/A/B-variant agents.

## MCP / tooling

Supabase MCP, Vercel MCP, Playwright MCP, context7 MCP — added at project scope.
No GitHub MCP; use native `git`/`gh`.
