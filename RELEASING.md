# Releasing

How a new version of Anything Goes Archive goes from `main` to published Docker images and a GitHub Release. Versions follow semver; replace `X.Y.Z` with the new version throughout.

**What ships isn't exactly what was tested.** Docker Publish builds the images fresh after the tag is pushed, so the base image (`3.N-slim`) can move to a new patch in between, and the arm64 image is only ever built by Docker Publish. Python packages can't drift, because `Pipfile.lock` pins exact versions and hashes. The closest this repo gets: test the same commit locally, let Compose Test pass on it, then let Compose Test check the published images from both registries on amd64 and arm64 after Docker Publish (step 6).

CI-only changes (a workflow fix) go to `main` without a version bump, tag or release.

## 1. Bump the version

The version lives in one file: `__version__` in `app/__init__.py`. It must match the tag, and it also feeds the Reddit API user agent in `app/config.py`, so a missed bump sends the wrong version to Reddit on every request.

If this release also changes the Python version, these must all agree on `3.N`:

| File | Setting | Pins |
|---|---|---|
| `Dockerfile` | `ARG DOCKER_PYTHON_V=3.N-slim` | minor only |
| `Pipfile` | `python_version = "3.N"` | minor only |
| `Pipfile.lock` | `_meta.requires.python_version` | rewritten by `pipenv lock --clear`; never edit by hand |
| `.github/workflows/lint.yml` | `python-version: ["3.N"]` | minor only |

Also update the Python version in the README's Tech Stack section. pipenv runs in a throwaway container on the new `3.N`, so nothing is installed on the host; this regenerates the lock file, for a Python change or a dependency update:

```bash
docker run --rm -u 1000:1000 -e HOME=/tmp -v "$PWD":/src -w /src python:3.N-slim \
  sh -c 'pip install -q --user --no-warn-script-location pipenv && python -m pipenv lock --clear'
```

## 2. Write the release notes in CHANGELOG.md

In `CHANGELOG.md`, rename `## Unreleased` to the version heading with today's date (America/New_York):

```markdown
## [vX.Y.Z](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/vX.Y.Z) (YYYY-MM-DD)
```

- `### Upgrading` comes first and lists what a running stack must change (variables, `compose.yaml`, the data folder), as instructions naming the old and new values. Then `### What's New` and `### Bug Fixes`. Leave out empty sections.
- Written for the people who run the app, most significant change first. Never copied from commit messages.
- Read every commit since the previous tag, bodies included (`git log --reverse vPREV..main`), not just `--oneline`.

## 3. Test the commit locally

The local container uses the same Reddit API credentials as prod, so stop the prod stack first, or both instances will poll Reddit with one client.

```bash
docker compose up -d --build
docker ps   # healthy
```

`docker compose` inside the repo also loads `compose.override.yaml`, so this builds and runs `r-fantasybaseball-indexer:local`. Try the main features for real: the thread list, a thread page, search and settings, and check that the logs show the scheduler storing comments.

## 4. Commit and tag

The release commit holds only the version bump and CHANGELOG. Tags are annotated.

```bash
git add app/__init__.py CHANGELOG.md   # plus the Python version files, if step 1 touched them
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git tag -n && git log --oneline --decorate -5
```

## 5. Push `main`, wait for CI, then push the tag

Docker Publish starts the moment the tag arrives and doesn't wait for the other workflows, so `main` goes first.

Before pushing anything, `gh workflow list` must show Compose Test as `active`; if it doesn't, `gh workflow enable compose-test.yml`. A disabled workflow starts on no trigger, so a disabled Compose Test would skip step 6's published-image test without a word.

```bash
git push origin main
sleep 15  # give GitHub a moment to queue the runs
for wf in lint.yml compose-test.yml; do
  gh run watch --exit-status "$(gh run list --workflow $wf --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId -q '.[0].databaseId')"
done
git push origin vX.Y.Z
git ls-remote --tags origin
git remote -v   # SSH, no credentials in any URL
```

Push one tag at a time. Several tags pushed together publish in parallel, and `latest` can end up on an older version.

### Wrong tag after pushing

The images are already published as `X.Y.Z`, `X.Y` and `latest`. Fix the cause, delete the release if one exists (`gh release delete vX.Y.Z --yes`), then move the tag and force-push it; the new publish overwrites those image tags:

```bash
git tag -fa vX.Y.Z -m "vX.Y.Z"
git push --force origin vX.Y.Z
```

## 6. Watch the images publish, then the published-image test

```bash
sleep 15  # give GitHub a moment to queue the run
gh run watch --exit-status "$(gh run list --workflow docker.yml --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId -q '.[0].databaseId')"
sleep 15  # give GitHub a moment to queue the run
gh run watch --exit-status "$(gh run list --workflow compose-test.yml --event workflow_run --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId -q '.[0].databaseId')"
```

