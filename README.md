# platform

The product-level home of **Vivid Pay**, a digital wallet built as a learning project with production
standards. This repo holds the context that every session and agent needs.

| File | What it is |
|---|---|
| [VISION.md](VISION.md) | Why this exists, goals, non-goals, principles, constraints |
| [ROADMAP.md](ROADMAP.md) | Phases, order and how they map to Jira epics |
| [CLAUDE.md](CLAUDE.md) | How any session orients itself, plus the working agreements |
| [docs/story-template.md](docs/story-template.md) | The Jira story template and Definition of Ready |
| [docs/requirements.md](docs/requirements.md) | Functional and non-functional requirements |
| [docs/adr/README.md](docs/adr/README.md) | Index of all ADRs (both repos), numbering rule, and the system-wide ADRs |
| `.claude/agents/product-owner.md`, `.claude/commands/groom.md` | The product-owner agent and `/groom` |

## Which folder do I open in Claude Code?
- **Planning and backlog discussions:** open `~/Projects/platform`. Run `/groom` to refine the backlog.
- **Building a ticket:** open the service's folder (for example `~/Projects/wallet-service`) and run `/ticket VPAY-<n>`.

Status lives in Jira (project `VPAY`); intent and order live here.
