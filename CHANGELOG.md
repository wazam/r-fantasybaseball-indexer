# Changelog

Release notes for every version, newest first. Each version is tagged in git and has a matching [release on GitHub](https://github.com/wazam/r-fantasybaseball-indexer/releases). Changes that haven't been released yet collect under **Unreleased**, and [RELEASING.md](RELEASING.md) covers how to ship them.

## [v0.4.0](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/v0.4.0) (2026-11-11)

### Upgrading

- `PUID` and `PGID` are removed. The container now starts as the user in your compose file's `user:` setting (default `1000:1000`) and no longer changes the owner of `./data` on startup. If you set `PUID`/`PGID`, remove them, then either give `./data` to uid 1000 (`sudo chown -R 1000:1000 ./data`) or add `user: "PUID:PGID"` with the same numbers to keep the current owner. If you didn't set them, nothing changes. If `./data` isn't writable by the container's user, it now stops with an error that says how to fix it.
- `compose.yaml` now reads every setting from a `.env` file next to it, with defaults for the optional ones, instead of values typed into the file. If you switch to the new `compose.yaml`, put your settings in `.env` (start from `.env.example`). Compose refuses to start without `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`.
- The compose service is renamed from `app` to `anything-goes-archive`, matching the container name. If you switch to the new `compose.yaml`, first run `docker compose down` with the old one. Otherwise Compose stops with an error that the container name `anything-goes-archive` is already in use, and `--remove-orphans` doesn't avoid it.
- Optional: the example `compose.yaml` now hardens the container with `user`, `cap_drop: ALL`, `no-new-privileges`, a read-only filesystem (`read_only: true`, with a 256 MB `/tmp` tmpfs), `init: true`, a 1 GB memory limit (`mem_limit: 1g`) and a 128-process limit (`pids_limit: 128`). Copy those settings into your own compose file to get the same protection. Nothing breaks if you skip them.
- The undocumented `DATABASE_URL` setting is removed. The database is always `./data/data.db` (`/app/data/data.db` in the container). If you set `DATABASE_URL`, move your database file there before upgrading.

### What's New

- New optional `FORWARDED_ALLOW_IPS` setting for running behind a reverse proxy. Set it to your proxy's IP so logs show real client IPs instead of the proxy's, and redirects (like `/settings/` to `/settings`) keep `https://` instead of dropping to `http://`.
- New optional `REDDIT_USER_AGENT` setting, so the requests to Reddit's API can carry your own username instead of the project author's.
- Runs on Python 3.14, up from 3.13, with every dependency updated to its latest release.
- The image's labels are accurate: title `Anything Goes Archive` and the project's own description instead of the repository name and its GitHub About text, plus the base image's name. GHCR's package page shows the description. Local builds leave out the build date, commit, and version instead of setting them to `unknown`.

### Bug Fixes

- Fixed security vulnerabilities in two dependencies: certifi trusted root certificates whose keys were compromised (critical), and urllib3 could hang, use unbounded memory, or ignore HTTPS proxy settings (high).
- Q&A sort on a thread page now puts the comments with the most replies first. Each comment's reply counts were saved once and never updated, so comments that drew replies later sorted too low. The first start after upgrading recounts the reply counts of every stored comment, which takes a few seconds.
- Comments from deleted Reddit accounts show `[deleted]` as their author, as on Reddit, instead of `None`, which looked like a single user and linked to an unrelated account, u/None. Comments archived before their author deleted the account keep the name. The first start after upgrading relabels stored comments, and a blocked or favorited `None` carries over to `[deleted]`.
- Search filters work as the Settings page describes. `-author:`, `-flair:` and `-score:` leave out what they name instead of being ignored, so `-author:name` no longer returns only that author's comments. Repeating `author:` or `flair:` matches any of the values instead of nothing, and `score:=3` finds comments with exactly that score instead of being ignored.
- Search treats `%` and `_` as ordinary characters. They worked as wildcards, so `"100%"` also found comments with just `100` in them, and `author:_` matched every comment.
- Comments with stray asterisks, underscores or tildes now display the way Reddit shows them, instead of turning part of the comment bold or italic. Strikethrough written like `~~this~~that` now renders correctly too.

## [v0.3.0](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/v0.3.0) (2026-09-17)

### Upgrading

- Replace your compose file with the new `compose.yaml`. The separate `web` and `scheduler` services are now one `app` service running a single image.
- If you set `BACKFILL_DATE=auto`, change it to an explicit `YYYY-MM-DD` date. `auto` was removed because it could silently skip backfilling entirely if run before February 1st.

### What's New

- Comment bodies now render as formatted markdown (bold, italic, links, lists, tables) instead of raw text, with clickable auto-linked URLs and Giphy embeds.
- Redesigned comment rows for better glanceability on mobile.
- Search syntax: exact phrases, required (+) and excluded (-) terms, author/flair filters, and score comparisons.
- Matched search terms are now highlighted inline in comment bodies, including in the expanded Context view.
- Relative dates now extend to a month, with a new week ("1w") granularity, instead of falling back to an absolute date after a week.
- Author Profiles: tap any username to see their comment count, total score, first/last seen dates, and recent comments, with a link to their Reddit profile.
- Block & Favorite Users and Saved Comments, synced across every browser and device.
- Saved Searches: save frequent search queries from a dropdown on the search bar, and rerun them with one tap, synced across every browser and device.
- Relative Dates, Hide Flairs, and Auto-collapse Threshold are also synced across every browser and device now, alongside the lists above.
- Auto/Light/Dark theme, following your device automatically when set to Auto.
- Added a container health check endpoint, surfacing healthy/unhealthy status in docker ps and tools like Portainer.
- Consistent structured logging across the app and scheduler.

### Bug Fixes

- Fixed the Auto-collapse Threshold input getting stuck and not actually disabling when cleared.
- Fixed the iOS home screen icon showing a transparent background instead of the app's icon.
- Added a setting to work around iOS 26+ covering the search bar with a status bar rendering effect when installed to your home screen as a progressive web app (PWA).
- Fixed mixed-content errors on HTTPS behind a reverse proxy by using relative static asset paths instead of url_for.
- Fixed search field keywords (author:, flair:, score:) breaking when mobile keyboards auto-capitalize them; also added user: as an alias for author:.
- Fixed multi-arch (amd64/arm64) Docker builds.
- Fixed the scheduler crashing with a traceback on transient Reddit API errors; it now logs once and keeps going.

## [v0.2.2](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/v0.2.2) (2026-08-28)

### What's New

- Optional `PUID`/`PGID` environment variables to run the container as a specific user/group, matching an existing host user. Default to `1000`, no change for existing setups.

### Bug Fixes

- Fixed a permissions bug where the container could fail to start with "unable to open database file" if the host's data directory wasn't owned by the expected user.

## [v0.2.1](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/v0.2.1) (2026-08-28)

### Bug Fixes

- Fixed a Python version pin in `Pipfile` that blocked the Docker build. v0.2.0's image never actually published to GHCR or Docker Hub because of it.

## [v0.2.0](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/v0.2.0) (2026-08-28)

The first release with a web UI.

### Upgrading

- Rename two environment variables: `THREAD_ACTIVE_CUTOFF_HOURS` to `THREAD_TTL_HOURS`, and `THREAD_REFRESH_RATE_MINUTES` to `SCHEDULER_INTERVAL_MINUTES`.

### What's New

- Mobile-first responsive interface with dark mode, full-width mode, and adjustable text size.
- Thread list with sort (New/Old/Top/Q&A) and Days Back filtering.
- Thread detail pages with a nested comment tree: collapse/expand, sort controls, date filtering.
- Search across all archived comments, with parent/child context expansion on results.
- Settings page for browser preferences (night mode, relative dates, auto-collapse threshold, rows per page).
- `/` keyboard shortcut to jump to search.
- Installable as a home-screen PWA (manifest and icons).
- Scheduler runs as its own container, separate from the web UI, and fetches new/active threads on a configurable interval.
- Docker entry point (`app.startup`) that optionally runs a backfill, then starts the scheduler.
- `BACKFILL_DATE` environment variable (`auto` or `YYYY-MM-DD`) to backfill missing threads on container start.
- Backfill CLI now takes a cutoff date directly.
- Timezone display via the `TZ` environment variable, applied across all timestamps.
- Multi-stage Dockerfile, non-root user, OCI image labels.
- `compose.yaml` with two independent services, `web` and `scheduler`, sharing the same image and data volume.
- GitHub Actions: build and publish to GHCR and Docker Hub on version tags, Compose stack integration test, lint, Dependabot.
- README rewritten with Quick Start, Tech Stack, environment variable reference, and screenshots.
- `CONTRIBUTING.md`, `ROADMAP.md`, `.env.example` added.

## [v0.1.0](https://github.com/wazam/r-fantasybaseball-indexer/releases/tag/v0.1.0) (2026-04-20)

First pre-release. Data pipeline is complete, no web UI yet.

### What's New

- Background scheduler fetches new threads, refreshes active ones, and marks old threads inactive on a set interval.
- Archives full comment trees including upvote scores, league flairs, and threaded reply structure.
- Tracks Reddit submission IDs to prevent storing duplicate threads and comments.
- Preserves deleted comments, updates edited ones, and keeps upvote and downvote scores current.
- Handles Reddit API rate limits with automatic retries.
- CLI backfill tool to import threads missed while the scheduler was offline.
- Refresh rate, thread activity window, and backfill start date are all configurable via `.env`.
- Archive is stored as a SQLite `.db` file and requires a compatible tool to browse.
