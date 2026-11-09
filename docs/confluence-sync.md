# Confluence mirror of the docs

The docs are written in the repositories and mirrored, one way, into a Confluence space so everything can be found
and read in one place. **The repository file is the source of truth.** Every Confluence page says so at the top and
links to its file; a page edited in Confluence is overwritten on the next sync. Change the repository file instead.
Confluence comments are fine as notes; act on them with a PR.

## What is published
| Section | Source |
|---|---|
| Product | `platform`: `VISION.md`, `ROADMAP.md`, `docs/requirements.md` |
| Architecture decisions | the ADR index (`docs/adr/README.md`) and every numbered ADR in `platform` and `wallet-service` (not the template) |
| API conventions | `wallet-service`: `docs/api-*.md` (money conventions, pagination, admin API, ...) |
| Docs index | a generated page linking all of the above |

Links between published docs become links between Confluence pages; links to anything else go to GitHub.
Publishing a new kind of doc means adding it in `collect()` in `scripts/confluence_sync.py`.

## How it works
`scripts/confluence_sync.py` (Python 3, one dependency: `markdown`, pinned in `scripts/requirements.txt`) converts each
file and calls the Confluence REST API.
- **No duplicates.** A page is found by a label derived from its source path (for example
  `src-platform-vision-md`), never by its title, so renaming a heading updates the same page.
- **Updates in place, only when changed.** The page version message carries a hash of the content; an unchanged page
  is skipped, so re-running creates no new versions.
- **Never deletes and never creates spaces.** If a source file is removed, delete its page by hand.
- Refuses any `CONFLUENCE_BASE_URL` that is not `https://<site>.atlassian.net`, so the token cannot be sent elsewhere.

## Run it
Dry run (no credentials, no network; renders and validates every page):
```bash
pip install -r scripts/requirements.txt
python scripts/confluence_sync.py --platform . --wallet-service ../wallet-service --dry-run --out /tmp/rendered
python -m unittest discover -s scripts      # the script's tests
```
Publish (the GitHub Action does this; locally only if you export the variables below yourself):
```bash
python scripts/confluence_sync.py --platform . --wallet-service ../wallet-service
```

## The GitHub Action
`.github/workflows/confluence-sync.yml` runs on a push to `develop` that touches docs or the script, daily (to pick up
`wallet-service` changes, which cannot trigger this repo), and on demand.
- **Off until the owner switches it on.** Automatic runs happen only when the repository variable
  `CONFLUENCE_SYNC_ENABLED` is `true`.
- **A manual run is a dry run by default.** Untick `dry_run` to publish. Publishing only works from `develop`.

### Credentials (names only; values live in GitHub, never in the repo)
| Name | Kind | What |
|---|---|---|
| `CONFLUENCE_API_TOKEN` | repository **secret** | Atlassian API token of the account below |
| `CONFLUENCE_EMAIL` | repository variable | the Atlassian account the token belongs to |
| `CONFLUENCE_BASE_URL` | repository variable | `https://<site>.atlassian.net` |
| `CONFLUENCE_SPACE_KEY` | repository variable | key of the existing space |
| `CONFLUENCE_SYNC_ENABLED` | repository variable | `true` to allow automatic runs |

An Atlassian API token acts as its owner across Atlassian Cloud, not just Confluence. Treat it as a password. If your
plan offers scoped tokens, give it only Confluence page read and write.

### First-time setup (owner)
1. Create the Confluence space (suggested name **Vivid Pay Docs**, key `VPAYDOCS`).
2. Create the API token at https://id.atlassian.com/manage-profile/security/api-tokens and add the secret and
   variables above to `vivid-pay/platform` (Settings, Secrets and variables, Actions). Do not set
   `CONFLUENCE_SYNC_ENABLED` yet.
3. Run the workflow manually with `dry_run` ticked and look at the `rendered-pages` artifact.
4. Run it once more with `dry_run` unticked: this is the first publish. Check the space.
5. Set `CONFLUENCE_SYNC_ENABLED` to `true`. Optionally set the "Docs index" page as the space home page.
