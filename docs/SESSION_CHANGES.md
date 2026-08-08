# Session Changes — RAG Knowledge Base, Ticket Workflow, and Roles

This documents every functional change made to TriagePilot in this session, in the order they landed. Each section covers what changed, why, how it works, where it sits in the architecture, before/after behavior, the concepts you need to explain it, and a short spoken explanation you can reuse as-is.

---

## 1. RAG Knowledge Base Pipeline (PDF → chunks → embeddings → search)

**Files:** new `backend/tickets/rag.py`, new `DocumentChunk` model in `backend/tickets/models.py`, migration `0009_documentchunk.py`, new management command `backend/tickets/management/commands/ingest_pdf.py`, `backend/tickets/knowledge_base.py` (wiring), new `backend/test_rag_chunking.py`.

### What changed
Before this session, `search_knowledge_base()` in `knowledge_base.py` only ever searched a hardcoded Python list of 20 fake KB articles (`KB_ARTICLES`). There was no way to feed it real documentation. I built a full pipeline that turns an actual PDF into searchable, embedded text chunks stored in the database, and wired it in as the *first* thing the search function tries.

### Why
The project's own description (`triagepilot-project-description.md`) frames the agent as calling "your existing RAG knowledge-base API as a tool" — the hardcoded articles were explicitly a placeholder (`TODO: Wire in real RAG API`). You wanted to be able to upload real documents (e.g. a Terms of Service PDF) and have the agent actually answer from them.

### How
The pipeline is five stages, all in `rag.py`:

1. **Extraction** (`extract_pages`) — `pypdf.PdfReader` pulls text per page. `clean_text` undoes common PDF-extraction artifacts: words split across a line by a hyphen, running page-number lines, ragged whitespace.
2. **Structuring** (`split_sections`, `is_heading`) — a heuristic (short, capitalized, unpunctuated lines) detects section headings within a page, so each chunk can carry its nearest heading as metadata.
3. **Recursive chunking** (`_recursive_split`, `_merge_to_target`, `_overlap_tail`, `chunk_pages`) — text is split on the coarsest separator that gets pieces under a hard cap (paragraph → line → sentence → word → character), then small adjacent pieces are merged back up toward a target size. Target is ~650 tokens, hard cap 800, minimum 40 (below that a chunk is dropped as noise). Consecutive chunks *within the same section* get ~75 tokens of overlap from the tail of the previous chunk, so a fact split across a chunk boundary doesn't get lost. There's no tokenizer installed, so tokens are estimated at 4 characters each — close enough for English prose.
4. **Embedding** (`embed_texts`) — chunks are sent to Ollama's `mxbai-embed-large` model (already installed, no new dependency) and the resulting vectors are **normalized to unit length** on write. That's a deliberate choice: with unit vectors, cosine similarity becomes a plain dot product, which is both cheaper to compute in Python and matches what a future pgvector cosine index would do natively.
5. **Search** (`search_chunks`) — embeds the incoming query the same way, then scores every stored chunk by dot product against it, filtered by category and/or document name, thresholded at a minimum score, sorted best-first.

`ingest_pdf()` ties it together: extract → chunk → embed → `DocumentChunk.objects.bulk_create()`. Re-ingesting a document with the same name first deletes its old chunks, so re-uploading replaces rather than duplicates.

`knowledge_base.py`'s `search_knowledge_base()` was changed to try `search_chunks()` first; if that returns nothing (no documents ingested, or nothing clears the similarity threshold), it falls back to the original hardcoded-article search, now renamed `_search_static_articles()`. Both paths return the same shape (`id`, `title`, `content`, `category`, `relevance_score`), so nothing downstream — the agent's prompts — needed to change.

**Storage decision:** vectors are stored in a plain Django `JSONField` on SQLite, not pgvector, because there's no Postgres server yet. This is intentional and documented in a `ponytail:` comment at the top of `search_chunks()`: it's a full table scan with a Python dot-product loop per chunk, which is fine for a few thousand chunks but won't scale. The upgrade path is explicit: swap `JSONField` for `pgvector.django.VectorField` and replace the Python loop with `ORDER BY embedding <=> %s LIMIT n` once the project is on PostgreSQL — the unit-normalized vectors are already shaped for that.

