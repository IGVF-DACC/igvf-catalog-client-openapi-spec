#!/usr/bin/env bash
# Regenerate one client in place: wipe the files the generator wrote last time,
# run openapi-generator with the pinned version, reorder the README endpoint
# table and copy the specs in. Used by generate-clients.yml and for local runs.
#
#   scripts/generate_client.sh <python|python-async|r> <client_dir> <spec_dir> <version>
#
# <spec_dir> holds openapi_spec.json and openapi_spec_processed.json.
set -euo pipefail

if [ $# -ne 4 ]; then
  sed -n '2,8p' "$0" >&2
  exit 2
fi

name=$1
client_dir=$(cd "$2" && pwd)
spec_dir=$(cd "$3" && pwd)
version=$4
tools_dir=$(cd "$(dirname "$0")/.." && pwd)

case "$name" in
  python)       generator=python; tag=IgvfCatalog;      repo=igvf-catalog-python-client ;;
  python-async) generator=python; tag=AsyncIgvfCatalog; repo=igvf-catalog-async-python-client ;;
  r)            generator=r;      tag=IgvfCatalog;      repo=igvf-catalog-r-client ;;
  *) echo "unknown client '$name'" >&2; exit 2 ;;
esac

if command -v openapi-generator-cli > /dev/null; then
  generator_cli=(openapi-generator-cli)
else
  generator_cli=(npx --yes @openapitools/openapi-generator-cli@2.41.0)
fi

cd "$client_dir"

# Files listed in FILES were written by the previous run; files the
# .openapi-generator-ignore protects are never listed.
if [ -f .openapi-generator/FILES ]; then
  grep -vE '^/|(^|/)\.\.(/|$)' .openapi-generator/FILES | xargs -r -d '\n' rm -f --
fi

cp "$tools_dir/openapitools.json" .
templates=()
if [ -d templates ]; then templates=(-t templates); fi

"${generator_cli[@]}" generate \
  -i "$spec_dir/openapi_spec_processed.json" \
  -g "$generator" \
  -c "$tools_dir/config/$name.yaml" \
  "${templates[@]}" \
  -o . \
  --additional-properties "packageVersion=$version" \
  --openapi-normalizer "SET_TAGS_FOR_ALL_OPERATIONS=$tag" \
  --git-host github.com --git-user-id IGVF-DACC --git-repo-id "$repo"

python3 "$tools_dir/scripts/reorder_readme.py" --readme README.md --ordering "$tools_dir/ordering.txt"
cp "$spec_dir/openapi_spec.json" "$spec_dir/openapi_spec_processed.json" .
