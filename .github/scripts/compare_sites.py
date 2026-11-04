#!/usr/bin/env python3
"""Require byte-for-byte build parity, allowing only the validated CNAME file."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def files(directory):
    return {path.relative_to(directory): path for path in directory.rglob("*") if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
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
    changed = [
        str(name) for name in sorted(legacy.keys() & candidate.keys())
        if legacy[name].read_bytes() != candidate[name].read_bytes()
    ]
    errors.extend(f"Changed content: {name}" for name in changed)
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
    print(f"Legacy: {len(legacy)} files; candidate: {len(candidate)} files; changed: {len(changed)}")
    print("PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
