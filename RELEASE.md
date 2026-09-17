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
Use this repo's normal commit style: a semantically-prefixed title
(`feat:`/`fix:`/`docs:`/`chore:`/`refactor:`, scoped to what changed in the
codebase), then a prose body explaining why, and no attribution lines. This
is a developer-facing artifact; keep it separate from the user-facing
release notes in step 4, don't copy one into the other.

```bash
git checkout main
git merge dev
git add app/__init__.py   # plus any Python-version-sync files, if this release touches those too
git commit -m "$(cat <<'EOF'
chore: bump version to X.Y.Z

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

Release notes are written fresh for the user, not copied from commit
messages: group by user-visible impact, order by significance, and use
plain language instead of commit-speak.

Read the full commit log back to the previous tag, titles and bodies both,
not just a truncated `git log --oneline`: a title alone can undersell what
actually changed (`git log --reverse vPREV..dev` to see every commit in
order, `git log -1 --format="%B" <hash>` for a specific commit's full
body). A commit's body can carry a real user-facing change that its title
doesn't hint at (e.g. a "harden against API errors" commit that also quietly
removed a broken config option), and a commit merged early in the branch's
life is just as easy to lose track of as a recent one.

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
- No manual README changes needed for the badges: the version, pulls, image
  size, and latest-release badges are all shields.io endpoints pulling live
  from GHCR, Docker Hub, and GitHub, so they update on their own once the
  above are live.
- If this release changed the UI, double-check README's Features list and
  Screenshots section are still accurate; unlike the badges, none of that
  updates itself.
- The Docker Hub repository description (intro paragraph, Features list,
  and Run via Docker quickstart, mirrored from README.md) isn't linked to
  this repo and won't update on its own either. Update it manually to match
  if any of those sections changed.
