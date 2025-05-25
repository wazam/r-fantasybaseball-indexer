# r-fantasybaseball-indexer

A web app for fetching, storing, and searching comments from the Daily and Nightly “Anything Goes” threads on [r/fantasybaseball](https://www.reddit.com/r/fantasybaseball/).

## Features

- Archives Reddit comment threads (with upvote scores, league flairs, and replies)
- Supports keyword search across multiple days
- Avoids duplicate fetches (tracks which threads are already stored)
- Built with FastAPI, SQLAlchemy, and Pipenv
- Designed to run self-hosted (Docker support planned)

## Set Up Reddit API Access

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **"Create App"** → choose **script**
3. Set:
   - Name: `r-fantasybaseball-indexer`
   - Redirect URI: `http://localhost`

4. Copy your:
   - `client_id` (under the app name)
   - `client_secret` (in the app details)

5. Create a `.env` file in your project root:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
```

## License

This project is licensed under the [MIT License](LICENSE).
