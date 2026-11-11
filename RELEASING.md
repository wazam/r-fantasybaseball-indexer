# Releasing

Every release goes from `main`. CI builds and publishes the image when a tag is pushed, so the steps below test the commit, wait for CI on it, and then check what was published.

**What ships isn't exactly what was tested.** Docker Publish builds the images fresh after the tag is pushed, so the base image (`3.N-slim`) can move to a new patch in between, and the arm64 image is only ever built by Docker Publish. Python packages can't drift, because `Pipfile.lock` pins exact versions and hashes. The closest this repo gets: test the same commit locally, let Compose Test pass on it, then let Compose Test check the published images from both registries on amd64 and arm64 after Docker Publish (step 6).

CI-only changes (a workflow fix) go to `main` without a version bump, tag or release.

## 1. Bump the version

The version lives in one file: `__version__` in `app/__init__.py`. It must match the tag, and it also feeds the Reddit API user agent in `app/config.py`, so a missed bump sends the wrong version to Reddit on every request.

If this release also changes the Python version, these must all agree on `3.N`:

| File | Setting | Pins |
|---|---|---|
| `.tool-versions` | `python 3.N.P` | the full patch, for asdf |
| `Dockerfile` | `ARG DOCKER_PYTHON_V=3.N-slim` | minor only |
| `Pipfile` | `python_version = "3.N"` | minor only |
| `Pipfile.lock` | `_meta.requires.python_version` | rewritten by `pipenv lock --clear`; never edit by hand |
| `.github/workflows/lint.yml` | `python-version: ["3.N"]` | minor only |

Also update the Python version in the README's Tech Stack section. After `asdf install python 3.N.P`, run `python -m pip install pipenv` and `asdf reshim`, since pipenv is installed per Python version.

## 2. Write the release notes

In `CHANGELOG.md`, rename `## Unreleased` to the version heading with today's date (America/New_York):

```markdown
## [vX.Y.Z](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/vX.Y.Z) (YYYY-MM-DD)
```

- `### Upgrading` comes first and lists what a running stack must change (variables, `compose.yaml`, the data folder), as instructions naming the old and new values. Then `### What's New` and `### Bug Fixes`. Leave out empty sections.
- Written for the people who run the app, most significant change first. Never copied from commit messages.
- Read every commit since the previous tag, bodies included (`git log --reverse vPREV..main`), not just `--oneline`.

## 3. Test the commit locally

```bash
docker compose up -d --build
docker ps   # healthy
```

`docker compose` inside the repo also loads `compose.override.yaml`, so this builds and runs `r-fantasybaseball-indexer:local`. Try the main features for real: the thread list, a thread page, search and settings, and check that the logs show the scheduler storing comments.

## 4. Release commit and tag

The release commit holds only the version bump and CHANGELOG. Tags are annotated.

```bash
git add app/__init__.py CHANGELOG.md   # plus the Python version files, if step 1 touched them
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git tag -n && git log --oneline --decorate -5
```

## 5. Push `main`, wait for CI, then push the tag

Docker Publish starts the moment the tag arrives and doesn't wait for the other workflows, so `main` goes first:

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

## 6. Watch Docker Publish and the published-image tests

```bash
gh run watch --exit-status "$(gh run list --workflow docker.yml --limit 1 --json databaseId -q '.[0].databaseId')"
sleep 15  # give GitHub a moment to queue the run
gh run watch --exit-status "$(gh run list --workflow compose-test.yml --event workflow_run --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId -q '.[0].databaseId')"
```

Docker Publish builds amd64 and arm64, pushes to GHCR and Docker Hub with a build provenance attestation for each, and tags `X.Y.Z`, `X.Y`, `latest` and `main`. When it finishes, it starts one Compose Test run with four jobs: the `X.Y.Z` image from each registry, on amd64 and arm64 runners. All four must pass. The `--commit` filter keeps an earlier release's run from being picked up, and matches only while nothing else lands on `main` between the release commit and the tag push.

