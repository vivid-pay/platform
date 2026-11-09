#!/usr/bin/env python3
"""Mirror the Vivid Pay docs from the repositories to a Confluence space (one-way, repo -> Confluence).

The repository files stay the source of truth. Every page is generated from a markdown file and says so at the
top. Re-running updates existing pages in place: a page is found by a label derived from the source path, never
by its title, and is only rewritten when its content changed. Nothing is deleted.

Usage:
    confluence_sync.py --platform PATH --wallet-service PATH --dry-run [--out DIR]
    confluence_sync.py --platform PATH --wallet-service PATH            # publishes

Environment (publishing only; values are never stored in the repository):
    CONFLUENCE_BASE_URL    e.g. https://example.atlassian.net
    CONFLUENCE_EMAIL       the Atlassian account the token belongs to
    CONFLUENCE_API_TOKEN   an Atlassian API token (a repository secret)
    CONFLUENCE_SPACE_KEY   the key of an existing space; the script never creates spaces
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import html.entities
import json
import os
import posixpath
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import markdown

GITHUB_ORG = "vivid-pay"
GITHUB_BRANCH = "develop"
REPOS = ("platform", "wallet-service")
INDEX_TITLE = "Docs index"
INDEX_LABEL = "src-generated-index"
MESSAGE_PREFIX = "docs-sync sha256:"

SECTION_PRODUCT = "Product"
SECTION_ADR = "Architecture decisions"
SECTION_API = "API conventions"
SECTIONS = (SECTION_PRODUCT, SECTION_ADR, SECTION_API)

CODE_LANGUAGES = {"java": "java", "sql": "sql", "bash": "bash", "sh": "bash", "json": "json", "yaml": "yaml",
                  "yml": "yaml", "xml": "xml", "python": "python", "javascript": "js", "js": "js"}
XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}


class SyncError(Exception):
    """A problem the operator has to fix (bad configuration, duplicate titles, API refusal)."""


@dataclass(frozen=True)
class Doc:
    repo: str
    path: str  # posix path inside the repo
    file: Path
    section: str

    @property
    def key(self) -> tuple[str, str]:
        return self.repo, self.path

    @property
    def label(self) -> str:
        return "src-" + re.sub(r"[^a-z0-9]+", "-", f"{self.repo}-{self.path}".lower()).strip("-")

    @property
    def github_url(self) -> str:
        return github_url(self.repo, self.path)


@dataclass(frozen=True)
class Page:
    doc: Doc | None  # None for the generated index
    title: str
    label: str
    body: str

    @property
    def digest(self) -> str:
        return hashlib.sha256(f"{self.title}\n{self.body}".encode()).hexdigest()


def github_url(repo: str, path: str) -> str:
    return f"https://github.com/{GITHUB_ORG}/{repo}/blob/{GITHUB_BRANCH}/{path}"


# ---------------------------------------------------------------- collecting

def collect(roots: dict[str, Path]) -> list[Doc]:
    """The docs that are published, in a stable order. A missing repo checkout is an error, not a skip."""
    docs: list[Doc] = []

    def add(repo: str, path: str, section: str) -> None:
        file = roots[repo] / path
        if not file.is_file():
            raise SyncError(f"Expected doc not found: {repo}/{path}")
        docs.append(Doc(repo, path, file, section))

    for repo in REPOS:
        if not roots[repo].is_dir():
            raise SyncError(f"Checkout of {repo} not found at {roots[repo]}")
    for path in ("VISION.md", "ROADMAP.md", "docs/requirements.md"):
        add("platform", path, SECTION_PRODUCT)
    add("platform", "docs/adr/README.md", SECTION_ADR)
    for repo in REPOS:
        adr_dir = roots[repo] / "docs" / "adr"
        for file in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")) if adr_dir.is_dir() else []:
            if not file.name.startswith("0000-"):  # the template is not a decision
                add(repo, f"docs/adr/{file.name}", SECTION_ADR)
    api_dir = roots["wallet-service"] / "docs"
    for file in sorted(api_dir.glob("api-*.md")):
        add("wallet-service", f"docs/{file.name}", SECTION_API)
    return docs


def split_title(text: str, fallback: str) -> tuple[str, str]:
    """Returns (title, body without its first H1). The page title replaces the heading."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), "\n".join(lines[:i] + lines[i + 1:])
    return fallback, text


# ----------------------------------------------------------------- rendering

def _numeric_entities(rendered: str) -> str:
    """Confluence storage is XML: named HTML entities such as &rarr; are not valid there."""
    def fix(match: re.Match) -> str:
        name = match.group(1)
        if name in XML_ENTITIES:
            return match.group(0)
        codepoint = html.entities.name2codepoint.get(name)
        return f"&#{codepoint};" if codepoint else match.group(0)
    return re.sub(r"&([A-Za-z][A-Za-z0-9]*);", fix, rendered)


