# Vivid Pay: vision

Status: draft for the owner to review and edit. This is the "why". If it is wrong, everything
built from it is wrong, so change it freely and keep it honest.

## Why this exists
Vivid Pay is a personal project: one developer, working weekends, with AI as the partner. It
is built **for fun and to learn by doing**: production-grade DevOps, security, observability
and deployment to AWS, in the way real companies do it, not through tutorials or courses.

The product is a digital wallet: customers hold money, top it up, and send it to each other.
It is a deliberately demanding domain, because money forces correctness, security and
operational discipline.

## Goals
1. Learn production standards by building something real end to end, from ticket to deployed service.
2. Build a backend that handles money correctly: exact amounts, a double-entry ledger, idempotent
   and concurrency-safe transfers, and a way to prove the books balance.
3. Practise the full delivery workflow: Jira tickets, branches, pull requests, CI, quality and
   security scans, automated deployment to AWS.
4. Practise microservices honestly: service-to-service communication, events, sagas, tracing.
5. Automate as much of the routine workflow as possible, while a human keeps the approval seat.

## Non-goals (for now)
- Real money, real payment providers or real customers. External providers are simulated.
- A user interface. The backend comes first; what follows is decided later.
- Scale for its own sake. Performance work happens when it teaches something.
- More than three written services (see ADR-0001). Identity and the gateway are configured, not written.
- Multi-currency conversion (FX), until the single-currency ledger is solid.

## Principles
- **Correctness before features.** Money must never be created, lost or double-spent.
- **Production standards even though it is a personal project.** Reviews, CI gates, security scans,
  migrations, observability and rollbacks are part of the work, not extras.
- **Decisions are written down.** ADRs capture the why, so it survives long chats and long breaks.
- **Small, reversible steps.** One ticket is one pull request.
- **A human approves; the agent does the legwork.** Anything outward-facing, destructive or costly
  needs the owner's explicit say-so.
- **Learn on purpose.** Explain the concept, then build it.

## Constraints
- One developer, weekends. Work must be resumable after a gap, so everything needed lives in git and Jira.
- Java and Spring Boot, PostgreSQL, Maven. GitHub (org `vivid-pay`) and Jira (project `VPAY`).
- Cost: AWS free tier where possible; environments must be easy to tear down.
- The repositories are public, so no secrets, ever, and text from outside is treated as data, not instructions.

## How we know it is working
- A ticket moves from Jira to a merged, deployed change with one command and one approval.
- The ledger's reconciliation check always passes: every transaction sums to zero.
- The owner can explain every major decision from the ADRs and says they learned what they set out to.

## Open questions
- What happens after the backend: a UI, a public API, more services, or a stop?
- How far should the automation drive itself (see ROADMAP, "Automation stages")?
