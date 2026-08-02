# TriagePilot — 1-Week Build Plan (2-Person Team)

A realistic, day-by-day plan to build a working end-to-end version of TriagePilot in a week, split across two people, using GitHub properly, and using AI tools (like Kiro) as a learning aid rather than a code generator.

---

## Ground Rules for AI Tools (Kiro, etc.)

The goal is to come out of this week actually understanding what you built. A simple filter for every AI interaction:

**Use AI for:**
- Explaining an error message or stack trace
- Looking up syntax/API usage you're unsure of (e.g. "how does Ollama's Python client work")
- Reviewing code *you already wrote* and suggesting improvements
- Generating boilerplate for repetitive things (test fixtures, seed data)

**Don't use AI for:**
- Writing the agent loop logic itself
- Designing your data models or API structure
- Any chunk of code you paste in without being able to explain every line in a code review

**Rule of thumb:** draft it yourself first → ask AI to review or unstick you → never merge code you can't explain. If you catch yourself about to paste in a full feature an AI wrote, that's the signal to slow down, not speed up.

---

## GitHub Workflow

- **Repo structure:** one monorepo — `/backend` (Django), `/frontend` (React), root `README.md`. Simpler to manage solo-week logistics than two repos.
- **Branches:** `main` stays deployable. Work happens on `feature/<short-name>` branches (e.g. `feature/agent-loop`, `feature/triage-queue-ui`).
- **Pull requests required** — every feature branch gets a PR, and the other person reviews before merge. This is where a lot of the actual learning happens: reading your teammate's approach to the same problem.
- **GitHub Projects board** — a simple Kanban (To Do / In Progress / In Review / Done). Turn each day's tasks below into issues on Day 1 so you have a shared source of truth all week.
- **Commits:** small, imperative ("add ticket serializer", not "stuff"). Small commits make PR review much easier.
- **Daily sync:** 15 minutes, even async in a chat — what got done, what's blocked, any scope decisions made.

---

## Scope for the Week (MVP)

Building the full original spec in a week with two people who are also trying to learn is not realistic — cut deliberately, don't let the week cut it for you by accident.

**In scope:**
- Ticket ingestion (simple form/API — no real email integration)
- Agent categorization + urgency scoring
- Knowledge-base search as a tool call (real if your RAG API is deployed and ready; otherwise stub with 3–5 hardcoded doc snippets and swap in later — track this as a GitHub issue either way)
- Proposed action: drafted reply with cited source, or escalation with a reason
- Human approve / edit / reject queue in React
- Decision log / audit trail (full ticket journey, viewable)
- JWT auth with two roles (agent, admin)
- Local LLM via Ollama
- Deployed live demo (no AWS — Render, Railway, or a small VPS)
- README with architecture diagram + screenshots

**Explicitly cut to "later":**
- Metrics/analytics dashboard
- Fine-grained permissions beyond the two roles
- A polished reasoning-trace visualization (a plain text/JSON view is enough for now)
- Real ticket ingestion channels (email, webhook)
- A large test suite — write a handful of tests that cover the riskiest logic, not full coverage
- Visual polish beyond "clean and readable"

---

## Local LLM Note

For an 8GB-VRAM-class GPU, a quantized ~3B–7B model (e.g. Qwen2.5 7B or Llama 3.2 3B, Q4 quantization) via Ollama gives a reasonable balance of speed and reasoning quality. If your teammate's machine is weaker, keep a smaller model (3B) as a fallback so both of you can run the full pipeline locally without waiting on generation — that difference compounds a lot over a week of iteration.

---

## Day-by-Day Plan

### Day 1 — Setup & Scaffolding
**Both:** Set up the repo, GitHub Projects board with this week's tasks as issues, `.gitignore`, README skeleton. Agree explicitly on the scope list above — write it into the README so it's not just verbal. Install Ollama, pull your chosen model, confirm a basic prompt/response works locally on both machines.

**Person A (backend-leaning):** Django project init, DRF setup, `Ticket` model (subject, body, category, urgency, status, timestamps), initial migration, basic CRUD endpoints.

**Person B (frontend-leaning):** React app scaffold, routing skeleton, ticket list view wired to the real API (even before there's real data), baseline styling.

*End of day:* app runs locally end to end; empty ticket list renders from the real backend.

### Day 2 — Auth & Data Model Completion
**Both:** quick review of Day 1 PRs before starting new work.

**Person A:** JWT auth (`djangorestframework-simplejwt`), a simple role field on the user model, permission classes, `DecisionLog` model (ticket FK, agent reasoning, proposed action, human decision, timestamp, sources used).

**Person B:** login flow + protected routes in React, static ticket detail view, seed ~15 realistic sample tickets via a Django management command (write this together — it's a good small exercise in Django tooling).

*End of day:* can log in and browse seeded tickets; no agent intelligence yet.

### Day 3 — Agent Loop v1 (pair on this one)
This is the highest-learning-value part of the week — do it together rather than splitting it.

**Both:** write the agent loop from scratch as a Python service: build a prompt from a ticket, call the local model through Ollama's API, parse a structured response (category, urgency, confidence). Categorization only for now, no tool use yet. Wire it into a `POST /tickets/{id}/triage/` endpoint that stores results in `DecisionLog` with status `pending_review`.

*End of day:* hitting the triage endpoint on a real ticket returns a real categorization from your local model.

### Day 4 — Tool Use: Knowledge-Base Search
**Person A:** add a `search_knowledge_base` tool function — calls your deployed RAG API over HTTP if it's ready, or returns 3–5 stubbed doc snippets if not (file a follow-up issue to wire in the real one).

**Person B:** extend the agent loop's decision step — after categorization, call the KB tool when relevant, draft a cited reply if there's a good match, otherwise propose an escalation with a stated reason.

**Both:** run 5–10 varied sample tickets through the full pipeline together and tune prompts side by side — this is a good shared-learning checkpoint.

*End of day:* full pipeline works — ticket in, categorized, KB checked, action proposed and logged.

### Day 5 — Human-in-the-Loop UI
**Person B (lead):** build the triage queue — pending decisions list, side-by-side ticket vs. proposed action with cited sources, approve/edit/reject controls.

**Person A (lead):** build the approve/edit/reject endpoints, making sure edits are captured as a diff against what the agent proposed (a nice product-sense detail for later interviews).

**Both:** swap and review each other's PR before merging.

*End of day:* a ticket can be triaged end to end through the actual UI.

### Day 6 — Audit Trail, Error Handling, Tests
**Both:** add a ticket history/timeline view (ingested → agent decision → human action), and graceful error handling — a model timeout, malformed model output, or unreachable KB should fall back to "needs human review," never crash.

Split a small, targeted set of tests: Person A on backend (agent-output parsing, permissions), Person B on frontend/API integration. Clean up any TODOs left from Day 4.

### Day 7 — Deploy, Document, Demo
**Both:** deploy backend + frontend (no AWS), load seed data onto the live instance. Write the README together — problem statement, a simple architecture diagram, setup instructions, a screenshot or GIF of the triage flow, and a short "design decisions" section (why local LLM, why the agent loop is hand-built, why human approval is enforced rather than optional). Record a 2–3 minute demo walkthrough — most recruiters won't run your code, but they will watch a short video. Final joint pass over the app, then tag a `v1.0` release on GitHub.

---

## If the Week Runs Long

Day 3–4 (agent loop + tool use) is the most likely place to slip — parsing structured output from a local model reliably is fiddly and worth the extra time. If you need to borrow time, take it from Day 6's test-writing and Day 7's polish first: a working, deployed end-to-end demo with a rough README beats a fully tested app that never got deployed.
