# Anything Goes Archive

[![Docker Publish](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/docker.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/docker.yml)
[![Compose Test](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/compose-test.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/compose-test.yml)
[![Python Lint](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/lint.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/lint.yml)
[![Latest Release](https://img.shields.io/github/v/release/wazam/r-fantasybaseball-indexer?sort=semver&label=Latest%20Release)](https://github.com/wazam/r-fantasybaseball-indexer/releases)
[![Image Size](https://img.shields.io/docker/image-size/wazam123/r-fantasybaseball-indexer/latest?label=Image%20Size&logo=docker)](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer)
[![Docker Hub Pulls](https://img.shields.io/docker/pulls/wazam123/r-fantasybaseball-indexer?logo=docker&label=Docker%20Hub%20Pulls)](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer)
[![GHCR Pulls](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fwazam%2Fr-fantasybaseball-indexer%2Fr-fantasybaseball-indexer&query=downloadCountRaw&label=GHCR%20Pulls&logo=github)](https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer)

![Anything Goes Archive](docs/icon.png) **Anything Goes Archive** is a self-hosted tool that automatically archives every Daily and Nightly "Anything Goes" thread from [r/fantasybaseball](https://www.reddit.com/r/fantasybaseball/). Tens of thousands of comments are stored locally with upvote scores, league flairs, and full reply structure. Search across all threads at once to track player discussions over time, compare sentiment across multiple days side by side, and find exactly what you need without fighting Reddit's search.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Set Up Reddit API Access](#set-up-reddit-api-access)
- [Quick Start](#quick-start)
  - [Run via Docker Compose](#run-via-docker-compose)
  - [Build from Source](#build-from-source)
- [Environment Variables](#environment-variables)
- [Your Data](#your-data)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [Disclaimers](#disclaimers)
- [License](#license)

## Features

- **Web UI**: mobile-friendly browser interface for browsing threads and comment trees, with sort, pagination, collapse/expand, and auto-collapse by score
- **Search**: syntax-aware search across the full archive, supporting exact phrases, required (+) and excluded (-) terms, author/flair filters, and score comparisons, with matched terms highlighted inline
- **Author Profiles**: tap any username to see their comment count, total score, first/last seen dates, and recent comment history
- **Block & Favorite Users**: hide unwanted commenters or highlight ones you follow, synced across every browser and device
- **Saved Comments & Saved Searches**: bookmark comments and save frequent search queries for one-tap access later
- **Theming & Display Preferences**: light, dark, or auto theme, adjustable text size, and a full-width layout option
- **Installable Web App**: add to your phone's home screen for an app-like experience
- **Scheduler**: automatically fetches newly posted threads, refreshes active ones, and marks old threads inactive on a configurable interval
- **Comment Archiving**: stores full comment trees with upvote scores, league flairs, reply counts, and parent/child relationships for full thread reconstruction
- **Duplicate Prevention**: tracks Reddit submission and comment IDs to avoid storing duplicates
- **Change Tracking**: updates edited comment bodies and upvote scores on each refresh; preserves deleted and removed comments in the archive
- **Rate Limit Handling**: retries automatically when Reddit API rate limits are hit
- **Backfill**: import threads missed while the scheduler was offline, automatically on startup with the `BACKFILL_DATE` environment variable, or once with `docker exec anything-goes-archive ./.venv/bin/python -m app.threads.backfill YYYY-MM-DD`

## Tech Stack

- **Language:** Python 3.14, managed with Pipenv
- **Web Framework:** FastAPI with Jinja2 templating and uvicorn
- **Database:** SQLite via SQLAlchemy ORM
- **Reddit API:** PRAW
- **Scheduler:** APScheduler
- **Deployment:** Docker with Docker Compose

## Set Up Reddit API Access

All install methods require a Reddit API app.

> [!WARNING]
> Reddit closed self-service API access starting November 2025 under its new [Responsible Builder Policy](https://www.reddit.com/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/). New apps now require approval, which tends to go unanswered for small hobby projects like this one. If you already have Reddit API credentials, they still work fine.

If you do have access, create an app at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps):

1. Click **"create another app..."**
2. Set the name to `Anything Goes Archive`, type to **script**, and redirect URI to `http://localhost`
3. Copy your `client_id` (shown under the app name) and `client_secret`

## Quick Start

> [!TIP]
> Run via Docker Compose is recommended for most users. No clone or Python environment required.

### Run via Docker Compose

The image is published to [GitHub Container Registry](https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer) (`ghcr.io/wazam/r-fantasybaseball-indexer`) and [Docker Hub](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer) (`wazam123/r-fantasybaseball-indexer`). This is the `compose.yaml` to use:

```yaml
services:
  anything-goes-archive:
    image: ghcr.io/wazam/r-fantasybaseball-indexer:latest
    container_name: anything-goes-archive
    restart: unless-stopped
    user: "1000:1000"
    environment:
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}  # required
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}  # required
      - REDDIT_USER_AGENT=${REDDIT_USER_AGENT:-}  # optional
      - THREAD_TTL_HOURS=${THREAD_TTL_HOURS:-24}  # optional
      - SCHEDULER_INTERVAL_MINUTES=${SCHEDULER_INTERVAL_MINUTES:-60}  # optional
      - BACKFILL_DATE=${BACKFILL_DATE:-}  # optional
      - TZ=${TZ:-UTC}  # optional
      - FORWARDED_ALLOW_IPS=${FORWARDED_ALLOW_IPS:-127.0.0.1,::1}  # optional
    volumes:
      - ./data:/app/data
    ports:
      - "9009:9009"
```

The container runs as user `1000:1000` and can only write to `./data` if that user owns it. Check the owner with `ls -nd data`. If it shows different numbers, set `user:` to match, for example `user: "1001:1001"`, or change the owner with `sudo chown -R 1000:1000 data`.

1. **Create the data directory**

   ```sh
   mkdir data
   ```

2. **Download the compose file**

   ```sh
   curl -O https://raw.githubusercontent.com/wazam/r-fantasybaseball-indexer/main/compose.yaml
   ```

3. **Create `.env`**

   Next to `compose.yaml`, create a `.env` file with these two lines, filled in with your Reddit app's client ID and secret (see [Set Up Reddit API Access](#set-up-reddit-api-access)). Add any optional setting you want to change the same way, one `NAME=value` per line.

   ```sh
   REDDIT_CLIENT_ID=
   REDDIT_CLIENT_SECRET=
   ```

   Without the two credentials, or with ones Reddit rejects, the app exits at startup with an error in `docker compose logs`.

4. **Start the stack**

   ```sh
   docker compose up -d
   ```

5. **Open the web UI**

   Visit [http://localhost:9009](http://localhost:9009) in your browser.

---

### Build from Source

1. **Clone the repository**

   ```sh
   git clone https://github.com/wazam/r-fantasybaseball-indexer.git
   cd r-fantasybaseball-indexer
   ```

2. **Create a .env file**

   In the repo folder, create `.env` with your Reddit API credentials, as in step 3 of [Run via Docker Compose](#run-via-docker-compose).

3. **Build and start the stack**

   ```sh
   docker compose up -d --build
   ```

   Inside the repo, `docker compose` also loads `compose.override.yaml`, which builds the image from source as `r-fantasybaseball-indexer:local`, so it never overwrites the published image. To run the published image from the repo folder instead, use `docker compose -f compose.yaml up -d`.

4. **Open the web UI**

   Visit [http://localhost:9009](http://localhost:9009) in your browser.

---

## Environment Variables

Set these in a `.env` file next to `compose.yaml`, one `NAME=value` per line. `compose.yaml` passes each one you set to the container, and any you leave unset or empty keep the defaults below. A value the app can't use, such as a number out of range, a malformed date or credentials Reddit rejects, stops it at startup with the reason in `docker compose logs`.

| Variable | Description | Required | Default |
| --- | --- | --- | --- |
| `REDDIT_CLIENT_ID` | Reddit app client ID, the string under the app name at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (see [Set Up Reddit API Access](#set-up-reddit-api-access)). | Yes | |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret, the "secret" field at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps). | Yes | |
| `REDDIT_USER_AGENT` | User agent sent to Reddit's API. Reddit asks each app to identify itself with its own username, in the form `platform:app:version (by /u/your_username)`. Leave unset to use the built-in one, `linux:r-fantasybaseball-indexer:v<version> (by /u/wazam)`, which names this project's author. | No | |
| `THREAD_TTL_HOURS` | Hours a thread stays active and continues to be refreshed before being archived. A whole number from 1 to 8760 (a year). | No | `24` |
| `BACKFILL_DATE` | Backfill missing threads on container startup before the scheduler begins. Set to a `YYYY-MM-DD` cutoff date. Leave unset to skip. | No | |
| `SCHEDULER_INTERVAL_MINUTES` | Minutes between scheduler runs, a whole number from 1 to 1440 (a day). Each thread with 1,000 to 3,000 comments takes roughly 2 to 3 minutes to fetch, so values below 15 are not practical. | No | `60` |
| `TZ` | Time zone for the web UI's dates and the timestamps in the container's logs. Accepts a canonical [tz database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) such as `America/New_York`; legacy names such as `US/Eastern` and `EST5EDT` aren't in the image. An unknown one logs a warning and uses UTC. | No | `UTC` |
| `FORWARDED_ALLOW_IPS` | Reverse proxy IPs to trust for `X-Forwarded-For` and `X-Forwarded-Proto` headers, comma-separated, with CIDR ranges allowed (`10.0.0.0/24`, not `10.0.0.5/24`). Behind a reverse proxy, set this to the proxy's address as the container sees it, so the access log shows real client IPs and redirects keep `https://`: the proxy container's address on a shared Docker network, or the network's gateway (from `docker network inspect`) when the proxy runs on the host. Use `*` only if nothing but the proxy can reach port 9009. A value that isn't `*` or a list of IP addresses and ranges stops the app at startup. | No | `127.0.0.1,::1` |

> [!TIP]
> Other devices on your network can reach the archive at `http://<host-ip>:9009`, where `<host-ip>` is the address of the machine running Docker.
>
> If a reverse proxy runs on the same machine, publish the port on loopback only (`"127.0.0.1:9009:9009"` under `ports:`), so other devices can't go around the proxy.
>
> Do not put this on the Internet if you do not know what you are doing.

## Your Data

Everything the app stores is in one SQLite file, `./data/data.db`: the archived threads and comments, plus your blocked and favorited users, saved comments, saved searches and synced preferences. Browser preferences (theme, text size, full width, rows per page, taller header) stay in each browser. Threads from February to early November 2026 (about 415,000 comments) take about 200 MB.

- **Ownership:** the container runs as uid 1000 and needs to write to `./data` (see [Run via Docker Compose](#run-via-docker-compose)).
- **Backups:** stop the container, then copy `data.db`. A copy taken while the app is writing can be incomplete.
- **Moving or starting over:** put `data.db` in the new host's `./data` folder, or delete it to start fresh. The tables are created on startup.

## Screenshots

<img src="docs/screenshot index.jpg" width="480" alt="Thread list page showing archived Anything Goes threads">

Thread list sorted by date, with comment counts, how recently each thread was active, and a link back to the original Reddit post.

<img src="docs/screenshot thread.jpg" width="480" alt="Thread detail page with a nested comment tree">

Thread detail page with a nested comment tree, sort controls, and a date filter.

<img src="docs/screenshot search.jpg" width="480" alt="Search results with a matched term highlighted">

Search results for a multi-term query, with matched words highlighted inline.

<img src="docs/screenshot user summary.jpg" width="480" alt="Author profile popup showing stats and recent comments">

Tapping any username opens their profile: total comments and score, first/last seen dates, and their recent comment history.

<img src="docs/screenshot saved comments.jpg" width="480" alt="Saved Comments page listing bookmarked comments">

Comments bookmarked with the save icon collect here for quick reference later.

<img src="docs/screenshot thread full width large text.jpg" width="480" alt="Thread page with full width layout and large text enabled">

Full width and Large text size, two of several display preferences available in Settings.

<img src="docs/screenshot settings.jpg" width="480" alt="Settings page with browser preferences, synced preferences, blocked and favorited users, and search syntax help">

Settings page: device-only display preferences, preferences synced across browsers, Blocked/Favorited Users management, and a Search Syntax reference.

<img src="docs/screenshot dark mode.jpg" width="480" alt="Thread detail page in dark mode">

Dark mode, available as a manual choice or set to follow your device automatically.

<img src="docs/screenshot mobile thread webbrowser.jpg" width="320" alt="Thread detail page on a mobile browser">

The mobile layout in a regular browser tab.

<img src="docs/screenshot mobile thread pwa dark mode.jpg" width="320" alt="Thread detail page installed as a home screen app on iOS, in dark mode">

Installed to the home screen as a PWA for an app-like experience, with an extra-tall header available in Settings to work around iOS's status bar effects.

## Contributing

Report bugs or feature requests by opening an issue on the [GitHub repository](https://github.com/wazam/r-fantasybaseball-indexer/issues). See [CHANGELOG.md](CHANGELOG.md) for what changed in each release, [ROADMAP.md](ROADMAP.md) for planned and proposed features, and [RELEASING.md](RELEASING.md) for how a release is made.

## Disclaimers

- [Reddit User Agreement](https://redditinc.com/policies/user-agreement)

## License

This project is licensed under the [MIT License](LICENSE).
