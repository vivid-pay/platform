# Architecture decision records

ADRs for the whole Vivid Pay system. **System-wide** decisions (they affect more than one service, or the
product itself) live here. **Service-specific** decisions live in that service's `docs/adr/`.

## Numbering
One global sequence across all repos. The next ADR number is the highest number in the table below, plus one.
Update this table in the same piece of work that adds an ADR. Copy [0000-template.md](0000-template.md).
Numbers are never reused or renumbered, because code, Jira tickets and docs cite them (for example `ADR-0003`).

## Index
| ADR | Title | Status | Lives in |
|---|---|---|---|
| [0001](0001-microservices-with-three-services.md) | Microservices, limited to three deliberate services | accepted | platform |
| [0002](https://github.com/vivid-pay/wallet-service/blob/develop/docs/adr/0002-ledger-and-balance-model.md) | Double-entry ledger with a stored balance projection | accepted | wallet-service |
| [0003](0003-money-representation.md) | Money as integer minor units plus a currency code | accepted | platform |
| [0004](0004-api-error-format.md) | API errors as RFC 9457 problem details | accepted | platform |
| [0005](https://github.com/vivid-pay/wallet-service/blob/develop/docs/adr/0005-sonarqube-quality-gate.md) | SonarQube Cloud quality gate on new code | accepted | wallet-service |
| [0006](https://github.com/vivid-pay/wallet-service/blob/develop/docs/adr/0006-temporary-owner-identity-header.md) | Temporary caller identity from the X-User-Id header | accepted | wallet-service |
