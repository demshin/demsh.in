"""Exercise publication failures and legitimate content/style changes."""

import json
from pathlib import Path
import tempfile
import unittest

from check_site import validate


class SiteValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.contract = {"site_url": "https://demsh.in", "analytics_id": "G-XKK8ZMW7D2", "posts": ["post.html"],
                         "redirects": {"/post.html": "https://demsh.in/post.html"}}
        for name, url in (("index.html", "/"), ("about/index.html", "/about/"), ("404.html", "/404.html"), ("post.html", "/post.html")):
            post = '<article itemtype="https://schema.org/BlogPosting"><h1 class="post-title">Post</h1><time itemprop="datePublished" datetime="2026-11-01T12:00:00+05:00"></time><div class="post-content">Body</div></article>' if name == "post.html" else "Page"
            self.write(name, f'''<!doctype html><html><head><title>Title</title><meta name="description" content="Description"><link rel="canonical" href="https://demsh.in{url}"><link rel="stylesheet" href="/css/main.css"><link type="application/rss+xml" href="https://demsh.in/feed.xml"></head><body><div id="cv">{post}</div><a href="/about#cv">CV</a><script src="https://www.googletagmanager.com/gtag/js?id=G-XKK8ZMW7D2"></script><script>gtag('config', 'G-XKK8ZMW7D2')</script></body></html>''')
        self.write("css/main.css", "body{color:#111}")
        self.write("CNAME", "demsh.in\n")
        self.write("robots.txt", "Sitemap: https://demsh.in/sitemap.xml\n")
        self.write("redirects.json", json.dumps(self.contract["redirects"]))
        self.write("feed.xml", '''<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Blog</title><description>Blog description</description><link>https://demsh.in/</link><atom:link rel="self" href="https://demsh.in/feed.xml"/><item><title>Post</title><description>Body</description><pubDate>Sun, 01 Nov 2026 12:00:00 +0500</pubDate><link>https://demsh.in/post.html</link><guid>https://demsh.in/post.html</guid></item></channel></rss>''')
        self.write("sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>https://demsh.in{p}</loc></url>" for p in ("/", "/about/", "/post.html")) + "</urlset>")
        self.contract["required_files"] = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def replace(self, name, before, after):
        path = self.root / name
        text = path.read_text()
        self.assertIn(before, text)
        self.write(name, text.replace(before, after))

    def check(self, passed, message=None):
        result = validate(self.root, self.contract)
        self.assertEqual(result["passed"], passed, result["errors"])
        if message:
            self.assertTrue(any(message in e for e in result["errors"]), result["errors"])
        return result

    def test_valid_site_and_extensionless_directory_links_pass(self):
        result = self.check(True)
        self.assertEqual(result["html_pages"], 4)
        self.assertEqual(result["posts"], 1)
        self.assertEqual(len(result["candidate_sha256"]), len(self.contract["required_files"]))

    def test_missing_or_empty_published_file_fails(self):
        for name in self.contract["required_files"]:
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.unlink()
                self.check(False, "Missing published path")
                path.write_bytes(b"")
                self.check(False, "Empty output file")
                path.write_bytes(original)

    def test_all_pages_require_metadata_and_analytics(self):
        for before, after in (("<title>Title</title>", ""), ('content="Description"', 'content=""'), ('href="https://demsh.in/about/"', 'href="https://other.example/"'), ('type="application/rss+xml"', 'type="text/plain"'), ('rel="stylesheet"', 'rel="other"'), ("G-XKK8ZMW7D2", "G-WRONG")):
            with self.subTest(before=before):
                original = (self.root / "about/index.html").read_text()
                self.replace("about/index.html", before, after)
                self.check(False)
                self.write("about/index.html", original)

    def test_broken_links_resources_fragments_and_base_fail(self):
        for markup in ('<a href="/missing/">link</a>', '<img src="/missing.png">', '<a href="/about#missing">link</a>', '<base href="https://other.example/">', '<a href="http://demsh.in/about/">link</a>'):
            with self.subTest(markup=markup):
                original = (self.root / "index.html").read_text()
                self.replace("index.html", "</body>", markup + "</body>")
                self.check(False)
                self.write("index.html", original)
        self.write("css/main.css", 'body{background:url("../missing.png")}')
        self.check(False, "Broken internal URL")

    def test_post_structure_content_and_date_failures(self):
        for before, after in (("https://schema.org/BlogPosting", "https://other.example"), (">Body</div>", "></div>"), (">Post</h1>", "></h1>"), ("2026-11-01T12:00:00+05:00", "invalid")):
            with self.subTest(before=before):
                original = (self.root / "post.html").read_text()
                self.replace("post.html", before, after)
                self.check(False)
                self.write("post.html", original)

    def test_rss_items_and_sitemap_coverage_are_validated(self):
        cases = (("feed.xml", "<title>Post</title>", "<title>Wrong</title>"), ("feed.xml", "Sun, 01 Nov 2026", "Mon, 02 Nov 2026"), ("feed.xml", "<guid>https://demsh.in/post.html</guid>", "<guid>https://demsh.in/wrong</guid>"), ("feed.xml", "<item>", "<item><unexpected>"), ("sitemap.xml", "<url><loc>https://demsh.in/post.html</loc></url>", ""), ("sitemap.xml", "https://demsh.in/about/", "https://other.example/about/"))
        for name, before, after in cases:
            with self.subTest(name=name, before=before):
                original = (self.root / name).read_text()
                self.replace(name, before, after)
                self.check(False)
                self.write(name, original)

    def test_domain_robots_and_redirect_contract_are_enforced(self):
        for name, bad in (("CNAME", "other.example"), ("robots.txt", "Sitemap: https://other.example/sitemap.xml"), ("redirects.json", "{}"), ("redirects.json", "[]"), ("redirects.json", '{"/post.html": 123}')):
            with self.subTest(name=name):
                original = (self.root / name).read_text()
                self.write(name, bad)
                self.check(False)
                self.write(name, original)

    def test_source_maps_private_files_and_symlinks_are_rejected(self):
        for name in ("css/main.css.map", ".git/config", "_drafts/post.html", "Gemfile", "Gemfile.lock", "AGENTS.md", "_config.yml", ".github/token"):
            with self.subTest(name=name):
                self.write(name, "private")
                self.check(False, "Source or private file")
                (self.root / name).unlink()
        (self.root / "linked.html").symlink_to(self.root / "index.html")
        self.check(False, "Symlink")

    def test_legitimate_text_and_css_changes_do_not_need_hash_updates(self):
        self.replace("post.html", ">Body</div>", ">Updated body</div>")
        self.replace("post.html", ">Post</h1>", ">Updated title</h1>")
        self.replace("feed.xml", "<title>Post</title>", "<title>Updated title</title>")
        self.write("css/main.css", "body{color:#222;margin:1rem}")
        self.check(True)

    def test_new_asset_is_allowed_but_checked_when_referenced(self):
        self.write("new.css", "body{color:#123}")
        self.replace("index.html", "</head>", '<link rel="stylesheet" href="/new.css"></head>')
        self.check(True)
        self.write("new.css", "body{background:url(/absent.png)}")
        self.check(False, "Broken internal URL")

    def test_srcset_resources_are_checked_without_splitting_data_urls(self):
        original = (self.root / "index.html").read_text()
        for tag in ("img", "source"):
            with self.subTest(tag=tag):
                self.write("index.html", original.replace("</body>", f'<{tag} srcset="data:image/png;base64,AAAA 1x, /missing.png 2x"></body>'))
                self.check(False, "Broken internal URL")
                self.write("index.html", original.replace("</body>", f'<{tag} srcset="data:image/png;base64,AAAA 1x, /css/main.css 2x"></body>'))
                self.check(True)

    def test_required_rss_version_and_description(self):
        original = (self.root / "feed.xml").read_text()
        for before, after in (('version="2.0"', ''), ('version="2.0"', 'version="1.0"'), ('<description>Blog description</description>', '')):
            with self.subTest(before=before, after=after):
                self.write("feed.xml", original)
                self.replace("feed.xml", before, after)
                self.check(False)
                self.write("feed.xml", original)

    def test_only_an_index_basename_maps_to_a_directory_url(self):
        self.write("myindex.html", (self.root / "index.html").read_text().replace('href="https://demsh.in/"', 'href="https://demsh.in/myindex.html"'))
        self.replace("sitemap.xml", "</urlset>", "<url><loc>https://demsh.in/myindex.html</loc></url></urlset>")
        self.check(True)


if __name__ == "__main__":
    unittest.main()