Docker Publish builds amd64 and arm64, pushes to GHCR and Docker Hub with a build provenance attestation for each, and tags `X.Y.Z`, `X.Y`, `latest` and `main`. When it finishes, it starts one Compose Test run with eight jobs: the `X.Y.Z` image from each registry, on amd64 and arm64 runners, each run once with the plain `compose.yaml` and once hardened. All eight must pass. The `--commit` filters keep an earlier release's runs from being picked up; without them, the first `gh run list` can return the previous release's finished Docker Publish run, and `gh run watch` passes at once. The Compose Test filter matches only while nothing else lands on `main` between the release commit and the tag push.

### If the published image is bad

If one fails, point `latest` back at the previous version (nothing gets rebuilt), then fix forward with a new patch version:

```bash
docker buildx imagetools create -t ghcr.io/wazam/r-fantasybaseball-indexer:latest ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.(Z-1)
docker buildx imagetools create -t wazam123/r-fantasybaseball-indexer:latest wazam123/r-fantasybaseball-indexer:X.Y.(Z-1)
```

Do the same for `main`, and for `X.Y` if it moved.

## 7. Create the GitHub Release

`CHANGELOG.md` is the only source of release notes:

```bash
awk '/^## \[vX.Y.Z\]/{f=1;next} /^## /{f=0} f' CHANGELOG.md \
  | gh release create vX.Y.Z --title "vX.Y.Z" --latest --notes-file -
```

## 8. Check the published image

```bash
docker buildx imagetools inspect ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z   # linux/amd64 and linux/arm64, nothing else
for image in ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z wazam123/r-fantasybaseball-indexer:X.Y.Z; do
  gh attestation verify oci://$image --repo wazam/r-fantasybaseball-indexer \
    --signer-workflow wazam/r-fantasybaseball-indexer/.github/workflows/docker.yml --source-ref refs/tags/vX.Y.Z
done
```

`docker.yml` attests each pushed image with `actions/attest` (since v0.4.1). The attestations live in GitHub's attestation store, not in the registries, and both build steps set `provenance: false` (since v0.4.2), so buildx adds no unsigned provenance manifests (`unknown/unknown`) to the index. Each release therefore adds only its image to GHCR, and the package page's header shows it. Up to v0.4.0, `docker.yml` signed with cosign instead: the signature, pushed last as a `sha256-<digest>.sig` tag in the image's package, became the version the page showed. Those signatures were deleted from the package on 2026-11-11, so v0.4.0 and older can't be checked with `cosign verify` (their entries in Sigstore's transparency log remain).

Then the labels and GHCR's description annotation, in both registries. Each platform should show the same 12 labels: the Dockerfile's 9 (title, description, url, source, documentation, licenses, authors, vendor, base.name), plus `created`, `revision` equal to `git rev-parse vX.Y.Z^{commit}`, and `version` `X.Y.Z`. The index should hold the description:

```bash
for image in ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z wazam123/r-fantasybaseball-indexer:X.Y.Z; do
  docker buildx imagetools inspect $image --format '{{json .Image}}' | python3 -c "import json,sys; d=json.load(sys.stdin); [print(p, json.dumps(v['config']['Labels'], indent=1, sort_keys=True)) for p, v in d.items()]"
  docker buildx imagetools inspect $image --raw | python3 -c "import json,sys; print(json.load(sys.stdin).get('annotations'))"
done
```

Then open `https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer` and check that its header shows the `X.Y.Z` image, not a `sha256-...sig` tag, with the description and a `docker pull` command for the image.

### GHCR package versions

GHCR lists every manifest as a version. A release adds three: its tagged index and, untagged, the amd64 and arm64 images the index points to. v0.4.1 and older also have two untagged `unknown/unknown` provenance manifests each. Never delete an untagged version that a tagged index lists: pulls of that release, or tools that read the whole index, break. Docker Hub's Image Management page lists the same manifests under the same rule, its "Preview and delete" also takes everything a selected index references, and its deletions can't be undone. To see what each version is:

```bash
gh api --paginate '/users/wazam/packages/container/r-fantasybaseball-indexer/versions?per_page=100' \
  --jq '.[] | "\(.id) \(.name) \(.metadata.container.tags|join(","))"'
docker buildx imagetools inspect --raw ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z   # the digests the index lists
```

Listing needs a token with `read:packages` and deleting one with `delete:packages` (`gh auth refresh -h github.com -s read:packages,delete:packages`, then `-r` to drop them). GitHub can restore a deleted version for 30 days.

## 9. Update the Docker Hub page and GitHub About

They copy the README and don't update on their own (GHCR's page does):

