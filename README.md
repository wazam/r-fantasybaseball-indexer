# Anything Goes Archive

![Anything Goes Archive](docs/icon.png)

[![Docker](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/docker.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/docker.yml)
[![Test Docker Compose Stack](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/compose-test.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/compose-test.yml)
[![Lint](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/lint.yml/badge.svg)](https://github.com/wazam/r-fantasybaseball-indexer/actions/workflows/lint.yml)
[![Latest Release](https://img.shields.io/github/v/release/wazam/r-fantasybaseball-indexer?sort=semver)](https://github.com/wazam/r-fantasybaseball-indexer/releases)
[![Docker Image Size](https://img.shields.io/docker/image-size/ghcr.io/wazam/r-fantasybaseball-indexer/latest?label=image&logo=docker)](https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer)

Anything Goes Archive is a self-hosted tool that automatically archives every Daily and Nightly "Anything Goes" thread from [r/fantasybaseball](https://www.reddit.com/r/fantasybaseball/). Tens of thousands of comments are stored locally with upvote scores, league flairs, and full reply structure. Search across all threads at once to track player discussions over time, compare sentiment across multiple days side by side, and find exactly what you need without fighting Reddit's search.

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

- **Scheduler** -- automatically fetches newly posted threads, refreshes active ones, and marks old threads inactive on a configurable interval
- **Comment Archiving** -- stores full comment trees with upvote scores, league flairs, reply counts, and parent/child relationships for full thread reconstruction
- **Duplicate Prevention** -- tracks Reddit submission and comment IDs to avoid storing duplicates
- **Change Tracking** -- updates edited comment bodies and upvote scores on each refresh; preserves deleted and removed comments in the archive
- **Rate Limit Handling** -- retries automatically when Reddit API rate limits are hit
- **Backfill** -- CLI tool to import threads missed while the scheduler was offline
- **Web UI** -- mobile-friendly browser interface for browsing threads, searching comments, and filtering by date and sort order

## Tech Stack

- **Language:** Python 3.13, managed with Pipenv
- **Web Framework:** FastAPI with Jinja2 templating and uvicorn
- **Database:** SQLite via SQLAlchemy ORM
- **Reddit API:** PRAW
- **Scheduler:** APScheduler
- **Deployment:** Docker with Docker Compose

## Set Up Reddit API Access

All install methods require a Reddit API app. Create one at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps):

1. Click **"create another app..."**
2. Set the name to `Anything Goes Archive`, type to **script**, and redirect URI to `http://localhost`
3. Copy your `client_id` (shown under the app name) and `client_secret`

## Quick Start

> [!TIP]
> Run via Docker is recommended for most users. No clone or Python environment required.

### Run via Docker

The image is published to [GitHub Container Registry](https://github.com/wazam/r-fantasybaseball-indexer/pkgs/container/r-fantasybaseball-indexer) and [Docker Hub](https://hub.docker.com/r/wazam123/r-fantasybaseball-indexer).

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
     web:
       image: ghcr.io/wazam/r-fantasybaseball-indexer:latest
       ports:
         - "9009:9009"
       volumes:
         - ./data:/app/data
       environment:
         - TZ=UTC
       restart: unless-stopped

     scheduler:
       image: ghcr.io/wazam/r-fantasybaseball-indexer:latest
       volumes:
         - ./data:/app/data
       environment:
         - REDDIT_CLIENT_ID=        # Required - see Set Up Reddit API Access in README
         - REDDIT_CLIENT_SECRET=    # Required - see Set Up Reddit API Access in README
         # - THREAD_TTL_HOURS=24
         # - SCHEDULER_INTERVAL_MINUTES=60
       command: ["./.venv/bin/python", "-m", "app.scheduler"]
       restart: unless-stopped
   ```

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

   Imports threads missed while the scheduler was offline. Pass a `YYYY-MM-DD` cutoff date to set how far back to look. This may take a couple of hours for large date ranges.

   ```sh
   pipenv run python -m app.threads.backfill 2026-02-10
   ```

6. **Start the scheduler** (Terminal 1)

   ```sh
   pipenv run python -m app.scheduler
   ```

7. **Start the web UI** (Terminal 2)

   ```sh
   pipenv run uvicorn app.main:app --reload --host 0.0.0.0 --port 9009
   ```

   Then open [http://localhost:9009](http://localhost:9009) in your browser. The `--host 0.0.0.0` flag is required to reach the UI from other devices on your local network. Omit it for localhost-only access.

---

## Environment Variables

| Variable | Description | Required | Default |
| --- | --- | --- | --- |
| `REDDIT_CLIENT_ID` | Reddit app client ID. | Yes | |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret. | Yes | |
| `THREAD_TTL_HOURS` | Hours a thread stays active and continues to be refreshed before being archived. | No | `24` |
| `BACKFILL_DATE` | Backfill missing threads on container startup before the scheduler begins. Set to `auto` for Feb 1 of the current year, or a specific `YYYY-MM-DD` date. Leave unset to skip. | No | |
| `SCHEDULER_INTERVAL_MINUTES` | How often the scheduler runs. Each thread with 2,000-4,000 comments takes roughly 2-3 minutes to fetch, so values below 15 are not practical. | No | `60` |
| `TZ` | Timezone for displaying dates and times in the web UI. Accepts any [tz database identifier](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List). | No | `UTC` |

## Screenshots

![Thread list page showing archived Anything Goes threads](<docs/screenshot index.png>)

Thread list sorted by date with comment counts, scores, and Reddit links.

![Thread list on mobile device](<docs/screenshot mobile index.png>)

Home page on a mobile device.

![Thread detail page with nested comment tree](<docs/screenshot thread.png>)

Thread detail page with nested comment tree, sort controls, and date filter.

![Search results with inline parent and child comment context](<docs/screenshot search.png>)

Search page for a player with inline context for parent/child discussion.

![Search results in dark mode with full width layout](<docs/screenshot search dark mode wide.png>)

Search results in dark mode with the full width layout enabled.

![Search page on mobile in dark mode](<docs/screenshot mobile search dark mode.png>)

Search page in dark mode on a mobile device.

![All Comments page browsing the full archive](<docs/screenshot comments.png>)

All Comments view with no search term, browsing the full comment archive.

![Settings page with browser preferences](<docs/screenshot settings.png>)

Settings page with browser preferences for display and behavior options.

## Contributing

Report bugs or feature requests by opening an issue on the [GitHub repository](https://github.com/wazam/r-fantasybaseball-indexer/issues). See [ROADMAP.md](ROADMAP.md) for planned and proposed features. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting pull requests.

## Disclaimers

- [Reddit User Agreement](https://redditinc.com/policies/user-agreement)

## License

This project is licensed under the [MIT License](LICENSE).
