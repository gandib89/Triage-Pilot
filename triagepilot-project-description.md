# TriagePilot

**An autonomous support-ticket triage agent with human-in-the-loop oversight, built on Django REST Framework and React.**

---

## Why This One

Out of the three options, a support-triage agent gives you the strongest recruiter story for three reasons: it's a business problem anyone can understand in one sentence (faster ticket resolution, less human toil), it lets your existing RAG knowledge-base API plug directly into it as a tool the agent calls, and it maps almost exactly onto a pattern already proven in the wild — production systems described as agentic AIOps and claims-triage tools with explainable, human-in-the-loop oversight, and Django CRM agents running local LLMs with semantic search and human confirmation. You're not inventing a new category; you're building a well-understood one, competently, end to end.

---

## The Problem It Solves

Support teams drown in incoming tickets that need to be read, categorized, prioritized, and either answered from existing documentation or escalated to the right person. Doing this by hand is slow and inconsistent. TriagePilot automates the *reasoning* part of that workflow — reading each ticket, deciding what it's about, checking whether the answer already exists in the knowledge base, drafting a response or an escalation — while keeping a human in control of every action the agent takes before it goes out.

The pitch in one line: **an agent that reads a ticket, thinks about what to do with it, and shows its work — a human approves, edits, or rejects before anything happens.**

---

## What It Does (Functionality)

At its core, TriagePilot is a pipeline with a reasoning agent in the middle:

1. **Ingest** — tickets arrive via a DRF API (simulating email/helpdesk submission, or a simple form for demo purposes).
2. **Understand** — the agent (running on a local LLM, no external API calls) reads the ticket and extracts intent, urgency, and category.
3. **Investigate** — the agent calls out to your existing RAG knowledge-base API as a tool, searching for relevant documentation or past resolutions.
4. **Decide** — based on what it finds, the agent proposes one of: a drafted reply (with sources cited from the KB), an escalation to a human specialist with a reason, or a request for more information from the customer.
5. **Confirm** — nothing is sent or closed automatically. Every proposed action lands in a queue for a human to approve, edit, or reject.
6. **Learn from the trail** — every decision, every piece of evidence the agent used, and every human override is logged, so the whole reasoning chain is inspectable after the fact.

This is deliberately *not* a chatbot. The user-facing product is a triage queue, not a conversation window — which is a more enterprise-credible shape and avoids looking like every other "RAG chatbot" portfolio project out there.

---

## Key Features

### Agent Intelligence
- **Local LLM reasoning** — runs entirely on a locally-hosted model (e.g. via Ollama), no cloud inference cost or vendor dependency.
- **Hand-built agent loop** — perceive → reason → act cycle written from scratch (no LangChain or similar), so you can speak fluently to exactly how it works in an interview.
- **Tool use** — the agent calls real tools: a knowledge-base search (your RAG API), a ticket-history lookup, and a categorization function — not just free-text generation.
- **Confidence signaling** — every proposed action carries a confidence indicator, so low-confidence cases are visually flagged for closer human review.
- **Reasoning trace** — the agent's intermediate steps (what it searched, what it found, why it chose an action) are captured and viewable, not just the final answer.

### The Triage Queue (React Dashboard)
- **Live incoming-ticket feed** with category, urgency, and proposed-action badges at a glance.
- **Side-by-side review panel** — original ticket on one side, agent's proposed response and cited sources on the other.
- **One-click approve / edit / reject** on every proposed action, with edits feeding back into the audit trail.
- **Escalation view** — tickets the agent flagged as needing a human specialist, with its stated reasoning for the handoff.
- **Search and filter** across historical tickets by status, category, or resolution path.

### Trust & Audit
- **Full decision log** — every ticket's full journey (ingested → reasoned → proposed → human decision → resolved) is stored and queryable.
- **Human-in-the-loop by default** — the agent never sends anything or closes a ticket without explicit approval; this is a hard architectural constraint, not a toggle.
- **Source citation** — any drafted reply that pulls from the knowledge base shows exactly which documents it used.
- **Role-based access** — distinguish between agents who can approve/reject and admins who can see system-wide metrics.

### Integration & System Design
- **Composes with your RAG project** — the knowledge-base API isn't rebuilt, it's called as an external tool, which is a real microservice-style integration story rather than a monolith.
- **Metrics dashboard** — deflection rate (tickets resolved without human drafting), average time-to-resolution, and human-override rate, so you can talk about *impact*, not just features.
- **Deployed, not local-only** — live demo URL, seeded with realistic sample tickets so a recruiter can click around without setup.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django + Django REST Framework |
| Frontend | React |
| Agent runtime | Local LLM via Ollama, hand-written agent loop (no framework) |
| Knowledge retrieval | Your existing pgvector-backed RAG API, called as a tool |
| Database | PostgreSQL |
| Auth | JWT-based, role-based permissions |
| Deployment | No AWS — self-hosted / free-tier friendly (e.g. Render, Railway, or a VPS), consistent with your local-first approach |

---

## Why This Stands Out to Recruiters

- It solves a **real operational problem**, not a tutorial clone — a clear "before/after" story you can tell in an interview.
- It demonstrates **agentic AI beyond retrieval-only** — reasoning, tool use, and decision-making, which is the differentiator over a plain RAG chatbot.
- It shows **system design judgment**: human-in-the-loop as a deliberate constraint, audit logging, and composing two of your own services together instead of building everything as one blob.
- It's **architecturally defensible** — because you built the agent loop yourself instead of importing a framework, you can explain every part of it under questioning, which is exactly what separates a real portfolio project from a copied tutorial.
- It pairs naturally with your RAG API as a **two-project narrative**: "I built a retrieval system, then I built an agent that uses it to take action" is a coherent growth story, not two disconnected side projects.

---

*Next step, if you want it: a full technical spec — data models, the agent-loop pseudocode, API endpoints, and a milestone-by-milestone build order.*
