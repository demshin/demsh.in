#!/usr/bin/env python3
"""Validate the generated site without a second builder or network requests."""

import argparse
from datetime import datetime
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.ids = set()
        self.title = []
        self.heading = []
        self.body = []
        self.in_title = self.in_heading = False
        self.body_depth = 0
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "title":
            self.in_title = True
        if tag == "h1" and "post-title" in attrs.get("class", "").split():
            self.in_heading = True
        if tag == "div":
            if self.body_depth:
                self.body_depth += 1
            elif "post-content" in attrs.get("class", "").split():
                self.body_depth = 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "h1":
            self.in_heading = False
        if tag == "div" and self.body_depth:
            self.body_depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.in_heading:
            self.heading.append(data)
        if self.body_depth:
            self.body.append(data)

    def attributes(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


def page_url(name):
    return "/" + (name[:-10] if name == "index.html" or name.endswith("/index.html") else name)


def srcset_urls(value):
    """Extract URLs without splitting commas inside data URLs.

    Follow the URL/descriptor boundaries in the HTML srcset parsing algorithm:
    https://html.spec.whatwg.org/multipage/images.html#parse-a-srcset-attribute
    """
    while value:
        value = value.lstrip(" \t\n\r\f,")
        match = re.match(r"[^ \t\n\r\f]+", value)
        if not match:
            return
        url = match.group()
        value = value[match.end():]
        if not url.endswith(","):
            in_parens = False
            for index, char in enumerate(value):
                if char == "(":
                    in_parens = True
                elif char == ")":
                    in_parens = False
                elif char == "," and not in_parens:
                    value = value[index + 1:]
                    break
            else:
                value = ""
        yield url.rstrip(",")


def validate(directory, contract):
    errors = []
    entries = list(directory.rglob("*"))
    files = {p.relative_to(directory).as_posix(): p for p in entries if p.is_file() and not p.is_symlink()}
    for path in entries:
        if path.is_symlink():
            errors.append(f"Symlink in output: {path.relative_to(directory)}")
    for name in sorted(set(contract["required_files"]) - files.keys()):
        errors.append(f"Missing published path: {name}")
    for name, path in files.items():
        if any(part.startswith((".", "_")) for part in Path(name).parts) or path.suffix in {".map", ".scss", ".sass", ".py", ".rb", ".sh", ".yml", ".yaml", ".lock", ".key"} or name in {"Gemfile", "AGENTS.md", "CLAUDE.md"} or (path.suffix == ".md" and name != "README.md"):
            errors.append(f"Source or private file in output: {name}")
        if path.stat().st_size == 0:
            errors.append(f"Empty output file: {name}")
    origin = contract["site_url"]
    pages = {name: Page(path.read_text()) for name, path in files.items() if name.endswith(".html")}

    def check_link(value, source, fragment=False):
        url = urlsplit(urljoin(origin + page_url(source), value))
        if url.netloc != urlsplit(origin).netloc or url.scheme not in {"http", "https"}:
            return
        if url.scheme != "https":
            errors.append(f"Insecure internal URL in {source}: {value}")
        name = unquote(url.path).lstrip("/")
        if not name or name.endswith("/"):
            name += "index.html"
        elif name not in files and name + "/index.html" in files:
            name += "/index.html"
        if name not in files:
            errors.append(f"Broken internal URL in {source}: {value}")
        elif fragment and url.fragment and name in pages and unquote(url.fragment) not in pages[name].ids:
            errors.append(f"Missing fragment in {source}: {value}")

    redirects = {}
    try:
        redirects = json.loads(files["redirects.json"].read_text())
        if not isinstance(redirects, dict):
            raise ValueError("expected an object")
        for old, target in contract["redirects"].items():
            if redirects.get(old) != target:
                errors.append(f"Missing or changed redirect: {old}")
        for old, target in redirects.items():
            if not isinstance(target, str) or not old.startswith("/") or not target.startswith(origin + "/"):
                errors.append(f"Invalid redirect: {old} -> {target}")
                continue
            check_link(old, "redirects.json")
            check_link(target, "redirects.json")
    except (KeyError, ValueError, TypeError) as error:
        errors.append(f"Invalid redirects.json: {error}")
        redirects = {}

    post_urls = {}
    for name, page in pages.items():
        if page.attributes("base"):
            errors.append(f"Unexpected base URL: {name}")
        canonical = [a.get("href") for a in page.attributes("link") if "canonical" in a.get("rel", "").split()]
        url = origin + page_url(name)
        target = redirects.get(page_url(name), url)
        if canonical != [target]:
            errors.append(f"Incorrect canonical in {name}: {canonical}")
        if not "".join(page.title).strip():
            errors.append(f"Missing title: {name}")
        if target != url:
            refresh = [a.get("content", "") for a in page.attributes("meta") if a.get("http-equiv", "").lower() == "refresh"]
            if not any(re.fullmatch(r"0;\s*url=" + re.escape(target), value) for value in refresh):
                errors.append(f"Missing redirect refresh: {name}")
        else:
            if not any(a.get("href") == "/css/main.css" and "stylesheet" in a.get("rel", "").split() for a in page.attributes("link")):
                errors.append(f"Missing stylesheet: {name}")
            if not any(a.get("href") == origin + "/feed.xml" and a.get("type") == "application/rss+xml" for a in page.attributes("link")):
                errors.append(f"Missing RSS link: {name}")
            if not any(a.get("name") == "description" and a.get("content", "").strip() for a in page.attributes("meta")):
                errors.append(f"Missing description: {name}")
            text = files[name].read_text()
            analytics = contract["analytics_id"]
            if not any(a.get("src") == "https://www.googletagmanager.com/gtag/js?id=" + analytics for a in page.attributes("script")) or f"gtag('config', '{analytics}')" not in text:
                errors.append(f"Missing analytics: {name}")
        is_post = any(a.get("itemtype") == "https://schema.org/BlogPosting" for a in page.attributes("article"))
        if name in contract["posts"] and not is_post:
            errors.append(f"Missing post markup: {name}")
        if is_post:
            dates = [a.get("datetime", "") for a in page.attributes("time") if a.get("itemprop") == "datePublished"]
            try:
                date = datetime.fromisoformat(dates[0]) if len(dates) == 1 else None
                if date is None or date.utcoffset() is None:
                    raise ValueError("expected one date with timezone")
                post_urls[url] = {"title": "".join(page.heading).strip(), "date": date}
            except (ValueError, TypeError) as error:
                errors.append(f"Invalid post date in {name}: {error}")
            if not "".join(page.heading).strip() or not "".join(page.body).strip():
                errors.append(f"Empty post title or body: {name}")
        for tag, attrs in page.tags:
            for attr in ("href", "src", "poster"):
                if attrs.get(attr):
                    check_link(attrs[attr], name, fragment=tag == "a")
            for attr in ("srcset", "imagesrcset"):
                for value in srcset_urls(attrs.get(attr) or ""):
                    check_link(value, name)

    for name in (name for name in files if name.endswith(".css")):
        css = files[name].read_text()
        if not css.strip() or "{" not in css or "sourceMappingURL" in css or "{{" in css or "{%" in css:
            errors.append(f"Invalid CSS output: {name}")
        for match in re.finditer(r"url\(\s*['\"]?([^)'\"\s]+)", css):
            check_link(match.group(1), name)

    try:
        feed = ET.parse(files["feed.xml"]).getroot()
        channel = feed.find("channel")
        if feed.tag != "rss" or feed.get("version") != "2.0" or channel is None:
            raise ValueError("expected RSS 2.0 channel")
        if channel.findtext("link") != origin + "/" or not channel.findtext("title", "").strip() or not channel.findtext("description", "").strip():
            errors.append("Incorrect RSS channel metadata")
        self_link = channel.find("{http://www.w3.org/2005/Atom}link")
        if self_link is None or self_link.get("href") != origin + "/feed.xml" or self_link.get("rel") != "self":
            errors.append("Incorrect RSS self link")
        items = channel.findall("item")
        latest = sorted(post_urls, key=lambda url: post_urls[url]["date"], reverse=True)[:10]
        links = [item.findtext("link") for item in items]
        if len(links) != len(set(links)) or set(links) != set(latest) or not links:
            errors.append("RSS does not contain the latest posts exactly once")
        for item in items:
            url = item.findtext("link")
            check_link(url or "", "feed.xml")
            post = post_urls.get(url)
            if post is None or item.findtext("title", "").strip() != post["title"] or item.findtext("guid") != url or not item.findtext("description", "").strip() or parsedate_to_datetime(item.findtext("pubDate", "")) != post["date"]:
                errors.append(f"Incorrect RSS item: {url}")
    except (KeyError, ET.ParseError, ValueError, TypeError) as error:
        errors.append(f"Invalid RSS: {error}")

    try:
        sitemap = ET.parse(files["sitemap.xml"]).getroot()
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        if sitemap.tag != namespace + "urlset":
            raise ValueError("expected sitemap urlset")
        locations = [node.text or "" for node in sitemap.findall(namespace + "url/" + namespace + "loc")]
        expected = {origin + page_url(name) for name in pages if name != "404.html" and redirects.get(page_url(name), origin + page_url(name)) == origin + page_url(name)}
        if not expected.issubset(locations) or len(locations) != len(set(locations)):
            errors.append("Sitemap is missing pages or contains duplicate URLs")
        for url in locations:
            if not url.startswith(origin + "/"):
                errors.append(f"Unexpected sitemap URL: {url}")
            check_link(url, "sitemap.xml")
    except (KeyError, ET.ParseError, ValueError) as error:
        errors.append(f"Invalid sitemap: {error}")
    if "robots.txt" in files and f"Sitemap: {origin}/sitemap.xml" not in files["robots.txt"].read_text().splitlines():
        errors.append("Incorrect robots.txt sitemap")
    if "CNAME" in files and files["CNAME"].read_text().strip() != urlsplit(origin).hostname:
        errors.append("Incorrect CNAME")
    return {"passed": not errors, "files": len(files), "html_pages": len(pages), "posts": len(post_urls), "errors": errors,
            "candidate_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(files.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(Path(__file__).with_name("site_contract.json").read_text())
    report = validate(args.site, contract)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    for error in report["errors"]:
        print(error, file=sys.stderr)
    print(f"Files: {report['files']}; HTML: {report['html_pages']}; posts: {report['posts']}; errors: {len(report['errors'])}")
    print("PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
