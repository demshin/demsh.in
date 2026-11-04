#!/usr/bin/env bash
set -euo pipefail

# This is the exact image digest recorded by the successful e0af807 Pages build.
image=ghcr.io/actions/jekyll-build-pages@sha256:6791ebfd912185ed59bfb5fb102664fa872496b79f87ff8b9cfba292a7345041
source_dir=$(cd "$1" && pwd)
mkdir -p "$2"
destination_dir=$(cd "$2" && pwd)

# The old dependency set is only a migration reference. Give it no network or token.
docker run --rm --network none --platform linux/amd64 \
  --volume "$source_dir:/github/workspace:ro" \
  --volume "$destination_dir:/github/site-legacy" \
  --env GITHUB_WORKSPACE=/github/workspace \
  --env GITHUB_REPOSITORY=demshin/demsh.in \
  --env GITHUB_API_URL=https://api.github.com \
  --env INPUT_SOURCE=. \
  --env INPUT_DESTINATION=../site-legacy \
  --env "INPUT_BUILD_REVISION=$(git rev-parse HEAD)" \
  "$image"
