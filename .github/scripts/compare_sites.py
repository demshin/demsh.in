#!/usr/bin/env python3
"""Require build parity with narrowly reviewed Jekyll 4 compatibility changes."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def files(directory):
    return {path.relative_to(directory): path for path in directory.rglob("*") if path.is_file()}


class ListingHTML(HTMLParser):
    """Preserve content and significant whitespace while comparing listing markup."""

    protected_tags = {
        "pre", "code", "script", "style", "textarea", "svg", "math",
        "xmp", "listing", "plaintext", "iframe", "noembed", "noframes", "title",
    }

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tokens = []
        self.protected = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("start", self.get_starttag_text()))
        if tag in self.protected_tags:
            self.protected.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(("empty", self.get_starttag_text()))

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag))
        if self.protected and self.protected[-1] == tag:
            self.protected.pop()

    def handle_data(self, data):
        if not self.protected and data.isspace():
            data = re.sub(r"\n(?:[ \t]*\n)+", "\n", data)
        self.tokens.append(("data", data))

    def handle_entityref(self, name):
        self.tokens.append(("entity", name))

    def handle_charref(self, name):
        self.tokens.append(("char", name))

    def handle_comment(self, data):
        self.tokens.append(("comment", data))

    def handle_decl(self, decl):
        self.tokens.append(("declaration", decl))

    def unknown_decl(self, data):
        self.tokens.append(("unknown-declaration", data))

    def handle_pi(self, data):
        self.tokens.append(("instruction", data))


def listing_tokens(content):
    parser = ListingHTML()
    parser.feed(content.decode("utf-8"))
    parser.close()
    return parser.tokens


def accepted_change(name, legacy, candidate, policy):
    if name in {"index.html", "page2/index.html", "page3/index.html"}:
        if listing_tokens(legacy) == listing_tokens(candidate):
            return "Blank lines between listing elements"
    if name == "feed.xml":
        before = ("<generator>" + policy["legacy_generator"] + "</generator>").encode()
        after = ("<generator>" + policy["candidate_generator"] + "</generator>").encode()
        if legacy.count(before) == 1 and legacy.replace(before, after, 1) == candidate:
            return "Reviewed Jekyll generator version"
    reviewed = policy["reviewed_css"].get(name)
    if reviewed and hashlib.sha256(legacy).hexdigest() == reviewed["legacy_sha256"] and hashlib.sha256(candidate).hexdigest() == reviewed["candidate_sha256"]:
        return "Reviewed Dart Sass output (exact SHA-256 pair)"
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(Path(__file__).with_name("build_compatibility.json").read_text())
    legacy, candidate = files(args.legacy), files(args.candidate)
    errors = []
    required = {
        Path(name) for name in (
            "index.html", "about/index.html", "404.html", "css/main.css",
            "feed.xml", "sitemap.xml", "robots.txt", "redirects.json",
        )
    }
    for name in sorted(required - legacy.keys()):
        errors.append(f"Missing legacy reference: {name}")
    for name in sorted(legacy.keys() - candidate.keys()):
        errors.append(f"Missing candidate file: {name}")
    for name in sorted(candidate.keys() - legacy.keys()):
        if name != Path("CNAME") or candidate[name].read_text().strip() != "demsh.in":
            errors.append(f"Unexpected candidate file: {name}")
    changed = []
    accepted = {}
    unexpected = []
    for name in sorted(legacy.keys() & candidate.keys()):
        before, after = legacy[name].read_bytes(), candidate[name].read_bytes()
        if before == after:
            continue
        changed.append(str(name))
        reason = accepted_change(str(name), before, after, policy)
        if reason:
            accepted[str(name)] = reason
        else:
            unexpected.append(str(name))
            errors.append(f"Changed content: {name}")
    for name in ("feed.xml", "sitemap.xml"):
        if Path(name) in candidate:
            try:
                ET.parse(candidate[Path(name)])
            except ET.ParseError as error:
                errors.append(f"Invalid XML in {name}: {error}")
    if Path("index.html") in candidate:
        home = candidate[Path("index.html")].read_text()
        for expected in (
            'href="https://demsh.in/"', 'href="/css/main.css"',
            'gtag/js?id=G-XKK8ZMW7D2', "gtag('config', 'G-XKK8ZMW7D2')",
        ):
            if expected not in home:
                errors.append(f"Missing home page marker: {expected}")
    report = {
        "passed": not errors,
        "legacy_files": len(legacy),
        "candidate_files": len(candidate),
        "changed_files": changed,
        "accepted_changes": accepted,
        "unexpected_changes": unexpected,
        "errors": errors,
        "candidate_sha256": {
            str(name): hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sorted(candidate.items())
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"Legacy: {len(legacy)} files; candidate: {len(candidate)} files; changed: {len(changed)}; accepted: {len(accepted)}; unexpected: {len(unexpected)}")
    print("PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