- **Docker Hub:** at hub.docker.com, open the repository's General tab, update the short description (at most 100 characters, saying what the README's first sentence says), and replace the overview with the output of the command below, which builds it from `README.md` so the page can't drift from it. In order, with every link absolute, it has:
  - a first line `GitHub: https://github.com/wazam/r-fantasybaseball-indexer`, then the README's intro paragraph without its icon (Docker Hub shows the repository's avatar)
  - `## Quick Start`: the pointer to Set Up Reddit API Access, the two registries, the `compose.yaml`, the `./data` owner paragraph, and the numbered steps, without Build from Source or Manual Install
  - `## Features`, then `## Issues and Feature Requests` with the README's Contributing text: the issues sentence and the CHANGELOG, ROADMAP and RELEASING links

  Then check the public page, `https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer`.

```bash
# Run from the repo root.
/usr/bin/python3 -I - <<'EOF'
import re
s = open('README.md').read()
def sec(a, b):
    i = s.index(a); return s[i:s.index(b, i)].rstrip() + '\n'
def swap(t, old, new):
    assert t.count(old) == 1, old
    return t.replace(old, new)
base = 'https://github.com/wazam/r-fantasybaseball-indexer'
ghcr, hub = 'ghcr.io/wazam/r-fantasybaseball-indexer:latest', 'wazam123/r-fantasybaseball-indexer:latest'
intro = sec('![Anything Goes Archive]', '## Table of Contents').replace('![Anything Goes Archive](docs/icon.png) ', '')
run = sec('The image is published to', '1. **Create the data directory**')
run = swap(run, f'[Docker Hub](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer) (', 'Docker Hub (')
run = swap(run, 'This is the `compose.yaml` to use:', 'This is the `compose.yaml` to use, pulling from Docker Hub:')
run = swap(run, ghcr, hub)
steps = sec('1. **Create the data directory**', '---\n\n### Build from Source')
dl_end = '/main/compose.yaml\n   ```\n'
steps = swap(steps, dl_end, dl_end + f'\n   The downloaded `compose.yaml` pulls from GHCR. To pull from Docker Hub instead, change its `image:` line to `{hub}`, as above.\n')
steps = swap(steps, ' (see [Set Up Reddit API Access](#set-up-reddit-api-access))', '')
steps = swap(steps, 'Without the two credentials, the app exits at startup with an error in `docker compose logs`.', f'Without the two credentials, the app exits at startup with an error in `docker compose logs`. Every setting is described in the README\'s [Environment Variables]({base}#environment-variables) table.')
steps = swap(steps, '[http://localhost:9009](http://localhost:9009)', '`http://localhost:9009`')
quick = '\n'.join([
    '## Quick Start', '',
    f'You need Reddit API credentials first; see [Set Up Reddit API Access]({base}#set-up-reddit-api-access).', '',
    run, steps])
feat = sec('## Features', '## Tech Stack')
issues = sec('## Contributing', '## Disclaimers').replace('## Contributing', '## Issues and Feature Requests')
issues = re.sub(r'\]\((?!https?://)([^)]+)\)', lambda m: f']({base}/blob/main/{m.group(1)})', issues)
print('\n'.join([f'GitHub: {base}', '', intro, quick, feat, issues]).rstrip())
EOF
```

An `AssertionError` or `ValueError` means the README changed shape where the command expects it; update the command to match before pasting anything.

- **GitHub About:** the same sentence, through the gear icon next to About or `gh repo edit wazam/r-fantasybaseball-indexer --description "..."`.

The sentence also lives in the Dockerfile's `org.opencontainers.image.description` label, which `docker.yml` reads for GHCR's package page. A new sentence goes into the Dockerfile in the release's own commits, then onto Docker Hub and GitHub About here. Keep double quotes out of it: the label is written in double quotes, and `docker.yml`'s `sed` stops at the first one.

## 10. Verify

- The app runs: healthy, normal logs, main features work.
- The CHANGELOG heading link opens the release.
- Every release page matches CHANGELOG.md:

  ```bash
  for v in $(git tag -l 'v*'); do
    diff <(gh release view $v --json body -q .body | tr -d '\r' | sed '/^$/d') \
         <(awk "/^## \\[$v\\]/{f=1;next} /^## /{f=0} f" CHANGELOG.md | sed '/^$/d') >/dev/null \
      && echo "$v matches" || echo "$v DIFFERS"
  done
  ```

  For a page that differs, move anything better on the page into CHANGELOG.md first, then overwrite the page: `awk "/^## \\[$v\\]/{f=1;next} /^## /{f=0} f" CHANGELOG.md | gh release edit $v --notes-file -`.
- The README still matches the app, and the Docker Hub page matches the README.
