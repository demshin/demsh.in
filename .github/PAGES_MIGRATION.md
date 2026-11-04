# GitHub Pages migration checks

`Site build validation` builds each PR with Jekyll 3.10.0 from `Gemfile.lock`
on Ruby 3.3.13 and compares it with the previous GitHub Pages container.
Both builds use the same source and build time. HTML, CSS, feeds, redirects,
and static assets must match byte for byte. The only allowed extra file is
`CNAME`, containing `demsh.in`.

The CSS output style is explicitly compressed to match the built-in Pages
builder. Dependency versions are unchanged. Actions are pinned by commit SHA;
the legacy container is pinned by digest and runs without network access.

This workflow has read-only repository permissions and does not deploy or
change Pages settings. The live site continues to use the built-in builder
from `master:/`. Each run retains both generated sites, logs, source SHA,
build time, and a comparison report for 30 days. Artifacts from failed runs
are diagnostic only; use a successful, reviewed run for rollback.

The local `_migration_artifacts/` directory is excluded from Git. Keep the
verified published-site backup and Pages settings there for the cutover.
The `.github/` directory is excluded from Jekyll output by default, so these
checks and instructions do not become additional public pages.

Before switching Pages to a custom deployment workflow:

1. Require a successful comparison and inspect the candidate site.
2. Save the successful legacy artifact and current Pages settings outside
   the artifact retention window.
3. Add a separate deployment job restricted to `master`, after validation.
4. Switch the publishing source to GitHub Actions and verify HTTPS, critical
   pages, the existing redirect, CSS, RSS, and sitemap.
5. If verification fails, redeploy the saved legacy site. Restoring branch
   publishing from `master:/` is the fallback while Jekyll 3 is retained.

Upgrade dependencies only after the publishing migration is verified.
Jekyll 4 and its Sass compiler migration are a separate change.