def _cdata(text: str) -> str:
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _code_macros(rendered: str) -> str:
    def macro(match: re.Match) -> str:
        language = CODE_LANGUAGES.get((match.group(1) or "").lower())
        param = f'<ac:parameter ac:name="language">{language}</ac:parameter>' if language else ""
        return ('<ac:structured-macro ac:name="code">' + param + "<ac:plain-text-body>"
                + _cdata(html.unescape(match.group(2))) + "</ac:plain-text-body></ac:structured-macro>")
    return re.sub(r'<pre><code(?: class="language-([^"]*)")?>(.*?)</code></pre>', macro, rendered, flags=re.S)


def page_link(title: str, text: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]+>", "", text))
    return (f'<ac:link><ri:page ri:content-title="{html.escape(title, quote=True)}" />'
            f"<ac:plain-text-link-body>{_cdata(plain)}</ac:plain-text-link-body></ac:link>")


def _resolve_target(doc: Doc, href: str) -> tuple[tuple[str, str] | None, str]:
    """Maps a link to a (repo, path) inside the published set if it points at a repo file, else None.
    The second value is the absolute GitHub URL to fall back to."""
    href = html.unescape(href)
    absolute = re.match(rf"https://github\.com/{GITHUB_ORG}/([\w.-]+)/blob/(?:develop|main)/([^#?]+)", href)
    if absolute:
        return (absolute.group(1), absolute.group(2)), href
    if re.match(r"[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith("#"):
        return None, href
    target = posixpath.normpath(posixpath.join(posixpath.dirname(doc.path), href.split("#")[0].split("?")[0]))
    for repo in REPOS:
        if target.startswith(f"../{repo}/"):
            repo_path = target[len(f"../{repo}/"):]
            return (repo, repo_path), github_url(repo, repo_path)
    if target.startswith(".."):
        return None, href
    return (doc.repo, target), github_url(doc.repo, target)


def _rewrite_links(rendered: str, doc: Doc, titles: dict[tuple[str, str], str]) -> str:
    def rewrite(match: re.Match) -> str:
        href, text = match.group(1), match.group(2)
        if href.startswith("#"):
            return text  # in-page anchors do not survive the conversion
        key, fallback = _resolve_target(doc, href)
        if key in titles:
            return page_link(titles[key], text)
        return f'<a href="{html.escape(fallback, quote=False).replace(chr(34), "&quot;")}">{text}</a>'
    return re.sub(r'<a href="([^"]*)">(.*?)</a>', rewrite, rendered, flags=re.S)


def banner(source_label: str, url: str | None) -> str:
    if url:
        source = f'the repository file <a href="{html.escape(url)}">{html.escape(source_label)}</a>'
    else:
        source = html.escape(source_label)
    return ('<ac:structured-macro ac:name="info"><ac:rich-text-body><p>'
            f"<strong>The source of truth is {source}.</strong> "
            "This page is generated from it. Edits made here are overwritten on the next sync; change the "
            "repository file instead.</p></ac:rich-text-body></ac:structured-macro>")


def check_well_formed(body: str, title: str) -> None:
    try:
        ET.fromstring(f'<root xmlns:ac="urn:ac" xmlns:ri="urn:ri">{body}</root>')
    except ET.ParseError as e:
        raise SyncError(f"Generated page '{title}' is not valid Confluence storage XML: {e}") from e


def render_docs(docs: list[Doc]) -> list[Page]:
    parsed = {}
    for doc in docs:
        title, text = split_title(doc.file.read_text(encoding="utf-8"), doc.file.stem)
        parsed[doc.key] = (title, text)
    titles = {key: title for key, (title, _) in parsed.items()}
    seen: dict[str, tuple[str, str]] = {}
    for key, title in [*titles.items(), (("generated", "index"), INDEX_TITLE)]:
        if title in seen:
            raise SyncError(f"Two docs would get the page title '{title}': {seen[title]} and {key}")
        seen[title] = key

    pages = []
    for doc in docs:
        title, text = parsed[doc.key]
        rendered = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"],
                                     output_format="xhtml")
        rendered = _code_macros(_numeric_entities(rendered))
        body = banner(f"{doc.repo}/{doc.path}", doc.github_url) + _rewrite_links(rendered, doc, titles)
        check_well_formed(body, title)
        pages.append(Page(doc, title, doc.label, body))
    pages.append(render_index(docs, titles))
    return pages


def render_index(docs: list[Doc], titles: dict[tuple[str, str], str]) -> Page:
    parts = [banner("generated by the docs sync in the platform repository (scripts/confluence_sync.py)", None),
             "<p>Every page in this space is a copy of a file in the "
             f'<a href="https://github.com/{GITHUB_ORG}/platform">platform</a> or '
             f'<a href="https://github.com/{GITHUB_ORG}/wallet-service">wallet-service</a> repository.</p>']
    for section in SECTIONS:
        items = "".join(f"<li>{page_link(titles[d.key], titles[d.key])}</li>" for d in docs if d.section == section)
        parts.append(f"<h2>{html.escape(section)}</h2><ul>{items}</ul>")
    body = "".join(parts)
    check_well_formed(body, INDEX_TITLE)
    return Page(None, INDEX_TITLE, INDEX_LABEL, body)


