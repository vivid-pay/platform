# Story template and Definition of Ready

Every Jira story in project `VPAY` follows this shape. Create stories under their epic.

```
**As** <who>, **I want** <what> **so that** <why>.

**Acceptance criteria**
- [ ] Observable, testable statement (an endpoint and status code, a constraint that rejects bad data, ...)
- [ ] ...

**Technical notes**
- Decided by ADR-000x (link); blockers: "Blocked by VPAY-n" (one per line)
- Constraints, out-of-scope items, open questions
```

Labels: the service (`wallet-service`), the kind (`api`, `database`, `devops`, `security`, `docs`,
`automation`), and `foundation` where relevant.

## Definition of Ready (a story may be worked when)
- [ ] It fits in one pull request (roughly one focused working session)
- [ ] Each acceptance criterion can be checked by a test or a command
- [ ] Blockers are named and Done, or the story says why it is safe to start
- [ ] It agrees with the ADRs, and any needed decision has its own ADR story first
- [ ] It does not smuggle in unrelated work (split it instead)

## Writing good criteria
- Say what is observable ("returns 404 for another user's wallet"), not how it is coded.
- Include the unhappy paths: invalid input, missing data, duplicates, concurrency.
- State anything money-related precisely: units (minor units), currency, sign, rounding.