A `python manage.py ingest_pdf <path> [--category X] [--name Y] [--clear]` command exists for CLI ingestion, though the primary path ended up being admin upload (see §2).

### Context
This sits between the ticket-triage agent (`agent.py`) and the database. The agent doesn't call `rag.py` directly — it goes through `knowledge_base.search_knowledge_base()`, which is the same interface it always used. That's why swapping the implementation underneath was safe: the contract didn't change, only what's behind it.

### Before vs After
- **Before:** every ticket's "KB search" matched against 20 fixed fake articles, regardless of what documentation actually existed.
- **After:** if a PDF has been uploaded and ingested, ticket search finds real chunks from it by semantic similarity; if nothing matches or nothing's been uploaded, it silently falls back to the old fake articles so nothing breaks.

### Key concepts
- **Chunking:** breaking a long document into smaller pieces so each piece fits in an LLM's context and stays topically coherent enough to embed meaningfully.
- **Embedding:** converting text into a vector of numbers such that semantically similar text produces vectors that are numerically close together.
- **Cosine similarity via dot product:** if two vectors are both unit length (magnitude 1), their dot product *equals* the cosine of the angle between them — a cheap way to measure "how similar" two pieces of text are.
- **Recursive/hierarchical splitting:** trying the least-disruptive separator first (paragraphs) and only falling back to more aggressive ones (words, characters) when a piece is still too big.

### How to explain it
"I built a RAG pipeline that takes an uploaded PDF, extracts and cleans the text, splits it into ~650-token overlapping chunks with metadata (which document, page, section), embeds each chunk with a local Ollama model, and stores the vectors. When a ticket comes in, its text gets embedded the same way and compared against every stored chunk by cosine similarity, so the agent's replies can cite real uploaded documentation instead of hardcoded fake articles. It's currently a Python loop over vectors stored in SQLite, which I've documented as a known scaling limit — the fix is Postgres + pgvector, and the code's already shaped for that swap."

---

## 2. Admin-Only PDF Upload

**Files:** `KnowledgeDocument` model in `models.py`, migration `0013_knowledgedocument.py`, `backend/tickets/admin.py`, `backend/backend/settings.py` (MEDIA config), `backend/backend/urls.py` (serve media in DEBUG).

### What changed
Added a new model, `KnowledgeDocument`, with a `file` upload field and a `category` field, registered in Django admin. Saving it in the admin panel triggers the full ingestion pipeline from §1 automatically.

### Why
You wanted PDF upload to be admin-only — no customer-facing or staff-facing upload UI, no new API endpoint, just Django's built-in admin.

