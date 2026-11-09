import tempfile
import unittest
from pathlib import Path

import confluence_sync as cs


def write(root: Path, path: str, text: str) -> None:
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def make_repos(tmp: Path) -> dict[str, Path]:
    platform, wallet = tmp / "platform", tmp / "wallet-service"
    write(platform, "VISION.md", "# Vision\n\nWhy.\n")
    write(platform, "ROADMAP.md", "# Roadmap\n\nSee the [vision](VISION.md) and [a heading](#phase-1).\n")
    write(platform, "docs/requirements.md",
          "# Reqs\n\n[ADR-3](adr/0003-money.md), [money](https://github.com/vivid-pay/wallet-service/blob/develop/"
          "docs/api-money.md), [template](adr/0000-template.md), [other](https://example.com/a?x=1&y=2).\n")
    write(platform, "docs/adr/README.md", "# ADR index\n\nIndex.\n")
    write(platform, "docs/adr/0000-template.md", "# ADR-NNNN: Title\n")
    write(platform, "docs/adr/0003-money.md", "# ADR-0003: Money\n\nUse minor units &rarr; always.\n")
    write(wallet, "docs/adr/0002-ledger.md",
          "# ADR-0002: Ledger\n\n```java\nlong x = 1; // a < b\n```\n\n```\nplain ]]> text\n```\n\n"
          "| a | b |\n|---|---|\n| 1 | 2 |\n")
    write(wallet, "docs/api-money.md", "# API money\n\nSee [ADR-3](../../platform/docs/adr/0003-money.md).\n")
    return {"platform": platform, "wallet-service": wallet}


class FakeClient:
    def __init__(self):
        self.pages: dict[str, dict] = {}
        self.calls: list[str] = []

    def find(self, label):
        self.calls.append("find")
        page = self.pages.get(label)
        return None if page is None else {"id": label, "version": page["version"], "message": page["message"]}

    def create(self, page):
        self.calls.append("create")
        assert page.label not in self.pages, "duplicate page created"
        self.pages[page.label] = {"version": 1, "message": cs.MESSAGE_PREFIX + page.digest, "body": page.body}

    def update(self, existing, page):
        self.calls.append("update")
        stored = self.pages[existing["id"]]
        stored.update(version=existing["version"] + 1, message=cs.MESSAGE_PREFIX + page.digest, body=page.body)


class CollectTests(unittest.TestCase):
    def test_collects_the_required_docs_and_skips_the_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = cs.collect(make_repos(Path(tmp)))
        paths = [(d.repo, d.path) for d in docs]
        self.assertIn(("platform", "VISION.md"), paths)
        self.assertIn(("platform", "ROADMAP.md"), paths)
        self.assertIn(("platform", "docs/requirements.md"), paths)
        self.assertIn(("platform", "docs/adr/0003-money.md"), paths)
        self.assertIn(("wallet-service", "docs/adr/0002-ledger.md"), paths)
        self.assertIn(("wallet-service", "docs/api-money.md"), paths)
        self.assertNotIn(("platform", "docs/adr/0000-template.md"), paths)

    def test_a_missing_required_doc_or_checkout_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = make_repos(Path(tmp))
            (roots["platform"] / "VISION.md").unlink()
            with self.assertRaises(cs.SyncError):
                cs.collect(roots)
            with self.assertRaises(cs.SyncError):
                cs.collect({"platform": Path(tmp) / "nope", "wallet-service": roots["wallet-service"]})

    def test_labels_come_from_the_path_so_a_renamed_title_keeps_its_page(self):
        doc = cs.Doc("wallet-service", "docs/adr/0002-ledger.md", Path("x"), cs.SECTION_ADR)
        self.assertEqual(doc.label, "src-wallet-service-docs-adr-0002-ledger-md")


class RenderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        pages = cs.render_docs(cs.collect(make_repos(Path(self._tmp.name))))
        self.pages = {p.title: p for p in pages}

    def test_every_page_starts_with_the_source_banner_and_link(self):
        for title, page in self.pages.items():
            self.assertTrue(page.body.startswith('<ac:structured-macro ac:name="info">'), title)
            self.assertIn("source of truth", page.body)
            self.assertIn("overwritten", page.body)
        ledger = self.pages["ADR-0002: Ledger"].body
        self.assertIn('href="https://github.com/vivid-pay/wallet-service/blob/develop/docs/adr/0002-ledger.md"',
                      ledger)

    def test_the_first_heading_becomes_the_title_not_the_body(self):
        self.assertNotIn("<h1>", self.pages["Vision"].body)
        self.assertIn("Why.", self.pages["Vision"].body)

    def test_links_between_published_docs_become_confluence_page_links(self):
        roadmap = self.pages["Roadmap"].body
        self.assertIn('<ri:page ri:content-title="Vision" />', roadmap)
        reqs = self.pages["Reqs"].body
        self.assertIn('ri:content-title="ADR-0003: Money"', reqs)
        self.assertIn('ri:content-title="API money"', reqs)  # absolute GitHub URL of a published doc
        self.assertIn('ri:content-title="ADR-0003: Money"', self.pages["API money"].body)  # cross-repo relative

    def test_links_to_unpublished_files_and_external_urls_stay_links(self):
        reqs = self.pages["Reqs"].body
        self.assertIn('href="https://github.com/vivid-pay/platform/blob/develop/docs/adr/0000-template.md"', reqs)
        self.assertIn('href="https://example.com/a?x=1&amp;y=2"', reqs)
        self.assertNotIn("#phase-1", self.pages["Roadmap"].body)

    def test_code_becomes_code_macros_and_cdata_is_safe(self):
        body = self.pages["ADR-0002: Ledger"].body
        self.assertIn('<ac:parameter ac:name="language">java</ac:parameter>', body)
        self.assertIn("long x = 1; // a < b", body)
        self.assertIn("plain ]]]]><![CDATA[> text", body)
        self.assertIn("<table>", body)

    def test_named_html_entities_become_numeric_so_the_xml_is_valid(self):
        body = self.pages["ADR-0003: Money"].body
        self.assertIn("&#8594;", body)
        self.assertNotIn("&rarr;", body)

    def test_the_index_links_every_doc_once_and_is_labelled(self):
        index = self.pages[cs.INDEX_TITLE]
        self.assertEqual(index.label, cs.INDEX_LABEL)
        for title in self.pages:
            if title != cs.INDEX_TITLE:
                self.assertEqual(index.body.count(f'ri:content-title="{title}"'), 1, title)
        self.assertNotIn("ADR-NNNN", index.body)

    def test_duplicate_titles_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = make_repos(Path(tmp))
            write(roots["platform"], "ROADMAP.md", "# Vision\n")
            with self.assertRaises(cs.SyncError):
                cs.render_docs(cs.collect(roots))

    def test_invalid_xml_is_caught_before_publishing(self):
        with self.assertRaises(cs.SyncError):
            cs.check_well_formed("<p>unclosed", "t")


class SyncTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.roots = make_repos(Path(self._tmp.name))
        self.client = FakeClient()

    def pages(self):
        return cs.render_docs(cs.collect(self.roots))

    def run_sync(self):
        return cs.sync(self.pages(), self.client, log=lambda _: None)

    def test_first_run_creates_every_page_and_a_rerun_changes_nothing(self):
        total = len(self.pages())
        self.assertEqual(self.run_sync(), {"created": total, "updated": 0, "unchanged": 0})
        self.client.calls.clear()
        self.assertEqual(self.run_sync(), {"created": 0, "updated": 0, "unchanged": total})
        self.assertNotIn("create", self.client.calls)
        self.assertNotIn("update", self.client.calls)
        self.assertEqual(len(self.client.pages), total)

    def test_a_changed_doc_updates_only_its_own_page_in_place(self):
        self.run_sync()
        write(self.roots["platform"], "VISION.md", "# Vision\n\nNew why.\n")
        counts = self.run_sync()
        self.assertEqual((counts["created"], counts["updated"]), (0, 1))
        self.assertEqual(self.client.pages["src-platform-vision-md"]["version"], 2)
        self.assertIn("New why.", self.client.pages["src-platform-vision-md"]["body"])

    def test_a_renamed_title_updates_the_same_page_without_a_duplicate(self):
        self.run_sync()
        before = len(self.client.pages)
        write(self.roots["platform"], "VISION.md", "# Vision and goals\n\nWhy.\n")
        counts = self.run_sync()
        # the renamed page, plus the roadmap and the index, which link to it by title
        self.assertEqual((counts["created"], counts["updated"]), (0, 3))
        self.assertEqual(len(self.client.pages), before)

    def test_a_page_edited_by_hand_is_overwritten(self):
        self.run_sync()
        self.client.pages["src-platform-vision-md"]["message"] = "someone edited this"
        self.assertEqual(self.run_sync()["updated"], 1)


class ConfigTests(unittest.TestCase):
    def test_only_atlassian_cloud_over_https_is_accepted(self):
        self.assertEqual(cs.validate_base_url("https://acme.atlassian.net/"), "https://acme.atlassian.net")
        for bad in ("http://acme.atlassian.net", "https://evil.example.com", "https://acme.atlassian.net.evil.com",
                    "https://acme.atlassian.net/wiki", "acme.atlassian.net", ""):
            with self.assertRaises(cs.SyncError, msg=bad):
                cs.validate_base_url(bad)

    def test_dry_run_publishes_nothing_and_needs_no_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = make_repos(Path(tmp))
            out = Path(tmp) / "out"
            code = cs.main(["--platform", str(roots["platform"]), "--wallet-service", str(roots["wallet-service"]),
                            "--dry-run", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue((out / "src-platform-vision-md.html").is_file())

    def test_publishing_without_credentials_fails_before_any_network_call(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            roots = make_repos(Path(tmp))
            saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("CONFLUENCE_")}
            try:
                code = cs.main(["--platform", str(roots["platform"]),
                                "--wallet-service", str(roots["wallet-service"])])
            finally:
                os.environ.update(saved)
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
