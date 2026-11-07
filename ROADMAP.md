# Vivid Pay: roadmap

Jira (project `VPAY`, https://sithumkaushitha.atlassian.net) is the only source of truth for **status**:
what is done, in progress or blocked is read there, never from this file.
This file holds **intent and order** only. Update it when the plan changes, not when work finishes.

## Phases and Jira epics

| # | Phase | Jira epic | Outcome |
|---|---|---|---|
| 0 | Project foundation | VPAY-4 | Repos, CI, conventions, ADRs, `/ticket` automation, product-owner agent |
| 1 | Wallet service: accounts | VPAY-5 | Create wallet, read balance, list wallets, freeze/unfreeze; first migration |
| 2 | First deploy ("walking skeleton") | VPAY-8 (first slice) | Docker image, Terraform for a minimal AWS dev environment, CD from `develop` |
| 3 | Wallet service: ledger and transfers | VPAY-6 | Double-entry ledger, top-up, transfers, idempotency, history, reconciliation |
| 4 | Security | VPAY-7 | Keycloak, JWT, RBAC, threat model, rate limiting, audit log, scanning, secrets |
| 5 | Other services | VPAY-8 / new epics | `funding-service` (sync calls, sagas), `notification-service` (events) |
| 6 | Observability and hardening | VPAY-9 | Structured logs, metrics, tracing, SLOs, alerts, load and chaos tests |
| 7 | Full delivery pipeline | VPAY-8 | Promotion `release/x.y.z` to staging and production with approval, image scanning and signing, maybe Kubernetes |

Order rationale: get a real slice working, deploy it early so infrastructure problems appear while
the app is small, then build the money logic on a live environment.

## Rules for the backlog
- Detailed stories are written only for the epic that is next up; later epics stay as outlines.
- Every story is one pull request in size, has acceptance criteria, and names its blockers.
- A story must agree with the ADRs. If it cannot, an ADR is written or changed first.

## Automation stages
1. **Stage 1 (current):** the product-owner agent (`/groom`) writes and refines tickets; the owner
   chooses what to work on; `/ticket VPAY-n` builds one ticket up to a PR.
2. **Stage 2 (later, a separate decision):** a scheduled run picks the top ready ticket, works it up
   to a PR and notifies the owner. Approval and merge rules stay as they are.
3. **Not planned:** unattended approval or merging.

## Cross-cutting decisions
- ADR-0001 microservices limited to three, ADR-0002 ledger and balance, ADR-0003 money as minor units:
  [`docs/adr/`](docs/adr/README.md) (the index also lists the service-level ADRs in `wallet-service`).
