from datetime import datetime, timedelta, UTC
import logging

from prawcore.exceptions import PrawcoreException

from app.config import check_settings, get_reddit_client

logger = logging.getLogger(__name__)

# Every update looks for missing threads at least this far back
LOOKBACK_DAYS = 7


def is_valid_thread(title: str):
    title = title.lower()
    is_ag = "anything goes" in title
    is_freq = any(x in title for x in ["daily", "nightly", "weekly"])
    return is_ag and is_freq


def get_thread_urls(cutoff_date: float):
    """URLs of the Anything Goes threads posted since cutoff_date, a UTC timestamp, newest first. Reddit's search
    lists only its newest 250 results (about four months of threads), so it can't reach further back than that."""
    urls = []
    seen_ids = set()
    oldest = None

    query = "Anything Goes Thread"
    subreddit = get_reddit_client().subreddit("fantasybaseball")

    try:
        for post in subreddit.search(query, sort="new", time_filter="year", limit=None):
            # Newest first, so every later result is older too
            if post.created_utc < cutoff_date:
                break
            oldest = post.created_utc
            if not is_valid_thread(post.title) or post.id in seen_ids:
                continue

            urls.append(post.url)
            seen_ids.add(post.id)
        else:
            if oldest is not None:
                logger.warning(
                    f"Reddit's search reaches back only to {datetime.fromtimestamp(oldest, UTC):%Y-%m-%d}, so threads "
                    f"posted between {datetime.fromtimestamp(cutoff_date, UTC):%Y-%m-%d} and then can't be imported."
                )
    except PrawcoreException as e:
        logger.error(f"Couldn't search for threads: {e}")

    return urls


# Run with: docker exec anything-goes-archive ./.venv/bin/python -m app.threads.search
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
    check_settings()
    logger.info(f"Searching for 'Anything Goes' threads from the last {LOOKBACK_DAYS} days.")
    urls = get_thread_urls((datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).timestamp())
    logger.info(f"Found {len(urls)} thread URL(s).")
    for url in urls:
        logger.info(f"Found thread: {url}")
    logger.info("Thread search completed successfully.")
