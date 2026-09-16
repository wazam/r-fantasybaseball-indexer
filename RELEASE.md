# Release Pipeline

Do these in order. Nothing here should run until everything's been tested
locally via the normal dev cycle (`docker compose build --no-cache && docker
compose up -d`).

## 1. Bump the app version

Always required, every release:

- `app/__init__.py`: `__version__` (app release version; also feeds the
  Reddit API User-Agent string in `app/config.py`, so a missed bump means the
  wrong version gets sent to Reddit on every request)

Only required if this release also bumps the Python version itself; skip
this block otherwise:

- `.tool-versions`: `python A.B.C` (asdf, exact patch; the only file pinned
  to a specific patch, bump whenever your local interpreter changes)
- `Pipfile`: `python_version = "A.B"` (major.minor only, loosened so Pipenv
  doesn't break when the Docker base image patch drifts ahead of
  `.tool-versions`)
- `Pipfile.lock`: regenerate with `pipenv lock` after touching `Pipfile`'s
  `python_version`
- `Dockerfile`: `ARG DOCKER_PYTHON_V=A.B-slim` (image tag, major.minor only,
  auto-tracks latest patch)
- `.github/workflows/lint.yml`: `python-version: ["A.B"]` (major.minor only,
  auto-selects latest patch)
- `README.md`: `Python A.B` in Tech Stack (major.minor reference, update on
  major bumps)

## 2. Commit and tag

Work happens on `dev`; `main` only advances at a deliberate release point.
Merge `dev` into `main`, commit the version bump there, tag, and push both.
Use this repo's normal commit style (a plain descriptive title, then a prose
body explaining why, not a semantic-prefix bullet list), and no attribution
lines.

```bash
git checkout main
git merge dev
git add app/__init__.py   # plus any Python-version-sync files, if this release touches those too
git commit -m "$(cat <<'EOF'
Bump version to X.Y.Z

<why this release exists, one or two sentences>
EOF
)"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

## 3. Wait for CI before calling the release done

The push to `main` and the tag push together trigger three separate
workflows:

- `lint.yml` (push to `main`)
- `compose-test.yml` (push to `main`)
- `docker.yml` (tag push matching `v*.*.*`; builds, pushes to GHCR and
  Docker Hub, and cosign-signs the image)

Confirm all three succeed, not just the one tied to whatever you were
working on:

```bash
gh run list --branch main --limit 5
```

It's easy to check only the workflow tied to whatever you were fixing and
assume the rest are fine. Check all three explicitly, every time.

## 4. Create the GitHub Release

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(cat <<'EOF'
**What's New**

- ...

**Bug Fixes**

- ...
EOF
)"
```

Or without the CLI: create the release at
<https://github.com/wazam/r-fantasybaseball-indexer/releases/new>, select the
`vX.Y.Z` tag, and paste in notes.

## 5. Verify

- GHCR and Docker Hub show the new tag published
- GitHub Release page shows it live:
  <https://github.com/wazam/r-fantasybaseball-indexer/releases>
- No manual README changes needed here: the version, pulls, image size, and
  latest-release badges are all shields.io endpoints pulling live from
  GHCR, Docker Hub, and GitHub, so they update on their own once the above
  are live.
