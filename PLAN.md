# AI Marketing OS — Phase 1 Plan

Milestones from §11 of the build spec, expanded into tasks with a definition of done.
Rules that apply to every task: verify API shapes/limits against live docs before writing an
integration; no silent mocks; commit per task with conventional commits; tests before moving
on; ask before adding any dependency not named in the spec.

Legend: **DoD** = definition of done. A task is not done until its DoD is demonstrable.

---

## M0 — Skeleton

**Goal:** both apps boot, CI is green, database reachable, migrations runnable.

| # | Task | DoD |
|---|---|---|
| 0.1 | Repo scaffold: `/backend`, `/frontend`, `/infra` trees per §13; `.gitignore`; MIT-less private repo | Directory map matches CLAUDE.md exactly; `git status` clean |
| 0.2 | Backend init with `uv`: `pyproject.toml`, Python 3.12 pin, FastAPI + Pydantic v2 + uvicorn | `uv run uvicorn` serves; `uv.lock` committed |
| 0.3 | `backend/core/config.py`: Pydantic `Settings` reading every key in §4; fail fast at startup with a named-key error message | App refuses to boot with a missing required key and says which one |
| 0.4 | `.env.example` with all §4 keys, each documented with where to get it | Every key in §4 present with a comment; no real secret in the file |
| 0.5 | `GET /health` returning app version + DB connectivity | `curl /health` → 200 with `{"status":"ok","db":"ok"}` |
| 0.6 | Docker Compose: local Postgres 16 + `pgvector` extension | `docker compose up -d` then `psql -c 'select extversion from pg_extension where extname=$$vector$$'` returns a version |
| 0.7 | Migrations runner: versioned SQL files in `backend/db/migrations/`, applied in order, tracked in a `schema_migrations` table | `make migrate` is idempotent — running twice is a no-op |
| 0.8 | Migration 001: full §6 schema + RLS enabled on every table + the `delivery_attempts` unique constraint | `list_tables` shows all tables; RLS on; duplicate insert into `delivery_attempts` raises |
| 0.9 | Supabase project created; `DATABASE_URL` + auth keys wired; migrations applied to remote | Same schema exists locally and in Supabase; Supabase advisors report no critical issues |
| 0.10 | Frontend init: Vite + React 19 + TS strict + Tailwind v4 + TanStack Query/Router | `pnpm dev` serves a page; `tsc --noEmit` clean |
| 0.11 | `Makefile`: `dev`, `test`, `lint`, `migrate` | `make dev` brings up both apps in one command |
| 0.12 | Lint/type config: ruff + mypy (strict-ish), eslint + tsc | `make lint` exits 0 |
| 0.13 | CI workflow: lint + typecheck + tests on push/PR, **zero live API calls** | Green check on a PR |

**Milestone DoD:** `make dev` brings up both apps; CI is green; migrations applied to
Supabase; health endpoint proves DB connectivity.

---

## M1 — LLM layer

**Goal:** the routing/limiting/failover substrate everything else sits on.

| # | Task | DoD |
|---|---|---|
| 1.0 | **Verification pass** — confirm current model IDs, free-tier RPM/TPM/RPD and SDK versions for Gemini, Groq, Cerebras from official docs; record findings + date in `backend/llm/PROVIDERS.md` | Doc contains today's date, source URLs, and the numbers actually used in config |
| 1.1 | `LLMProvider` protocol: `complete()`, `complete_structured(schema)`, `embed()`; provider-agnostic request/response dataclasses incl. token usage | Protocol has no vendor types in its signature |
| 1.2 | `GeminiProvider` (google-genai) with structured output via response schema | Unit test with a recorded response validates into a Pydantic model |
| 1.3 | `GroqProvider` + `CerebrasProvider` (OpenAI-compatible) with JSON-schema structured output | Same test passes for both |
| 1.4 | `rate_limiter.py`: per-provider token bucket enforcing RPM + TPM + RPD, injectable clock | Unit tests with frozen time prove each of the three limits blocks independently |
| 1.5 | `router.py`: routing policy (deterministic → Groq/Cerebras, generative → Gemini), exponential backoff with jitter on 429, failover to next healthy provider, provider health tracking | Unit test: primary returns 429 → call succeeds on fallback, no exception escapes |
| 1.6 | `cache.py`: dev-only response cache keyed on `(provider, model, prompt_hash)`, off by default in prod | Cache hit avoids a provider call; disabled when `ENV=production` |
| 1.7 | Langfuse span per LLM call: provider, model, prompt/completion tokens, latency, cost, retry count | A call produces exactly one span with all fields populated |
| 1.8 | Concurrency guard: never more than 3 concurrent calls, and only after checking router budget | Test firing 10 concurrent requests observes max 3 in flight |
| 1.9 | Embeddings via Gemini → pgvector; store model name + dimension alongside each vector | Round-trip: embed text, insert, cosine-search returns it; dimension recorded |
| 1.10 | `scripts/llm_soak.py`: 50 calls across 3 providers, deliberately trips a rate limit | See milestone DoD |

