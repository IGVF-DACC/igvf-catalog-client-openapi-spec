# igvf-catalog-client-openapi-spec

The OpenAPI spec of the [IGVF Catalog API](https://api.catalogkg.igvf.org/) and the GitHub Actions pipeline that generates its clients from it:

| Client | Repo | Install |
|---|---|---|
| Python | [igvf-catalog-python-client](https://github.com/IGVF-DACC/igvf-catalog-python-client) | `pip install igvf-catalog-client` |
| Python (asyncio) | [igvf-catalog-async-python-client](https://github.com/IGVF-DACC/igvf-catalog-async-python-client) | `pip install igvf-catalog-async-client` |
| R | [igvf-catalog-r-client](https://github.com/IGVF-DACC/igvf-catalog-r-client) | `remotes::install_github("IGVF-DACC/igvf-catalog-r-client@vX.Y.Z")` |
| MCP server | [igvf-catalog-mcp](https://github.com/IGVF-DACC/igvf-catalog-mcp) | `pip install igvf-catalog-mcp` |

## How it works

[`igvf-catalog`](https://github.com/IGVF-DACC/igvf-catalog) sends a `repository_dispatch` to this repo (its `.github/workflows/trigger-clients.yml`), which runs [`generate-clients.yml`](.github/workflows/generate-clients.yml):

| | Dev channel | Release channel |
|---|---|---|
| Trigger | push to `igvf-catalog@dev` (`catalog-dev`) | published, non-prerelease `igvf-catalog` release (`catalog-release`) |
| Spec server | `https://catalog-api-dev.demo.igvf.org/api` | `https://api.catalogkg.igvf.org/api` |
| Version | Python `X.Y.(Z+1).devYYYYMMDDHHMMSS`, R `X.Y.Z.9000`, where `X.Y.Z` is the latest igvf-catalog release | the release tag, normalized (`v1.3` → `1.3.0`) |
| Branch in every downstream repo | `dev` | `main` + GitHub release `vX.Y.Z` |
| PyPI | no (install from the `dev` branch) | the Python clients and the MCP server |

`main` only ever holds released code and `dev` is never merged into it.

Jobs:

1. **spec**
   - Checks out igvf-catalog at the dispatched ref and dumps its spec with `src/scripts/generateOpenapi.ts`. No database is needed.
   - Cleans and preprocesses it, sets `info.version` and checks the server host.
   - On the dev channel, it stops here if the processed spec is unchanged from the one committed on `dev` (ignoring `info.version`).
2. **clients** (python, python-async, r)
   - Clones each client repo at the channel branch, creating `dev` from `main` if needed.
   - Regenerates the client with `scripts/generate_client.sh`, then builds and smoke-tests it offline (Python: install the wheel, then import and check the version and API class; R: `R CMD check`, then install and load).
   - Pushes the result. On the release channel it also creates the GitHub release, which triggers the client's PyPI publish workflow.
3. **publish-spec**: commits the spec to this repo's channel branch once every client has succeeded. On release it also creates the `vX.Y.Z` release here, with the spec files attached.
4. **mcp** (release only)
   - Bumps `igvf-catalog-mcp` to `X.Y.Z` (`scripts/bump_mcp.py`), pinned to `igvf-catalog-async-client==X.Y.Z`.
   - Runs its tests against the async client wheel built in the clients job.
   - Waits for that client to appear on PyPI.
   - Pushes `main` and `dev` and releases it, which publishes it to PyPI.

A release that already exists in any of these repos makes the run fail before anything is generated. Existing releases are never overwritten.

## Running it by hand

Actions → *Generate catalog clients* → *Run workflow*:

- `channel`: `dev` or `release`.
- `ref`: the igvf-catalog sha, branch or tag. It must contain `src/scripts/generateOpenapi.ts`, which was added in igvf-catalog PR #926 (after v1.3).
- `tag`: the igvf-catalog release tag (release channel only). It sets the version.
- `dry_run` (default **on**): runs everything, including generation and smoke tests, but pushes and releases nothing. The client jobs list the files that would change.
- `force`: regenerates the dev clients even when the spec is unchanged.

## Running it locally

Requires Node 20+, Java 11+ and Python 3.9+.

```bash
# 1. dump the spec from an igvf-catalog checkout (dev host shown)
(cd ../igvf-catalog && npm ci && \
  ENV=production IGVF_CATALOG_OPEN_API_CONFIG_TYPE=production IGVF_CATALOG_PROTOCOL=https \
  IGVF_CATALOG_HOSTNAME=catalog-api-dev.demo.igvf.org \
  npx tsx src/scripts/generateOpenapi.ts ../igvf-catalog-client-openapi-spec/build/openapi_spec.json)

# 2. clean, preprocess and version it
python scripts/remove_endpoints.py --input build/openapi_spec.json
python scripts/preprocess_spec.py --input build/openapi_spec.json --output build/openapi_spec_processed.json
python scripts/set_spec_version.py build/openapi_spec*.json --version 1.3.1.dev0 --expect-host catalog-api-dev.demo.igvf.org

# 3. regenerate a client checkout in place
scripts/generate_client.sh python ../igvf-catalog-python-client build 1.3.1.dev0
```

## Layout

| Path | Purpose |
|---|---|
| `scripts/remove_endpoints.py` | Drops `/health` and `/autocomplete`, and fixes the `/llm-query` `aql_result` array schema |
| `scripts/preprocess_spec.py` | Hoists inline schemas into `components/schemas` with readable names, so model names stay short |
| `scripts/set_spec_version.py` | Sets `info.version`; `--expect-host` guards against shipping a spec for the wrong server |
| `scripts/spec_changed.py` | Prints `true`/`false`: whether two specs differ, ignoring `info.version` |
| `scripts/compute_version.py` | Release and dev versions (see the table above) |
| `scripts/generate_client.sh` | Wipes the files listed in `.openapi-generator/FILES`, runs the generator, reorders the README and copies the specs in |
| `scripts/reorder_readme.py` + `ordering.txt` | Orders the README endpoint table by `ordering.txt` (add new endpoints there) |
| `scripts/smoke_test_python.py` | Offline import, version and API check for an installed Python client |
| `scripts/bump_mcp.py` | Sets the igvf-catalog-mcp version and pins it to the matching async client (release job) |
| `config/*.yaml` | Generator options per client. License (MIT) and author (IGVF DACC) are set here |
| `openapitools.json` | Pins openapi-generator **7.14.0** for every client. Upgrade it deliberately, in its own change |
| `openapi_spec.json`, `openapi_spec_processed.json` | The latest spec for this branch, written by CI |

Each client repo keeps its own `templates/README.mustache` and an `.openapi-generator-ignore` that protects hand-written files (`.github/`, `templates/`, tests, `LICENSE`, …).

Tests: `pip install -r requirements-dev.txt && pytest scripts/tests`.

## Setup (one time)

- **GitHub App:** a GitHub App (*catalog client builder*) with **Contents: read & write** and **Metadata: read**.
  - Install it on this repo, the three client repos and `igvf-catalog-mcp`.
  - In this repo and in `igvf-catalog`, set the repo variable `CATALOG_CLIENT_BUILDER_APP_ID` and the secret `CATALOG_CLIENT_BUILDER_PRIVATE_KEY`.
  - App tokens are used so the tags and releases they create trigger the downstream publish workflows; `GITHUB_TOKEN` wouldn't.
- **Branch protection:** if `main` or `dev` is protected anywhere, let the App bypass it.
- **PyPI:** add a trusted publisher (owner `IGVF-DACC`, workflow `release_to_pypi.yml`, environment `pypi`) for `igvf-catalog-client`, `igvf-catalog-async-client` and `igvf-catalog-mcp`. Also add a `pypi` environment to each of those repos.
