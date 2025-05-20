# r-fantasybaseball-indexer

A web app for fetching, storing, and searching comments from the Daily and Nightly “Anything Goes” threads on [r/fantasybaseball](https://www.reddit.com/r/fantasybaseball/).

## Features

- Archives Reddit comment threads (with upvote scores, league flairs, and replies)
- Supports keyword search across multiple days
- Avoids duplicate fetches (tracks which threads are already stored)
- Built with FastAPI, SQLAlchemy, and Pipenv
- Designed to run self-hosted (Docker support planned)

## License

This project is licensed under the [MIT License](LICENSE).

