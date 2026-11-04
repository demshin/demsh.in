# GitHub Pages build and deployment

`Site build and deployment` builds Jekyll 3.10.0 from the frozen `Gemfile.lock`
on Ruby 3.3.13 with Bundler 2.6.5. It compares the output with the previous
official Pages container, using the same source and build time. HTML, CSS,
feeds, redirects, and static assets must match byte for byte. The only allowed
extra file is `CNAME`, containing `demsh.in`.

Compressed CSS matches the previous built-in Pages output. Dependencies are
unchanged. External actions are pinned by SHA; the legacy container is pinned
by digest and runs without network access, a token, or writable source files.
These `.github/` instructions and scripts are excluded from Jekyll output.

## Publishing

The `compare` job has only `contents: read`. After successful comparison it
packages that exact candidate directory with `actions/upload-pages-artifact`.
Both builds, logs, source SHA, build time, comparison report, and the deployable
Pages artifact are retained for 30 days. Artifacts from failed runs are
diagnostic only.

The separate `deploy` job requires all of the following:

- The `compare` job succeeded, including artifact packaging.
- The run is for `refs/heads/master`.
- Repository variable `PAGES_DEPLOY_ENABLED` is exactly `true`.

Only this job receives `pages: write` and `id-token: write`. It uses the
`github-pages` environment and publishes the artifact from the same run.
Pull requests cannot deploy. An absent or false deployment variable disables
publishing without disabling validation. Runs on `master` are serialized;
new pushes do not cancel an in-progress deployment.

The site URL and base path come from `_config.yml`. The custom domain and
HTTPS settings remain in GitHub Pages settings; no DNS change is needed.

## Initial cutover

1. Keep `PAGES_DEPLOY_ENABLED` absent or false while reviewing and merging
   the workflow. Verify its PR and `master` checks; the deploy job must skip.
2. Save the live published site, its checksums, and the current Pages settings
   in `_migration_artifacts/` outside Git. Keep the successful CI artifacts
   outside GitHub's retention window as well.
3. Change only Pages `build_type` from `legacy` to `workflow`. Read it back
   and confirm `cname: demsh.in` and `https_enforced: true` are preserved.
4. Set `PAGES_DEPLOY_ENABLED` to `true` and manually run `site-check.yml` on
   `master`. Confirm comparison, packaging, and deployment all succeed.
5. Check HTTPS, all existing URLs and static assets, the existing redirect,
   CSS, the RSS feed, sitemap, and custom 404 behavior. RSS build dates may
   change; page and post content must remain unchanged.

Once enabled, pushes to `master` build, validate, and deploy automatically.
`workflow_dispatch` on `master` can republish the current source.

## Rollback

Keep the verified published-site archive and saved settings in the ignored
`_migration_artifacts/` directory. Changing or reverting the workflow does
not itself restore Pages settings.

For an immediate fallback while the Jekyll 3 source remains compatible:

1. Set `PAGES_DEPLOY_ENABLED` to `false`. Let any in-progress deployment finish
   or explicitly cancel it before restoring the previous publisher.
2. Restore Pages `build_type: legacy` and `source: {branch: master, path: /}`.
   Preserve the custom domain and HTTPS settings.
3. Request a legacy Pages build if one did not start automatically; wait for
   successful build and deployment, then verify the public site again.

The separately saved site archive is the content reference if rebuilding
ever becomes unsuitable. It is not an automatically deployable rollback job.

Dependency upgrades, replacing the temporary legacy parity gate, and the
Jekyll 4/Sass migration must be reviewed as separate changes after cutover.