**Milestone DoD:** the soak script fires 50 calls across 3 providers, deliberately hits a
rate limit, fails over cleanly, zero unhandled 429s, and every call appears in Langfuse with
correct token counts.

---

## M2 — One agent, end to end

**Goal:** brief in → structured copy out, through the real API path.

| # | Task | DoD |
|---|---|---|
| 2.1 | `schemas/brief.py`: `MarketingBrief` per §7, with validation (dates coherent, discount 0–100, ≥1 channel) | Unit tests cover valid + each invalid case |
| 2.2 | `schemas/copy.py`: `ChannelCopySet` (email subject lines, body, preheader; push title/body) | Schema round-trips through JSON-schema mode |
| 2.3 | `agents/creative.py`: single agent, channel-specific prompt templates as tools (not one agent per channel) | Adding a channel means adding a template, not an agent |
| 2.4 | Minimal LangGraph graph: `brief_intake → creative_content_agent`, `PostgresSaver` from the start | Graph compiles; checkpoints land in Postgres |
| 2.5 | `POST /api/campaigns` — validate brief, insert `runs` row (`status=queued`), schedule `BackgroundTask`, return `202 {run_id}` | Response is immediate (<200 ms); run executes after |
| 2.6 | `run_events` writes on every node transition; `GET /api/runs/{id}` polls status + partial outputs from that table | Killing and restarting the app mid-run leaves events intact and readable |
| 2.7 | Persist output to `campaign_outputs`; Langfuse span per agent node | Row exists, validates against `ChannelCopySet` |
| 2.8 | Golden fixtures: 5 canned Urban Thread briefs + recorded LLM responses; graph test runs against them with zero live calls | `pytest` passes offline with no API keys set |

**Milestone DoD:** `POST /api/campaigns` returns a run_id, polling shows completion, and the
persisted output validates against the Pydantic schema.

---

## M3 — Full graph + approval

**Goal:** all four agents, human-in-the-loop, survives restarts.

| # | Task | DoD |
|---|---|---|
| 3.1 | `schemas/strategy.py` (`CampaignStrategy`), `schemas/compliance.py` (`ComplianceReport` with per-violation line references), `schemas/publish.py` (`PublishPlan`) | Full chain `MarketingBrief → CampaignStrategy → ChannelCopySet → ComplianceReport → PublishPlan` typed end to end |
| 3.2 | `agents/strategy.py`: audience segmentation, offer framing, channel plan, calendar | Output validates; traced |
| 3.3 | `agents/compliance.py`: brand voice, grammar/QA, India compliance (TRAI DND, opt-out language, consent wording) | Rule unit tests: known-bad copy is flagged with the offending line |
| 3.4 | `agents/campaign_manager.py`: orchestrator — plans, routes, merges outputs | Graph routes through it, not around it |
| 3.5 | Retry loop: compliance failure routes back to creative with violations attached, max 2 retries, then escalate to human with violations shown | Test: forced 3rd failure ends in escalation, not infinite loop |
| 3.6 | `interrupt()` before publish; graph pauses with state persisted | Run sits at `awaiting_approval` with full state in Postgres |
| 3.7 | `POST /api/runs/{id}/approve` and `/reject` (with revision notes) resuming the checkpointed graph; writes to `approvals` | Reject re-enters creative with notes; approve proceeds |
| 3.8 | `GET /api/runs/{id}/events` — SSE stream of node transitions + token counts, reading `run_events` | Two clients attach mid-run and both see consistent state |
| 3.9 | Failure handling: per-node retry with backoff; terminal failure → `status=failed_partial` preserving completed work | Test: node 3 fails permanently, nodes 1–2 output survives and is readable |
| 3.10 | **Restart test (§5.3)**: start run → hit interrupt → restart the app process → resume from checkpoint → publish | See milestone DoD |

**Milestone DoD:** the restart test passes. If it doesn't, M3 is not done.

---

## M4 — Frontend

**Goal:** the operations console, designed before it is coded.