### How
`KnowledgeDocumentAdmin.save_model()` is overridden: after the base save persists the uploaded file to disk, it calls `rag.ingest_pdf(obj.file.path, document_name=str(obj), category=obj.category)` and stores the returned chunk count back on the object. If ingestion throws (e.g. Ollama isn't running), it's caught and shown as an admin error message rather than a 500 page; if the PDF has no extractable text, a warning message is shown instead. `delete_model()` and `delete_queryset()` are also overridden so deleting a `KnowledgeDocument` cleans up its `DocumentChunk` rows too — otherwise you'd get orphaned, unreachable chunks left behind.

Since uploaded files need somewhere to live, `MEDIA_ROOT`/`MEDIA_URL` were added to `settings.py`, and `urls.py` now serves that directory via Django's `static()` helper when `DEBUG=True` (standard Django dev pattern, not something that ships to production as-is).

### Context
This is the *input* side of §1's pipeline — it's the only way documents currently get into the RAG system in this project (the CLI command from §1 also works, but admin upload is the intended path).

### Before vs After
- **Before:** no way to add real documents at all.
- **After:** go to `/admin/tickets/knowledgedocument/add/`, upload a PDF, optionally tag a category, save — it's chunked, embedded, and searchable within seconds.

### Key concepts
- **Django admin `ModelAdmin` hooks** (`save_model`, `delete_model`, `delete_queryset`): the standard way to run custom logic around admin CRUD operations without building a separate view.
- **`MEDIA_ROOT`/`MEDIA_URL`:** Django's convention for where user-uploaded files live on disk vs. the URL path they're served from — distinct from `STATIC_URL`, which is for your own CSS/JS.

### How to explain it
"PDF upload only exists through Django admin, on purpose — I added a `KnowledgeDocument` model with a file field, and overrode the admin's save hook so that uploading a file there immediately runs it through the ingestion pipeline. Deleting the record in admin cleans up its chunks too, so nothing orphans."

---

## 3. Two RAG Bug Fixes (found while verifying end-to-end)

**Files:** `rag.py` (`search_chunks`), `agent.py` (`build_decision_prompt`).

### What changed
While verifying the pipeline actually worked with a real uploaded PDF, I found and fixed two real bugs:

1. **Category filter excluded uncategorized documents entirely.** `search_chunks()` filtered `DocumentChunk.objects.filter(category=category)`. A document uploaded without a category (category = `None`) would never match, because the agent *always* passes a real category (`technical`/`billing`/`account`/`general`) when it searches — there's no code path where it searches with `category=None`. So any uncategorized upload was permanently unreachable. Fixed by changing the filter to `Q(category__isnull=True) | Q(category=category)` — an uncategorized document now matches *every* ticket category, while a categorized one stays scoped to just that category.

2. **The agent hallucinated a fake citation.** `build_decision_prompt()`'s JSON-format instructions to the LLM used a literal, hardcoded example: `"sources_cited": ["KB001", "KB002"]` and `Cite KB article IDs in brackets: "According to [KB001]..."`. The local model (llama3.2) was found to literally echo `[KB001]` in its drafted replies even when the actual retrieved source was, say, `DOC7` — because `KB001` was the only concrete example it had ever been shown, regardless of what was actually in context. Fixed by computing `example_id = kb_articles[0]['id']` (falling back to `"KB001"` only when there are no articles at all) and using that real ID in both places in the prompt.

### Why
Both bugs were invisible until a real PDF was uploaded and run through a real ticket — the hardcoded test articles always had `category` set, so bug #1 never showed up before; and the fallback KB articles happened to line up closely enough with `KB00x`-style IDs that bug #2's hallucination wasn't obviously wrong before. This is why I ran the actual live pipeline (real Ollama calls, not mocks) rather than trusting the code to be correct by inspection.

### How
Both are one-line-scope fixes at their respective root causes — the shared filter function and the shared prompt-building function — not patches applied per-caller.

### Context
Bug #1 lives inside the retrieval layer from §1. Bug #2 lives inside the agent's decision-drafting step (`agent.py`, called from `TicketViewSet.triage` in `views.py`) — it's the step that takes retrieved KB articles and asks the LLM to draft a reply citing them.

### Before vs After
- **Before:** an uncategorized upload was invisible to search; even when a real chunk *was* found, the drafted reply could cite a made-up ID that didn't correspond to anything shown to the model.
- **After:** verified live, 3 runs in a row, uncategorized documents get retrieved for any category, and the reply consistently cited the real ID (`[DOC7]`) with phrasing grounded in that chunk's actual text.

### Key concepts
- **Prompt grounding:** an LLM given a hardcoded example in its instructions will often pattern-match to that literal example rather than substituting the real value from context — especially smaller local models. The fix is to make the example itself dynamic/real rather than fixed.
- **Silent failure vs. loud failure:** bug #1 didn't error — it just quietly returned zero results, which is why it needed an actual retrieval test to catch, not just code review.

### How to explain it
"I found two bugs by actually running a real ticket through the live pipeline instead of trusting the code by inspection. One: uncategorized PDFs were invisible to search because the category filter had no 'match anything' case — fixed with an OR condition. Two: the LLM was hallucinating a fake citation `[KB001]` because that's the literal example baked into the prompt — fixed by grounding the prompt's example in a real retrieved ID instead of a hardcoded one."

---

## 4. Role Rename: `agent` → `staff`

**Files:** `models.py` (`ROLE_CHOICES`, `STAFF_ROLES`), `permissions.py`, migration `0010_role_agent_to_staff.py`, `frontend/src/App.jsx`, `frontend/src/auth.js`.

### What changed
The `UserProfile.role` value `'agent'` was renamed to `'staff'` everywhere it appears: the model's choices, the permission check in `permissions.py`, the frontend's route guards and role-array, and a Django migration that both renames the schema choice *and* updates any existing database rows with `role='agent'` to `role='staff'`.

### Why
"Agent" was ambiguous in this codebase — it means both "the AI agent" (`agent.py`, `agent_reasoning` field, `categorize_ticket()`) and "a human support-staff role." That's confusing both in code and in the Django admin dropdown, where a role picker showing "Agent" next to a project whose whole pitch is "an AI agent" is misleading.

### How
Django migration `0010` is written as a `RunPython` data migration *followed by* a schema `AlterField` — deliberately in that order, so any existing `role='agent'` rows get renamed before the choices list changes underneath them. It's reversible: the migration includes both `agent_to_staff` and its inverse `staff_to_agent`, so `manage.py migrate tickets 0009` would cleanly roll it back.

The `IsAgent` permission class in `permissions.py` was *not* renamed — only the role string it checks (`'agent'` → `'staff'`) — because grepping the codebase showed that class is actually dead code (nothing imports it; the real staff-check is `IsSupportStaff` in `views.py`). Renaming an unused class would have been scope creep.

### Context
This touches the authorization layer that gates the whole staff-facing side of the app: `IsSupportStaff` (used on `DecisionLogViewSet`), `is_staff_role` property on `UserProfile` (used everywhere a request needs to know "is this a customer or staff member"), and the frontend's `STAFF_ROLES` array that decides which routes (`/triage`, `/triage/:id`) a logged-in user can reach.

### Before vs After
- **Before:** Django admin showed role options Customer / Agent / Admin; a JWT's `role` claim said `"agent"`.
- **After:** same three roles, now labeled Customer / Staff / Admin; existing accounts migrated automatically, no manual data fixup needed.

### Key concepts
- **Data migration vs. schema migration:** a schema migration changes the shape of a table (columns, choices); a data migration changes the *values* inside it. Doing both correctly, in the right order, in one Django migration file (`RunPython` + `AlterField`) is how you rename an enum-like field without orphaning existing rows.

### How to explain it
"I renamed the support-staff role from 'agent' to 'staff' to stop it colliding with 'the AI agent' terminology used everywhere else in the code. It's a single reversible Django migration that renames any existing rows before changing the schema's allowed choices, plus matching updates in the permission check and the frontend's route guards."

---

## 5. Follow-Up Messaging System

**Files:** `TicketMessage` model (`models.py`), migration `0011_ticketmessage.py`, `TicketMessageSerializer` + `TicketSerializer.resolution` (`serializers.py`), `TicketViewSet.messages` action (`views.py`), `admin.py` registration, new `frontend/src/components/MessageThread.jsx`, wired into `frontend/src/pages/TicketDetail.jsx` and `frontend/src/pages/DecisionDetail.jsx`, tab toggle in `frontend/src/pages/TriageQueue.jsx`.

### What changed
Before this, once staff approved/rejected a ticket's proposed reply, that was the end of the interaction — the customer's `TicketDetail` page only ever showed the raw status word ("approved"), never the actual reply text, and there was no way for either side to say anything further. I added: (a) a `resolution` field on the ticket API response that surfaces the actual approved reply text and its cited sources, and (b) a `TicketMessage` model plus a `GET/POST /api/tickets/{id}/messages/` endpoint for an ongoing follow-up thread, shared by a new `MessageThread` React component mounted on both the customer's and staff's ticket views.

### Why
You asked for this directly: "after the staff approves of the decision then show that decision to the user, currently it only shows approved, also provide a way to follow up to the reply by the staff."

### How
- **Showing the reply:** `TicketSerializer.get_resolution()` looks up the ticket's most recent `DecisionLog` where `human_decision` is `'approved'` or `'edited'`, and returns `{reply, sources, decided_at}`. It deliberately excludes `'rejected'` decisions — nothing was ever sent to the customer in that case, so there's nothing to show. This required no new endpoint; it's a field added to the existing `TicketSerializer`.
- **The thread:** `TicketMessage` is a simple model (`ticket`, `sender`, `body`, `created_at`). The `messages` action on `TicketViewSet` handles both GET (list the thread) and POST (append to it). Crucially, it does **not** define its own permission logic — it calls `self.get_object()`, which goes through `TicketViewSet.get_queryset()`, the same method that already scopes non-staff users to their own tickets. That means a customer literally cannot reach another customer's thread; the visibility rule was reused, not reimplemented.
- **The component:** `MessageThread.jsx` takes a single `ticketId` prop and is mounted in two different places — `TicketDetail.jsx` (customer side, shown once a `resolution` exists) and `DecisionDetail.jsx` (staff side, shown once a decision has been made and wasn't rejected). One component, two contexts, because the underlying data and permission model are identical.
- **Staff discoverability:** `TriageQueue.jsx` originally only ever queried `/decisions/?status=pending`, which lists tickets *never yet decided*. Once a ticket was approved, it vanished from that list forever — so I added a Pending/All tab toggle so staff can navigate to an already-decided ticket to see (and reply to) new follow-ups. (This surfaced a deeper bug, fixed in §6.)

### Context
This is layered directly on top of the existing `Ticket` → `DecisionLog` relationship (the original human-in-the-loop approve/reject flow) without modifying it — a `TicketMessage` thread is a separate, parallel concept: it doesn't create new `DecisionLog` rows or re-trigger the AI agent, it's just a conversation log.

### Before vs After
- **Before:** customer's ticket page showed only the word "approved"; no way to say anything further to staff.
- **After:** customer sees the actual reply text and cited sources, plus a message box to ask a follow-up; staff can find that ticket (via the new All tab) and reply in the same thread.

### Key concepts
- **Reusing an existing permission boundary instead of reimplementing it:** the `messages` action didn't need its own ownership check because `get_object()` already enforces one via `get_queryset()`. This is the same principle used again in §8 and §10.
- **Shared component across two roles:** `MessageThread` doesn't know or care if it's rendered for a customer or a staff member — it just reflects whatever `sender_role` the API returns per message.

### How to explain it
"I added a `TicketMessage` model for a simple back-and-forth thread on each ticket, separate from the original AI-decision flow, plus a `resolution` field so the customer actually sees the approved reply text instead of just the word 'approved.' One React component renders the thread on both the customer's and staff's pages — it reuses the same `/tickets/{id}/messages/` endpoint, and that endpoint reuses the ticket's existing ownership check rather than reimplementing permissions."

---

## 6. Ticket Reopening Logic + Staff Queue Visibility Fix

**Files:** `views.py` (`TicketViewSet.messages`, `DecisionLogViewSet.get_queryset`), `TicketSerializer.created_by_username` (`serializers.py`), `frontend/src/pages/DecisionDetail.jsx`.

### What changed
You reported: "when user sends a follow up it does not show in staff." I traced this to the actual root cause — not a broken message endpoint (that worked fine end-to-end when tested directly), but the fact that staff's default "Pending" queue is driven entirely by `DecisionLog.human_decision`, which is completely decoupled from whether new messages exist on the ticket. Once a decision was approved, that `DecisionLog` row's `human_decision` field never changes again, so the ticket could never reappear in the default queue view no matter what happened afterward.

Fixed with two coordinated changes:
1. In `TicketViewSet.messages`, a customer's follow-up on an `'approved'` ticket now flips `ticket.status` to `'in_review'`; a staff reply on an `'in_review'` ticket flips it back to `'approved'`.
2. In `DecisionLogViewSet.get_queryset`, the `status=pending` filter was widened from `human_decision__isnull=True` alone to `Q(human_decision__isnull=True) | Q(ticket__status='in_review')` — so a reopened-but-already-decided ticket reappears in staff's default queue automatically.

Also added `created_by_username` to `TicketSerializer` and displayed it on `DecisionDetail.jsx` ("Submitted by ...") — a separate but related ask, since staff reviewing a reopened ticket need to know who they're talking to.

### Why
This was a genuine bug, not a missing feature — the message *did* save correctly, but staff had no way to discover it existed without already knowing to click into that specific ticket.

### How
I verified this by hitting the real HTTP endpoints (not calling view methods directly) end-to-end: posted a customer follow-up on an approved ticket, confirmed the ticket's status flipped to `in_review`, confirmed the `/decisions/?status=pending` endpoint now included it, confirmed a staff reply flipped it back to `approved` and it dropped out of the pending list again. All four steps passed.

The fix is deliberately in the *shared* `get_queryset()` method rather than patched into the frontend `TriageQueue.jsx` component — any current or future caller of the pending-decisions endpoint benefits, not just that one page.

### Context
This directly builds on §5's messaging feature — it's the mechanism that makes the follow-up thread actually *actionable* for staff, not just theoretically visible if they happen to navigate to the right URL.

### Before vs After
- **Before:** a customer follow-up saved successfully but the ticket silently vanished from staff's radar forever (unless staff happened to remember and manually browse "All").
- **After:** a customer follow-up automatically reopens the ticket into staff's default Pending queue; a staff reply resolves it again, closing the loop.

### Key concepts
- **Root-cause fix vs. symptom patch:** the tempting fix would have been "add a banner to the frontend queue page." The actual fix is in the queryset every page's data ultimately comes from — one change, correct everywhere.
- **Status as a workflow signal:** `'in_review'` already existed as a ticket status (originally meaning "AI has categorized it, awaiting first decision") — reusing it to also mean "reopened, awaiting a reply" instead of inventing a new status value is a deliberate reuse of an existing concept rather than adding a new one.

### How to explain it
"A customer's follow-up was saving fine, but staff's default queue only ever looked at whether a decision had been made — not whether new activity happened after. I fixed it at the source: a customer follow-up now reopens the ticket's status, and the queue's query was widened to include reopened tickets, so it just shows back up where staff already look, no new UI needed."

---

## 7. Close Ticket Feature

**Files:** `models.py` (`STATUS_CHOICES`), migration `0012_alter_ticket_status.py`, `TicketViewSet.close` (`views.py`), `frontend/src/pages/TicketDetail.jsx`, `frontend/src/pages/TicketList.jsx`.

### What changed
Added a `'closed'` status and a `POST /api/tickets/{id}/close/` endpoint that only the ticket's own creator can call, plus a "Close ticket" button on the customer's ticket page.

### Why
Direct request — customers had no way to mark their own resolved ticket as done.

### How
`TicketViewSet.close()` checks `ticket.created_by_id != request.user.id` and returns 403 if it doesn't match (staff are explicitly excluded from this action — the docstring notes "staff don't get this button, they use approve/reject on the decision"), and returns 400 if the ticket's already closed. Verified with three scenarios over real HTTP: a non-owner gets 404 (blocked earlier, by `get_queryset` — they can't even see the ticket exists), the owner gets 200, and closing an already-closed ticket gets 400.

### Context
This is a customer-only action, independent of the staff approve/reject decision flow — a ticket can be closed regardless of whether it was ever approved, rejected, or never triaged at all.

### Before vs After
- **Before:** four statuses (`pending`, `in_review`, `approved`, `rejected`), no customer-initiated end state.
- **After:** five statuses; customers can voluntarily close their own ticket at any point.

### Key concepts
- **Object-level permission check inside an action**, as opposed to a class-level `permission_classes` — because "can close" depends on *which* ticket and *who's* asking, not just "is this user authenticated."

### How to explain it
"Added a 'closed' status and an endpoint gated so only the ticket's original submitter can close it — checked with an explicit ownership comparison inside the view, not just relying on authentication."

---

## 8. Delete Closed Tickets

**Files:** `TicketViewSet.perform_destroy` (`views.py`), `frontend/src/pages/TicketDetail.jsx`, `frontend/src/pages/DecisionDetail.jsx`.

### What changed
DRF's `ModelViewSet` gives every viewset a working `DELETE` endpoint for free, with no extra code — and until this change, `TicketViewSet`'s was completely unrestricted by ticket status (a customer could already delete an in-progress ticket, losing its audit trail). I overrode `perform_destroy()` to reject deletion unless `ticket.status == 'closed'`, and added a "Delete ticket" button (replacing "Close ticket" once already closed) on both the customer's `TicketDetail.jsx` and the staff's `DecisionDetail.jsx`.

### Why
Direct request: "provide a way for the staff and user to delete closed tickets" — implicitly, *only* closed ones.

### How
One `perform_destroy()` override, in the same viewset both roles already share — no separate staff-delete vs. customer-delete code paths. Ownership is still enforced by the existing `get_queryset()` (a non-owner, non-staff user gets a 404 before ever reaching the status check, since they can't see the ticket at all). Verified with three real HTTP cases: owner deleting a non-closed ticket → 403; a stranger trying to delete someone else's closed ticket → 404 (never even visible to them); staff deleting a closed ticket → 204 and it's actually gone from the database.

Both frontend buttons use a native `window.confirm()` before calling delete — a deliberate choice not to build a custom confirmation modal component for a single destructive action.

### Context
Builds directly on §7 — deletion is only reachable from the state that feature introduced.

### Before vs After
- **Before:** `DELETE /api/tickets/{id}/` worked on *any* ticket regardless of status (a latent, unused gap — no frontend button called it).
- **After:** deletion is explicitly gated to closed tickets only, with a visible button for both roles.

### Key concepts
- **DRF `ModelViewSet` default actions:** `list`/`create`/`retrieve`/`update`/`partial_update`/`destroy` all exist automatically once you subclass `ModelViewSet` — `perform_destroy()` is the correct override point to add business-rule gating without touching the routing or the base `destroy()` method.

### How to explain it
"Ticket deletion already existed as an unrestricted DRF default — I locked it down to only work on closed tickets, in one shared override, so both the customer's and staff's delete buttons go through the same rule."

---

## 9. Send → Sent UI Feedback

**File:** `frontend/src/components/MessageThread.jsx`.

### What changed
After a follow-up message successfully sends, the "Send" button now swaps to "Sent" (with a checkmark icon) for 1.5 seconds before reverting.

### Why
Direct UI request, based on a screenshot of the composer.

### How
A `justSent` boolean state is set to `true` right after a successful POST, with a `setTimeout` (tracked in a `useRef` so it can be cleared on unmount, avoiding a "set state on unmounted component" warning) reverting it after 1500ms. The button's icon and label are simple ternaries on that state.

### Context
Purely cosmetic, isolated to the shared `MessageThread` component from §5 — so it applies identically wherever that component is mounted (both customer and staff views).

### Before vs After
- **Before:** button always said "Send," no confirmation feedback beyond the message appearing in the list.
- **After:** brief "Sent" + checkmark confirmation on every successful send.

### Key concepts
- **Transient UI state with cleanup:** using a ref to hold a timeout ID specifically so it can be cancelled in a `useEffect` cleanup function if the component unmounts before the timer fires.

### How to explain it
"Small UX polish — the send button flips to a checkmarked 'Sent' state for 1.5 seconds after a successful send, using a timeout that's properly cleaned up on unmount."

---

## 10. Follow-Up Rate Limiting (max 3 in a row)

**Files:** `TicketViewSet.messages`, `TicketViewSet._consecutive_customer_messages` (`views.py`), `frontend/src/components/MessageThread.jsx`.

### What changed
A customer can no longer send more than 3 follow-up messages in a row without a staff reply in between — the 4th attempt is rejected server-side, and the frontend composer proactively swaps for a "please wait" message once the limit is hit.

### Why
Direct request, to prevent follow-up spam from one side dominating a thread before the other side has responded.

### How
`_consecutive_customer_messages()` walks the ticket's message thread backward from the newest message, counting how many in a row are from non-staff senders, stopping at the first staff/admin sender it finds. If that count is already 3 when a customer tries to POST a new message, the request is rejected with `429 Too Many Requests` and a plain-English detail message — checked *before* the message is created, so nothing partial gets saved. A staff reply is never rate-limited and, per §6, also resets the counter by breaking the backward scan early.

The frontend mirrors this with `consecutiveCustomerMessages()`, a pure function over the already-loaded message array, gated behind `!isStaff()` (reusing the existing `auth.js` role check) so staff viewing the same thread are never shown the limit UI at all.

Verified end-to-end over real HTTP: 3 customer messages succeed (201 each), the 4th returns 429 with the expected detail message, a staff reply succeeds, and the customer can immediately send again afterward.

### Context
Layered directly on top of §5's messaging thread and reuses §6's staff/customer role distinction — no new model or endpoint, just an additional check inside the existing `messages` POST handler.

### Before vs After
- **Before:** a customer could send unlimited follow-up messages with no staff response required.
- **After:** capped at 3 unanswered messages in a row, both enforced server-side (the real rule) and reflected client-side (so the UI doesn't invite an action that will just fail).

### Key concepts
- **Server-side enforcement with client-side mirroring:** the actual rule lives in the API (verified by testing the endpoint directly, independent of any UI) — the frontend copy of the same logic is purely for a better user experience (not showing an input box that will just error), not the source of truth.
- **`429 Too Many Requests`:** the semantically correct HTTP status for "you're sending too much, slow down," as distinct from `400` (bad input) or `403` (not allowed at all, ever).

### How to explain it
"Customers are capped at 3 follow-up messages in a row before a staff reply — enforced server-side by counting backward through the thread until hitting a staff message, returning 429 past that limit. The frontend mirrors the same count to swap the input for a wait message, but that's just UX — the real rule is server-side and I verified it directly against the API, not just through the UI."

---

## Summary Table

| # | Change | Primary files | Type |
|---|---|---|---|
| 1 | RAG pipeline (chunk/embed/search) | `rag.py`, `models.py`, `knowledge_base.py` | New feature |
| 2 | Admin-only PDF upload | `models.py`, `admin.py`, `settings.py` | New feature |
| 3 | Category filter + citation hallucination fixes | `rag.py`, `agent.py` | Bug fix |
| 4 | Role rename `agent` → `staff` | `models.py`, `permissions.py`, migration `0010` | Refactor |
| 5 | Follow-up messaging system | `models.py`, `serializers.py`, `views.py`, `MessageThread.jsx` | New feature |
| 6 | Staff queue visibility fix | `views.py`, `DecisionDetail.jsx` | Bug fix |
| 7 | Close ticket | `models.py`, `views.py`, `TicketDetail.jsx` | New feature |
| 8 | Delete closed tickets | `views.py`, `TicketDetail.jsx`, `DecisionDetail.jsx` | New feature |
| 9 | Send → Sent feedback | `MessageThread.jsx` | UI polish |
| 10 | Follow-up rate limiting | `views.py`, `MessageThread.jsx` | New feature |

All backend changes were verified against real HTTP requests (Django's test `Client`, not mocked view calls) and, where an LLM was involved, against a real running Ollama instance — not just static code review.
