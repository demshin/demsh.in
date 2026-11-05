# GitHub Pages build and deployment

`Site build and deployment` builds standalone Jekyll from the frozen
`Gemfile.lock` on Ruby 3.3.13 with Bundler 2.6.5. There is one build and no
legacy Pages container, Docker requirement, or CSS hash exception list.

## Validation

The Python standard-library validator `.github/scripts/check_site.py` runs
against the generated directory, without network access. Its tests run before
the Jekyll build. `.github/scripts/site_contract.json` records the existing
published paths, post paths, domain, analytics ID, and existing redirect.
It contains no content or CSS hashes.

Validation requires:

- All previously published files, including posts, CV, listings, 404, styles,
  fonts, scripts, RSS, sitemap, robots.txt, and CNAME, remain present and nonempty.
- HTML pages have titles, descriptions, the correct canonical, stylesheet,
  RSS link, and analytics. Posts retain their title, body, date, and structured
  markup. Generated redirect pages instead require their target canonical and
  refresh instruction.
- Local links, fragment targets, HTML resources, and CSS `url()` resources
  resolve to generated files. Directory URLs such as `/about` are supported.
- RSS contains the latest ten posts (or all posts if fewer), without duplicate
  items, with titles, dates, GUIDs, and links matching generated post pages.
- The sitemap covers generated HTML pages except 404 and redirect aliases,
  without duplicate URLs or off-domain locations. Its links must resolve.
- The existing redirect remains, CNAME matches the domain, and robots.txt
  references the correct sitemap.
- No source maps, source/configuration files, hidden/private directories,
  symlinks, or empty files enter the published output.

New pages and assets are allowed. Normal text and CSS changes need no hash
updates. Removing an existing published path requires an explicit contract
change. Keep that change separate and review its URL/redirect impact.

These checks do not compare prose or appearance with an old Jekyll version,
fetch external links, or replace browser review of intentional design changes.
The Jekyll 4 migration's saved visual and byte-comparison evidence remains in
the local ignored `_migration_artifacts/` archive.

Run the same checks locally:

```bash
python3 -B -m unittest discover -s .github/scripts -p 'test_*.py' -v
JEKYLL_ENV=production bundle exec jekyll build --destination /tmp/demshin-site --trace
python3 .github/scripts/check_site.py /tmp/demshin-site --report /tmp/demshin-validation.json
```

## Publishing

The `build` job has only `contents: read`. After successful validation it
packages that exact directory with `actions/upload-pages-artifact`. The site,
build log, source SHA, UTC build time, validation report, and deployable Pages
artifact are retained for 30 days. The report includes every output file's
SHA-256 so the packaged and public files can be checked against it. Artifacts
from failed runs are diagnostic only.

Both the Pages packager and the evidence uploader use Node.js 24 actions.
Evidence uploads explicitly keep ZIP archiving (`archive: true`) so downloads
retain the existing directory layout; hidden files remain excluded.

The official Pages publisher bundles a dependency that imports Node's deprecated
`punycode` module. Its step sets `NODE_OPTIONS: --disable-warning=DEP0040` to
filter that specific upstream notice. Other warning codes and error exit
statuses remain unchanged; build and validation steps have no such filter.
Remove the workaround when a pinned upstream release removes that import.

The separate `deploy` job requires all of the following:

- The `build` job succeeded, including validation and artifact packaging.
- The run is for `refs/heads/master`.
- Repository variable `PAGES_DEPLOY_ENABLED` is exactly `true`.

Only this job receives `pages: write` and `id-token: write`. It uses the
`github-pages` environment and publishes the artifact from the same run.
Pull requests cannot deploy. An absent or false deployment variable disables
publishing without disabling validation. Runs on `master` are serialized;
new pushes do not cancel an in-progress deployment. `workflow_dispatch` on
`master` can republish the current source.

External actions remain pinned by SHA. The site URL and base path come from
`_config.yml`; Sass source maps remain disabled. Pages uses `build_type:
workflow`, custom domain `demsh.in`, and HTTPS enforcement. No DNS change is
needed. `.github/` scripts and instructions are excluded from Jekyll output.

## Sass maintenance

`css/main.scss` loads the site's modules with `@use`; shared variables and
the responsive mixin live in `_sass/_settings.scss`. Use `sass:math` for
division and `sass:color` for color adjustments. Retired Sass imports,
global built-ins, color functions, and slash division are fatal compilation
errors rather than silenced warnings.

The local `assets/css/style.scss` and `_sass/jekyll-theme-minimal.scss`
override the theme's Sass entry points. The latter copies theme 0.2.0 with
only its two imports changed to `@use`; fonts and highlighting modules still
come from the pinned gem. Its original CC0 license is adjacent. Revisit this
override when updating the theme and compare generated CSS and appearance.
The existing theme CSS, font, image, and script URLs remain available.

Local agent instructions, migration plans, todo notes, and progress logs are
excluded from the generated site. Jekyll does not inherit `.gitignore` rules;
keep the local-only paths listed in `_config.yml` as well.

## Rollback

Keep verified published-site archives, reports, and saved Pages settings in
the ignored `_migration_artifacts/` directory, outside GitHub's artifact
retention window. Revert a bad source/workflow change and run the workflow
on the restored source, then verify deployment and the public site.

The last verified publication with the temporary parity gate is
`5c55a70df4b116e411291321af3fef0e3935638d` (Jekyll 4.4.1). The last verified
Jekyll 3 publication was `76197fd3b7925604992f18ab665fee0df68138f6`.

To pause automatic publishing, set `PAGES_DEPLOY_ENABLED` to `false`. This
does not cancel an already running deployment; finish or explicitly cancel
that deployment before another publisher takes over. Reverting source or
workflow files does not restore Pages settings. Saved site archives are
content references, not an automatically deployable rollback job.
