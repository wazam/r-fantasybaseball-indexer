# Anything Goes Archive

[![Docker Publish](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/docker.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/docker.yml)
[![Compose Test](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/compose-test.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/compose-test.yml)
[![Python Lint](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/lint.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/lint.yml)
[![Latest Release](https://img.shields.io/github/v/release/wazam/r-fantasybaseball-indexer?sort=semver&label=Latest%20Release)](https://github.com/wazam/r-fantasybaseball-indexer/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/wazam123/r-fantasybaseball-indexer/latest?label=Image%20Size&logo=docker)](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer)
[![Docker Hub Pulls](https://img.shields.io/docker/pulls/wazam123/r-fantasybaseball-indexer?logo=docker&label=Docker%20Hub%20Pulls)](https://hub.docker.com/repository/docker/wazam123/r-fantasybaseball-indexer/general)
[![GHCR Pulls](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fwazam%2Fr-fantasybaseball-indexer%2Fr-fantasybaseball-indexer&query=downloadCountRaw&label=GHCR%20Pulls&logo=github)](https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer)

![Anything Goes Archive](docs/icon.png) **Anything Goes Archive** is a self-hosted tool that automatically archives every Daily and Nightly "Anything Goes" thread from [r/fantasybaseball](https://www.reddit.com/r/fantasybaseball/). Tens of thousands of comments are stored locally with upvote scores, league flairs, and full reply structure. Search across all threads at once to track player discussions over time, compare sentiment across multiple days side by side, and find exactly what you need without fighting Reddit's search.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Set Up Reddit API Access](#set-up-reddit-api-access)
- [Quick Start](#quick-start)
  - [Run via Docker](#run-via-docker)
  - [Build from Source](#build-from-source)
  - [Manual Install (Python)](#manual-install-python)
- [Environment Variables](#environment-variables)
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
- **Backfill**: import threads missed while the scheduler was offline, either via a CLI tool or automatically on startup with the `BACKFILL_DATE` environment variable

## Tech Stack

- **Language:** Python 3.13, managed with Pipenv
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
> Run via Docker is recommended for most users. No clone or Python environment required.

### Run via Docker

The image is published to [GitHub Container Registry](https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer) (`ghcr.io/wazam/r-fantasybaseball-indexer`) and [Docker Hub](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer) (`wazam123/r-fantasybaseball-indexer`).

1. **Create the data directory**

   ```sh
   mkdir data
   ```

2. **Download the compose file**

   ```sh
   curl -O https://raw.githubusercontent.com/wazam/r-fantasybaseball-indexer/main/compose.yaml
   ```

   The compose file looks like this. Fill in your Reddit credentials and adjust settings as needed:

   ```yaml
   services:
     app:
       image: ghcr.io/wazam/r-fantasybaseball-indexer:latest
       container_name: anything-goes-archive
       restart: unless-stopped
       environment:
         - REDDIT_CLIENT_ID= # REQUIRED, see README
         - REDDIT_CLIENT_SECRET= # REQUIRED, see README
         # - THREAD_TTL_HOURS=24
         # - SCHEDULER_INTERVAL_MINUTES=60
         # - BACKFILL_DATE= #YYYY-MM-DD
         # - TZ=UTC
         # - PUID=1000
         # - PGID=1000
       volumes:
         - ./data:/app/data
       ports:
         - 9009:9009
   ```

   The web UI and scheduler run together in a single container.

3. **Start the stack**

   ```sh
   docker compose up -d
   ```

4. **Open the web UI**

   Visit [http://localhost:9009](http://localhost:9009) in your browser.

---

### Build from Source

1. **Clone the repository**

   ```sh
   git clone https://github.com/wazam/r-fantasybaseball-indexer.git
   cd r-fantasybaseball-indexer
   ```

2. **Build and start the stack**

   With `compose.override.yaml` present, `docker compose build` uses the local source instead of pulling the registry image.

   ```sh
   docker compose build
   docker compose up -d
   ```

   Or build the image manually and use it directly:

   ```sh
   docker build -t ghcr.io/wazam/r-fantasybaseball-indexer:latest .
   docker compose up -d
   ```

3. **Open the web UI**

   Visit [http://localhost:9009](http://localhost:9009) in your browser.

---

### Manual Install (Python)

For running without Docker using a local Python environment.

1. **Clone the repository**

   ```sh
   git clone https://github.com/wazam/r-fantasybaseball-indexer.git
   cd r-fantasybaseball-indexer
   ```

2. **Create a .env file**

   Copy `.env.example` to `.env` and fill in your Reddit API credentials.

3. **Install Python environment with Pipenv**

   ```sh
   pipenv install
   ```

4. **Initialize the database**

   ```sh
   pipenv run python -m app.init
   ```

5. **Backfill missing threads (optional)**

   Imports threads missed while the scheduler was offline. Requires a `YYYY-MM-DD` cutoff date to set how far back to look. This may take a couple of hours for large date ranges.

   ```sh
   pipenv run python -m app.threads.backfill 2026-02-10
   ```

6. **Start the app**

   ```sh
   pipenv run uvicorn app.main:app --reload --host 0.0.0.0 --port 9009 --log-config app/logging_config.json
   ```

   The web UI and scheduler run together in the same process. Then open [http://localhost:9009](http://localhost:9009) in your browser.

> [!TIP]
> The `--host 0.0.0.0` flag is required to reach the UI from other devices on your local network. Omit it for localhost-only access.

---

## Environment Variables

| Variable | Description | Required | Default |
| --- | --- | --- | --- |
| `REDDIT_CLIENT_ID` | Reddit app client ID. | Yes | |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret. | Yes | |
| `THREAD_TTL_HOURS` | Hours a thread stays active and continues to be refreshed before being archived. | No | `24` |
| `BACKFILL_DATE` | Backfill missing threads on container startup before the scheduler begins. Set to a `YYYY-MM-DD` cutoff date. Leave unset to skip. | No | |
| `SCHEDULER_INTERVAL_MINUTES` | How often the scheduler runs. Each thread with 1,000-3,000 comments takes roughly 2-3 minutes to fetch, so values below 15 are not practical. | No | `60` |
| `TZ` | Timezone for displaying dates and times in the web UI. Accepts any [tz database identifier](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List). | No | `UTC` |
| `PUID` | User ID the container runs as. Set this to match the owner of your `./data` directory if it isn't the default. | No | `1000` |
| `PGID` | Group ID the container runs as. Set this to match the group that owns your `./data` directory if it isn't the default. | No | `1000` |

## Screenshots

![Thread list page showing archived Anything Goes threads](<docs/screenshot index.jpg>)

Thread list sorted by date, with comment counts, how recently each thread was active, and a link back to the original Reddit post.

![Thread detail page with a nested comment tree](<docs/screenshot thread.jpg>)

Thread detail page with a nested comment tree, sort controls, and a date filter.

![Search results with a matched term highlighted](<docs/screenshot search.jpg>)

Search results for a multi-term query, with matched words highlighted inline.

![Author profile popup showing stats and recent comments](<docs/screenshot user summary.jpg>)

Tapping any username opens their profile: total comments and score, first/last seen dates, and their recent comment history.

![Saved Comments page listing bookmarked comments](<docs/screenshot saved comments.jpg>)

Comments bookmarked with the save icon collect here for quick reference later.

![Thread page with full width layout and large text enabled](<docs/screenshot thread full width large text.jpg>)

Full width and Large text size, two of several display preferences available in Settings.

![Settings page with browser preferences, synced preferences, blocked and favorited users, and search syntax help](<docs/screenshot settings.jpg>)

Settings page: device-only display preferences, preferences synced across browsers, Blocked/Favorited Users management, and a Search Syntax reference.

![Thread detail page in dark mode](<docs/screenshot dark mode.jpg>)

Dark mode, available as a manual choice or set to follow your device automatically.

![Thread detail page on a mobile browser](<docs/screenshot mobile thread webbrowser.jpg>)

The mobile layout in a regular browser tab.

![Thread detail page installed as a home screen app on iOS, in dark mode](<docs/screenshot mobile thread pwa dark mode.jpg>)

Installed to the home screen as a PWA for an app-like experience, with an extra-tall header available in Settings to work around iOS's status bar effects.

## Contributing

Report bugs or feature requests by opening an issue on the [GitHub repository](https://github.com/wazam/r-fantasybaseball-indexer/issues). See [ROADMAP.md](ROADMAP.md) for planned and proposed features. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting pull requests.

## Disclaimers

- [Reddit User Agreement](https://redditinc.com/policies/user-agreement)

## License

This project is licensed under the [MIT License](LICENSE).
