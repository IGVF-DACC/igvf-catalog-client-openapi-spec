# igvf-catalog-client-openapi-spec

The OpenAPI spec of the [IGVF Catalog API](https://api.catalogkg.igvf.org/) and the GitHub Actions pipeline that generates its clients from it:

| Client | Repo | Install |
|---|---|---|
| Python | [igvf-catalog-python-client](https://github.com/IGVF-DACC/igvf-catalog-python-client) | `pip install igvf-catalog-client` |
| Python (asyncio) | [igvf-catalog-async-python-client](https://github.com/IGVF-DACC/igvf-catalog-async-python-client) | `pip install igvf-catalog-async-client` |
| R | [igvf-catalog-r-client](https://github.com/IGVF-DACC/igvf-catalog-r-client) | `remotes::install_github("IGVF-DACC/igvf-catalog-r-client@vX.Y.Z")` |
| MCP server | [igvf-catalog-mcp](https://github.com/IGVF-DACC/igvf-catalog-mcp) | `pip install igvf-catalog-mcp` |

Both Python packages ship the processed spec they were generated from, as `<package>/openapi_spec_processed.json` (`igvf_catalog_client`, `igvf_catalog_async_client`). It keeps what the generated code drops, such as enum values of query parameters and page-size limits; the MCP server reads it at runtime. Load it with `importlib.resources.files("<package>").joinpath("openapi_spec_processed.json")`. Each client repo's `templates/setup.mustache` lists it in `package_data`.

## How it works

[`igvf-catalog`](https://github.com/IGVF-DACC/igvf-catalog) sends a `repository_dispatch` to this repo (its `.github/workflows/trigger-clients.yml`), which runs [`generate-clients.yml`](.github/workflows/generate-clients.yml):

| | Dev channel | Release channel | Post channel |
|---|---|---|---|
| Trigger | push to `igvf-catalog@dev` (`catalog-dev`) | published, non-prerelease `igvf-catalog` release (`catalog-release`) | by hand only (see [Post-releases](#post-releases-of-the-python-clients)) |
| Spec server | `https://catalog-api-dev.demo.igvf.org/api` | `https://api.catalogkg.igvf.org/api` | the spec released here as `vX.Y.Z`, unchanged |
| Version | Python `X.Y.(Z+1).devYYYYMMDDHHMMSS`, R `X.Y.Z.9000`, where `X.Y.Z` is the latest igvf-catalog release | the release tag, normalized (`v1.3` → `1.3.0`) | Python `X.Y.Z.postN`; R isn't built |
| Branch in every downstream repo | `dev` | `main` + GitHub release `vX.Y.Z` | the two Python client repos only: `main` + GitHub release `vX.Y.Z.postN` |
| PyPI | no (install from the `dev` branch) | the Python clients and the MCP server | the Python clients |

`main` only ever holds released code and `dev` is never merged into it.

Jobs:

1. **spec**
   - Checks out igvf-catalog at the dispatched ref and dumps its spec with `src/scripts/generateOpenapi.ts`. No database is needed.
   - Cleans and preprocesses it, sets `info.version` and checks the server host.
   - On the dev channel, it stops here if the processed spec is unchanged from the one committed on `dev` (ignoring `info.version`).
   - On the post channel it does none of the above: it takes both spec files as committed at this repo's tag `vX.Y.Z`.
2. **clients** (python, python-async, r; no r on the post channel)
   - Clones each client repo at the channel branch, creating `dev` from `main` if needed.
   - Regenerates the client with `scripts/generate_client.sh`, then builds and smoke-tests it offline (Python: install the wheel, then import and check the version, the API class and the shipped spec; R: `R CMD check`, then install and load).
   - Pushes the result. On the release and post channels it also creates the GitHub release, which triggers the client's PyPI publish workflow.
3. **publish-spec** (not on the post channel): commits the spec to this repo's channel branch once every client has succeeded. On release it also creates the `vX.Y.Z` release here, with the spec files attached.
4. **mcp** (release only)
   - Bumps `igvf-catalog-mcp` to `X.Y.Z` (`scripts/bump_mcp.py`), pinned to `igvf-catalog-async-client==X.Y.Z`.
   - Runs its tests against the async client wheel built in the clients job.
   - Waits for that client to appear on PyPI.
   - Pushes `main` and `dev` and releases it, which publishes it to PyPI.

A release that already exists in any of these repos makes the run fail before anything is generated (on the post channel, only the two Python client repos are checked). Existing releases are never overwritten.

## Versioning

- The **release segment** `X.Y.Z` of every client and of the MCP server is the igvf-catalog version they were generated from.
- A client **post-release** `X.Y.Z.postN` repackages the same API: it's generated from the same spec as `X.Y.Z`. The shipped spec's `info.version` is `X.Y.Z`, i.e. the package version without `.postN`. (A dev build's spec carries the full dev version.)
- MCP `.postN` releases are numbered independently of the clients' `.postN`. The MCP server pins an exact client version (`igvf-catalog-async-client==…`), which may be a client post-release.
- Under PEP 440, `==X.Y.Z` doesn't match `X.Y.Z.postN`, so a pin moves to a post-release only when it's changed explicitly. `X.Y.(Z+1).devN` sorts after `X.Y.Z.postN`.

## Post-releases of the Python clients

Use the post channel when the Python packages need to change without a new catalog release, e.g. a template or packaging fix. Catalog releases are months apart.

1. Merge the template or pipeline change into the client repos' `main` and this repo's `main` first. The run generates from both.
2. Run the workflow by hand with `channel=post`, `base_version` (e.g. `1.3.0`, which must be a release tag `v1.3.0` here) and `post_number` (e.g. `1`), with `dry_run` on. Leave `ref` and `tag` empty.
3. Check the client jobs' *Show changes*: compared with the last release, only the intended files should change.
4. Rerun with `dry_run` off. This commits to the two Python client repos' `main` and creates their `vX.Y.Z.postN` releases, which publish to PyPI.

The post channel doesn't build R (R versions can't express `.postN`), doesn't touch this repo's spec or releases, and never releases the MCP server; pin the MCP to the post-release by hand if it needs it.

## Running it by hand

Actions → *Generate catalog clients* → *Run workflow*:

- `channel`: `dev`, `release` or `post`.
- `ref`: the igvf-catalog sha, branch or tag (dev and release channels). It must be igvf-catalog PR #956 (`15f86847`) or later: the workflow runs Node 24 with npm 11, and the `package-lock.json` of older refs doesn't install there (`npm ci` fails).
- `tag`: the igvf-catalog release tag (release channel only). It sets the version.
- `base_version`, `post_number`: the released `X.Y.Z` to repackage and `N` for `X.Y.Z.postN` (post channel only; see [Post-releases](#post-releases-of-the-python-clients)).
- `dry_run` (default **on**): runs everything, including generation and smoke tests, but pushes and releases nothing. The client jobs list the files that would change.
- `force`: regenerates the dev clients even when the spec is unchanged.

## Running it locally

Requires Node 24, Java 11+ and Python 3.9+.

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

To reproduce a post-release, skip steps 1 and 2 and take the released spec instead:

```bash
mkdir -p build
git show v1.3.0:openapi_spec.json > build/openapi_spec.json
git show v1.3.0:openapi_spec_processed.json > build/openapi_spec_processed.json
scripts/generate_client.sh python ../igvf-catalog-python-client build 1.3.0.post1
```

## Layout

| Path | Purpose |
|---|---|
| `scripts/remove_endpoints.py` | Drops `/health` and `/autocomplete`, fixes the `/llm-query` `aql_result` array schema and strips the per-operation `security` requirements (the API is public) |
| `scripts/preprocess_spec.py` | Hoists inline schemas into `components/schemas` with readable names, so model names stay short. Keeps the component schemas the spec already has and renames them to PascalCase (`error.BAD_REQUEST` → `ErrorBadRequest`) |
| `scripts/set_spec_version.py` | Sets `info.version`; `--expect-host` guards against shipping a spec for the wrong server |
| `scripts/spec_changed.py` | Prints `true`/`false`: whether two specs differ, ignoring `info.version` |
| `scripts/compute_version.py` | Release, dev and post versions (see the table above) |
| `scripts/generate_client.sh` | Wipes the files listed in `.openapi-generator/FILES`, runs the generator, reorders the README and copies the specs in: both to the repo root, and the processed spec into the Python package |
| `scripts/reorder_readme.py` + `ordering.txt` | Orders the README endpoint table by `ordering.txt` (add new endpoints there) |
| `scripts/smoke_test_python.py` | Offline import, version and API check for an installed Python client, plus a check of the shipped spec (present, parses, enough operations, `info.version` = package version without `.postN`) |
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
