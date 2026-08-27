# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, one interface.

**Support operators (staff role)** are the working users. They sit in a queue of
agent-proposed actions and decide, one ticket at a time, whether a drafted reply
goes to a customer, needs an edit first, or should be rejected. They work the
queue in long sessions, so speed, density, and confident scanning matter more
than first impressions. Confirmed as the design target.

**Customers** submit tickets and read the reply, using a small subset of the app
(submit, list, detail, follow-up thread). They are not repeat users and arrive
with a problem already in hand.

**Evaluators (recruiters, hiring managers)** click through the deployed demo
without setup. They are not designed *for* — the operator tool being genuinely
good is what they are meant to see. Confirmed: design for the operator, stage
for the visitor.

## Product Purpose

TriagePilot reads an incoming support ticket with a locally-hosted LLM, decides
what it is about, searches a knowledge base for evidence, and proposes an action
— a drafted reply with cited sources, an escalation, or a request for more
information. A human approves, edits, or rejects every proposal before anything
reaches a customer. Success is a queue an operator can clear quickly without ever
losing the ability to see why the agent proposed what it proposed.

## Positioning

Not a chatbot. The user-facing product is a triage queue, and the agent's
reasoning is inspectable: what it searched, what it found, which documents it
cited, and what a human did about it. The competing shape — a conversation window
over a RAG index — cannot show its work or hold a human gate.

## Operating Context

- Ticket arrives via the API (simulated helpdesk submission or the in-app form).
- Agent extracts intent, urgency, and category; calls a pgvector-backed RAG
  knowledge-base API as an external tool; proposes an action.
- Proposal lands in the triage queue with status `pending`.
- Operator opens it, reads the customer's text beside the agent's reasoning and
  proposed action, and approves / edits / rejects.
- Decision is logged with its evidence trail. Approved replies become the
  ticket's resolution, visible to the customer along with the cited sources.
- Customer and staff can exchange follow-up messages on a resolved ticket, rate
  limited to three consecutive customer messages before a staff reply.

## Capabilities and Constraints

**Built and working:** JWT auth with email OTP verification, role-based access
(staff vs customer), ticket submit / list / detail, triage queue with pending and
all filters, decision detail with approve / edit / reject, source citations,
follow-up message thread, ticket close and delete.

**Specified but not built:** confidence signaling on proposals, a dedicated
escalation view, search and filter across historical tickets, and the metrics
dashboard (deflection rate, time-to-resolution, human-override rate). Future
visual work must not imply these exist.

**Hard constraints:**
- The human gate is architectural, not a setting. Nothing reaches a customer
  without an explicit human decision.
- Backend functionality is fixed. Same endpoints, same payloads, same auth flow.
  Presentation may change freely; the API contract may not.
- Frontend stack is React 19 + Vite + Tailwind v4 + React Router + framer-motion
  + lucide-react, already installed.

**Terminology:** ticket, decision, proposed action, triage queue, sources cited,
urgency (critical / high / medium / low), category, resolution, follow-up.

## Brand Commitments

None fixed. Confirmed open: the TriagePilot name, the shield-check mark, the
typeface, the palette, page structure, and copy are all replaceable. The backend
contract is the only thing off limits.

## Evidence on Hand

- Real working backend with seeded ticket data; the agent's reasoning, proposed
  action, and source citations are genuine API fields, not mockups.
- No customers, no benchmarks, no deflection statistics, no pricing, no uptime
  or deployment claims. None of these may be invented; the metrics dashboard
  that would produce them does not exist yet.
- Demo ticket content shown on marketing surfaces is authored sample data and
  must be labeled as such where a visitor could mistake it for production
  traffic.

## Product Principles

1. **The gate is the product.** Every surface should make the human decision
   feel consequential rather than frictionless. A rubber-stamp UI defeats the
   architecture.
2. **Show the work.** Reasoning, evidence, and citations are first-class
   content, not disclosure fine print.
3. **The operator's session is long.** Density, keyboard reach, and low-latency
   feedback outrank expression in the working surfaces.
4. **The customer is anxious.** Someone filing a ticket has a problem right now;
   their surfaces answer "what happens next" without being asked.
5. **Claim nothing the backend cannot show.** Unbuilt features stay off the
   screen.

## Accessibility & Inclusion

No product-specific standard established. Baseline: keyboard operability for the
full decision flow, visible focus, and status never carried by color alone.