A disabled workflow starts on no trigger, so a Compose Test that GitHub disabled for inactivity skips this run without a word. Before pushing the tag, `gh workflow list` must show Compose Test as `active`; if it doesn't, `gh workflow enable compose-test.yml`.

If one fails, point `latest` back at the previous version (nothing gets rebuilt), then fix forward with a new patch version:

```bash
docker buildx imagetools create -t ghcr.io/wazam/r-fantasybaseball-indexer:latest ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.(Z-1)
docker buildx imagetools create -t wazam123/r-fantasybaseball-indexer:latest wazam123/r-fantasybaseball-indexer:X.Y.(Z-1)
```

Do the same for `main`, and for `X.Y` if it moved.

## 7. Create the GitHub release

`CHANGELOG.md` is the only source of release notes:

```bash
awk '/^## \[vX.Y.Z\]/{f=1;next} /^## /{f=0} f' CHANGELOG.md \
  | gh release create vX.Y.Z --title "vX.Y.Z" --latest --notes-file -
```

## 8. Check the published image

```bash
docker buildx imagetools inspect ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z   # both platforms present
for image in ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z wazam123/r-fantasybaseball-indexer:X.Y.Z; do
  gh attestation verify oci://$image --repo wazam/r-fantasybaseball-indexer \
    --signer-workflow wazam/r-fantasybaseball-indexer/.github/workflows/docker.yml --source-ref refs/tags/vX.Y.Z
done
```

The attestations live in GitHub's attestation store, not in the registries, so nothing besides the image lands in GHCR, and its package page shows the image. Up to v0.4.0, `docker.yml` signed with cosign instead, and the signature, pushed last as a tag in the image's package, was what the package page showed. Those releases still verify with `cosign verify ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z --certificate-identity "https://github.com/wazam/r-fantasybaseball-indexer/.github/workflows/docker.yml@refs/tags/vX.Y.Z" --certificate-oidc-issuer https://token.actions.githubusercontent.com`, through `docker run --rm ghcr.io/sigstore/cosign/cosign:v2.N.P verify ...` where cosign isn't installed.

Then the labels and GHCR's description annotation, in both registries. Each platform should show the same 12 labels: the Dockerfile's 9 (title, description, url, source, documentation, licenses, authors, vendor, base.name), plus `created`, `revision` equal to `git rev-parse vX.Y.Z^{commit}`, and `version` `X.Y.Z`. The index should hold the description:

```bash
for image in ghcr.io/wazam/r-fantasybaseball-indexer:X.Y.Z wazam123/r-fantasybaseball-indexer:X.Y.Z; do
  docker buildx imagetools inspect $image --format '{{json .Image}}' | python3 -c "import json,sys; d=json.load(sys.stdin); [print(p, json.dumps(v['config']['Labels'], indent=1, sort_keys=True)) for p, v in d.items()]"
  docker buildx imagetools inspect $image --raw | python3 -c "import json,sys; print(json.load(sys.stdin).get('annotations'))"
done
```

Then open `https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer` and check that its header shows the `X.Y.Z` image, not a `sha256-...sig` tag, with the description and a `docker pull` command for the image.

## 9. Update Docker Hub and GitHub About

They copy the README and don't update on their own (GHCR's page does):

- **Docker Hub:** at hub.docker.com, open the repository's General tab and update the overview (intro, features, the Quick Start `compose.yaml`, required settings; absolute links) and the short description (at most 100 characters, saying what the README's first sentence says). Then check the public page, `https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer`.
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

## Wrong tag after pushing

The images are already published as `X.Y.Z`, `X.Y` and `latest`. Fix the cause, delete the release if one exists (`gh release delete vX.Y.Z --yes`), then move the tag and force-push it; the new publish overwrites those image tags:

```bash
git tag -fa vX.Y.Z -m "vX.Y.Z"
git push --force origin vX.Y.Z
```