# ----------------------------------------------------------------- Confluence

def validate_base_url(url: str) -> str:
    """Only an Atlassian Cloud site over https: the API token must not be sendable to anywhere else."""
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".atlassian.net") or parsed.path not in ("", "/"):
        raise SyncError("CONFLUENCE_BASE_URL must look like https://<site>.atlassian.net")
    return f"https://{parsed.hostname}"


class ConfluenceClient:
    def __init__(self, base_url: str, email: str, token: str, space_key: str):
        self.base = validate_base_url(base_url) + "/wiki/rest/api"
        self.space_key = space_key
        self._auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": self._auth, "Accept": "application/json", "Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read() or b"{}")
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503) and attempt < 2:
                    time.sleep(2 ** attempt * 2)
                    continue
                detail = e.read().decode(errors="replace")[:500]
                raise SyncError(f"Confluence {method} {path.split('?')[0]} failed: HTTP {e.code} {detail}") from e
            except urllib.error.URLError as e:
                raise SyncError(f"Confluence {method} {path.split('?')[0]} failed: {e.reason}") from e
        raise SyncError("unreachable")

    def check_space(self) -> None:
        self._request("GET", f"/space/{urllib.parse.quote(self.space_key)}")

    def find(self, label: str) -> dict | None:
        cql = f'space = "{self.space_key}" AND type = page AND label = "{label}"'
        found = self._request("GET", "/content/search?limit=5&expand=version&cql=" + urllib.parse.quote(cql))
        results = found.get("results", [])
        if len(results) > 1:
            raise SyncError(f"{len(results)} pages carry the label {label}; remove the extra ones by hand")
        if not results:
            return None
        page = results[0]
        return {"id": page["id"], "version": page["version"]["number"], "message": page["version"].get("message", "")}

    def create(self, page: Page) -> None:
        self._request("POST", "/content", {
            "type": "page", "title": page.title, "space": {"key": self.space_key},
            "body": {"storage": {"value": page.body, "representation": "storage"}},
            "metadata": {"labels": [{"prefix": "global", "name": page.label}]},
            "version": {"message": MESSAGE_PREFIX + page.digest}})

    def update(self, existing: dict, page: Page) -> None:
        self._request("PUT", f"/content/{existing['id']}", {
            "type": "page", "title": page.title,
            "body": {"storage": {"value": page.body, "representation": "storage"}},
            "version": {"number": existing["version"] + 1, "message": MESSAGE_PREFIX + page.digest}})


def sync(pages: list[Page], client, log=print) -> dict[str, int]:
    """Creates missing pages, rewrites changed ones, leaves identical ones alone."""
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for page in pages:
        existing = client.find(page.label)
        if existing is None:
            client.create(page)
            counts["created"] += 1
            log(f"created    {page.title}")
        elif existing["message"] == MESSAGE_PREFIX + page.digest:
            counts["unchanged"] += 1
            log(f"unchanged  {page.title}")
        else:
            client.update(existing, page)
            counts["updated"] += 1
            log(f"updated    {page.title}")
    return counts


# ------------------------------------------------------------------------ CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", type=Path, required=True, help="checkout of the platform repo")
    parser.add_argument("--wallet-service", type=Path, required=True, help="checkout of the wallet-service repo")
    parser.add_argument("--dry-run", action="store_true", help="render and validate only; no network access")
    parser.add_argument("--out", type=Path, help="with --dry-run: write each rendered page here for inspection")
    args = parser.parse_args(argv)
    try:
        pages = render_docs(collect({"platform": args.platform, "wallet-service": args.wallet_service}))
        if args.dry_run:
            for page in pages:
                print(f"would publish  {page.title}  [{page.label}]")
                if args.out:
                    args.out.mkdir(parents=True, exist_ok=True)
                    (args.out / f"{page.label}.html").write_text(page.body, encoding="utf-8")
            print(f"{len(pages)} pages rendered and validated; nothing was published.")
            return 0
        missing = [v for v in ("CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN",
                               "CONFLUENCE_SPACE_KEY") if not os.environ.get(v)]
        if missing:
            raise SyncError("Missing environment variables: " + ", ".join(missing))
        client = ConfluenceClient(os.environ["CONFLUENCE_BASE_URL"], os.environ["CONFLUENCE_EMAIL"],
                                  os.environ["CONFLUENCE_API_TOKEN"], os.environ["CONFLUENCE_SPACE_KEY"])
        client.check_space()
        counts = sync(pages, client)
        print(f"done: {counts['created']} created, {counts['updated']} updated, {counts['unchanged']} unchanged")
        return 0
    except SyncError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