| # | Task | DoD |
|---|---|---|
| 4.1 | **Design exploration (§9.1)** in Claude Design: 2–3 genuinely different directions for dashboard + run timeline; must avoid the three banned looks in §8.1 | Directions presented to you side by side |
| 4.2 | **Direction picked with you (§9.2)** — I do not proceed on my own judgment | Explicit approval recorded here |
| 4.3 | `frontend/src/styles/tokens.css`: colors, fluid type scale (`clamp()`), spacing, radii, shadows, motion durations/easings | Zero hardcoded hex anywhere in component code (lint rule or grep check in CI) |
| 4.4 | Fonts: display grotesque (restraint), Inter (body/UI), JetBrains Mono (traces, JSON, token counts, run IDs) | Mono used only for machine output |
| 4.5 | Agent graph component with two states: ambient (login background) and live (dashboard rail) | Same component, same DOM nodes, two states |
| 4.6 | `/login` (§8.2): centered card, Supabase email+password, "Continue as demo user", ambient graph behind, all real states (idle/loading/invalid/network/rate-limited), inline validation on blur | Every listed state reachable and screenshotted; errors say what happened and how to fix it |
| 4.7 | **Login → dashboard shared-element transition (§8.3)**: card scales 0.96 + fades (150 ms), graph brightens and re-lays-out into the live rail via `layoutId`, chrome staggers at 40 ms; ~450–550 ms, `cubic-bezier(0.16,1,0.3,1)`; nothing else animates on entry | Screen-recorded; `prefers-reduced-motion: reduce` gives a straight crossfade with no transforms |
| 4.8 | **Run timeline (signature element)**: horizontal agent track lighting up in sequence, SSE-driven, streaming token counts + elapsed time, each node expandable to structured output | Drives a real run live with no console errors |
| 4.9 | `/` dashboard: active runs, recent campaigns, live per-provider LLM quota | Empty states are invitations with a real primary action |
| 4.10 | `/campaigns/new`: multi-step brief form (§7), Zod-validated, saves drafts | Draft survives a reload |
| 4.11 | `/runs/:id/approve`: rendered email preview, push preview, compliance report with each violation linked to the offending line; approve / reject-with-notes | Optimistic approve, rolled back on failure |
| 4.12 | `/campaigns/:id`: what went out, which channels, delivery status | Reflects real `delivery_attempts` rows |
| 4.13 | Zod ↔ Pydantic parity check in CI | CI fails when a backend schema changes without the Zod counterpart |
| 4.14 | Quality floor (§8.5): keyboard-navigable with visible focus rings, WCAG AA on every token pair, skeletons not spinners, fluid 360 px → 2560 px | Screenshot evidence per screen; contrast table checked |
| 4.15 | Screenshot critique pass per screen (§9.5) — look at it, fix it, then remove one thing | Before/after noted per screen |

**Milestone DoD:** full flow driveable in a browser with no console errors; reduced-motion,
keyboard-only, and 360 px each verified by screenshot.

---

## M5 — Real delivery

**Goal:** it actually sends, exactly once.

| # | Task | DoD |
|---|---|---|
| 5.1 | Verification pass: current Brevo + FCM API shapes and free-tier limits | Recorded with date + source URLs |
| 5.2 | `services/brevo.py`: transactional send, sender identity, error surfacing (no silent failure) | Real email lands in a real inbox |
| 5.3 | `services/fcm.py` + frontend service worker, VAPID key, token registration, permission UX | Real push fires on a real device |
| 5.4 | `agents/publish.py`: consumes `PublishPlan`, writes `delivery_attempts` before send, skips already-sent recipients | Idempotency test: publishing twice sends once |
| 5.5 | Delivery status surfaced in `/campaigns/:id` | Per-recipient status visible, provider message IDs stored |
| 5.6 | Seed data: Urban Thread brand, guidelines (embedded), product catalog, demo recipients | `make seed` populates a working demo |

**Milestone DoD:** an approved campaign lands in a real inbox and fires a real push
notification, with no double-sends.

---

## M6 — Deploy

**Goal:** a stranger can use it.

| # | Task | DoD |
|---|---|---|
| 6.1 | Backend on Render free: Dockerfile/build, env vars, migrations on deploy | Health endpoint green on the public URL |
| 6.2 | Cold-start handling: Render free spins down after 15 min with ~60 s cold start; ephemeral FS; frontend shows an honest "waking up" state rather than a hung spinner | Documented in README + visible in UI |
| 6.3 | Frontend on Vercel Hobby, pointed at the Render backend, CORS correct | Public URL loads and authenticates |
| 6.4 | GitHub Actions deploy on merge to `main` | Push → deploy, both apps |
| 6.5 | Seeded Urban Thread data in production + working demo user | "Continue as demo user" works on the live URL |
| 6.6 | README: architecture, setup, env keys, cold-start behavior, and the §12 manual checklist (reduced motion, keyboard only, 360 px, cold start from sleep) | A stranger can follow it |
| 6.7 | E2E Playwright: login → transition → submit brief → approve → sent | Passes in CI against seeded data |

**Milestone DoD:** a stranger opens the URL, logs in as demo, and runs a campaign end to end.

---

## Cross-cutting, set up during M0

- `.mcp.json` at project scope: supabase, vercel, playwright, context7 (§10)
- `.claude/skills/add-agent-node.md` — schema → node → graph wiring → Langfuse span → test
- `.claude/skills/add-delivery-channel.md` — client → idempotency → preview component → test
- `.claude/agents/frontend-reviewer.md` — screenshots a route, critiques against §8.1
- `.claude/agents/schema-guard.md` — Pydantic ↔ Zod parity
- Hooks running `ruff`, `mypy`, `pytest -q`, `tsc --noEmit` after edits
- Plan mode for anything touching the LangGraph graph definition

## Open items needing your input

1. **GitHub push** — `gh` CLI isn't installed and the GitHub connector isn't authorized in
   this session. Local repo is initialized; I need one of: `gh` installed + authed, the
   connector authorized, or an empty repo created by you and the URL handed to me.
2. **Accounts** — Supabase, Google AI Studio, Groq, Cerebras, Langfuse, Brevo, Firebase all
   need signup by you. Per your call, I scaffold first and wire keys as each milestone needs
   them; M1's DoD and M5's DoD cannot be met without real keys.
3. **Design direction (4.2)** is an explicit stop-and-decide point.
