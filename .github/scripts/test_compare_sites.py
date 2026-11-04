"""Regression tests for the build comparison's accepted and rejected changes."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class BuildComparisonTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.legacy = self.root / 'legacy'
        self.candidate = self.root / 'candidate'
        self.tool = self.root / 'compare_sites.py'
        shutil.copyfile(Path(__file__).with_name('compare_sites.py'), self.tool)
        self.old_css = b'body{color:#111}\n'
        self.new_css = b'body{color:rgb(17,17,17)}\n'
        policy = {'legacy_generator': 'Jekyll v3.10.0', 'candidate_generator': 'Jekyll v4.4.1', 'reviewed_css': {
            'css/main.css': {'legacy_sha256': hashlib.sha256(self.old_css).hexdigest(), 'candidate_sha256': hashlib.sha256(self.new_css).hexdigest()}}}
        self.tool.with_name('build_compatibility.json').write_text(json.dumps(policy))
        self.home = b'''<!doctype html><html><head><link rel="canonical" href="https://demsh.in/"><link href="/css/main.css"><script src="https://www.googletagmanager.com/gtag/js?id=G-XKK8ZMW7D2"></script><script>gtag('config', 'G-XKK8ZMW7D2');</script></head><body><p><p>Intro</p>\n\n</p><a href="/about/">CV</a></body></html>'''
        files = {'index.html': self.home, 'about/index.html': b'<p>CV</p>', '404.html': b'<p>Not found</p>', 'css/main.css': self.old_css,
                 'feed.xml': b'<rss><channel><generator>Jekyll v3.10.0</generator><item><title>Post</title><link>https://demsh.in/post</link></item></channel></rss>',
                 'sitemap.xml': b'<urlset><url><loc>https://demsh.in/</loc></url></urlset>', 'robots.txt': b'Sitemap: https://demsh.in/sitemap.xml\n', 'redirects.json': b'{"old":"/new"}'}
        for name, content in files.items():
            for directory in (self.legacy, self.candidate):
                target = directory / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        (self.candidate / 'CNAME').write_text('demsh.in\n')

    def run_comparison(self, expected):
        report = self.root / 'report.json'
        result = subprocess.run([sys.executable, '-B', str(self.tool), str(self.legacy), str(self.candidate), '--report', str(report)], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        data = json.loads(report.read_text())
        self.assertEqual(data['passed'], expected == 0)
        return data

    def test_identical_builds_and_valid_domain_pass(self):
        self.run_comparison(0)

    def test_observed_jekyll4_serialization_changes_pass(self):
        (self.candidate / 'index.html').write_bytes(self.home.replace(b'\n\n', b'\n'))
        feed = self.candidate / 'feed.xml'
        feed.write_bytes(feed.read_bytes().replace(b'Jekyll v3.10.0', b'Jekyll v4.4.1'))
        (self.candidate / 'css/main.css').write_bytes(self.new_css)
        data = self.run_comparison(0)
        self.assertEqual(set(data['accepted_changes']), {'index.html', 'feed.xml', 'css/main.css'})

    def test_text_and_url_changes_fail(self):
        for old, new in ((b'Intro', b'Altered'), (b'/about/', b'/wrong/')):
            with self.subTest(new=new):
                (self.candidate / 'index.html').write_bytes(self.home.replace(old, new))
                self.run_comparison(1)

    def test_significant_whitespace_is_preserved(self):
        for markup in (b'<pre><code>a\n\nb</code></pre>', b'<script>const x = `a\n\nb`;</script>', b'<style>/* a\n\nb */</style>', b'<textarea>a\n\nb</textarea>', b'<p>a\n\nb</p>', b'<a>a</a>\n<a>b</a>'):
            with self.subTest(markup=markup):
                original = self.home.replace(b'Intro', markup)
                (self.legacy / 'index.html').write_bytes(original)
                (self.candidate / 'index.html').write_bytes(original.replace(b'\n\n', b'\n') if b'\n\n' in markup else original.replace(b'</a>\n<a>', b'</a><a>'))
                self.run_comparison(1)

    def test_whitespace_exception_is_not_applied_to_posts(self):
        name = 'post.html'
        (self.legacy / name).write_bytes(b'<p>a</p>\n\n<p>b</p>')
        (self.candidate / name).write_bytes(b'<p>a</p>\n<p>b</p>')
        self.run_comparison(1)

    def test_svg_cdata_and_raw_text_are_preserved(self):
        for before, after in (
            (b'<svg><text><![CDATA[Original]]></text></svg>', b'<svg><text><![CDATA[Altered]]></text></svg>'),
            (b'<svg><text><![CDATA[\n\n]]></text></svg>', b'<svg><text><![CDATA[\n]]></text></svg>'),
            (b'<xmp>\n\n</xmp>', b'<xmp>\n</xmp>'),
        ):
            with self.subTest(before=before):
                (self.legacy / 'index.html').write_bytes(self.home.replace(b'Intro', before))
                (self.candidate / 'index.html').write_bytes(self.home.replace(b'Intro', after))
                self.run_comparison(1)

    def test_unknown_css_and_unreviewed_source_fail(self):
        (self.candidate / 'css/main.css').write_bytes(self.new_css + b'body{width:1px}')
        self.run_comparison(1)
        (self.candidate / 'css/main.css').write_bytes(self.new_css)
        (self.legacy / 'css/main.css').write_bytes(self.old_css + b'body{width:2px}')
        self.run_comparison(1)

    def test_feed_version_does_not_hide_content_changes(self):
        feed = self.candidate / 'feed.xml'
        feed.write_bytes(feed.read_bytes().replace(b'Jekyll v3.10.0', b'Jekyll v4.4.1').replace(b'/post', b'/wrong'))
        self.run_comparison(1)

    def test_missing_page_extra_map_wrong_domain_and_invalid_xml_fail(self):
        page = self.candidate / 'about/index.html'
        content = page.read_bytes()
        page.unlink()
        self.run_comparison(1)
        page.write_bytes(content)
        extra = self.candidate / 'css/main.css.map'
        extra.write_text('{}')
        self.run_comparison(1)
        extra.unlink()
        (self.candidate / 'CNAME').write_text('example.com')
        self.run_comparison(1)
        (self.candidate / 'CNAME').write_text('demsh.in')
        (self.candidate / 'feed.xml').write_text('<rss>')
        self.run_comparison(1)


if __name__ == '__main__':
    unittest.main()
