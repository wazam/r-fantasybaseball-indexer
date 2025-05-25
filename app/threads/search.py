from datetime import datetime, timedelta, UTC

from app.config import get_reddit_client, get_cutoff_hours, get_cutoff_date

reddit = get_reddit_client()

def is_valid_thread(title: str):
    title = title.lower()
    is_ag = "anything goes" in title
    is_freq = any(x in title for x in ["daily", "nightly", "weekly"])
    return is_ag and is_freq

def is_active_thread(posted_at: datetime) -> bool:
    cutoff_hours = get_cutoff_hours()
    return datetime.now(UTC) - posted_at < timedelta(hours=cutoff_hours)

def get_thread_urls(only_active=True):
    cutoff_date = get_cutoff_date()
    urls = []
    seen_ids = set()

    query = "Anything Goes Thread author:AutoModerator"
    subreddit = reddit.subreddit("fantasybaseball")

    for post in subreddit.search(query, sort="new", time_filter="year", limit=None):
        if not is_valid_thread(post.title):
            continue
        if post.created_utc < cutoff_date:
            continue

        posted_at = datetime.fromtimestamp(post.created_utc, UTC)
        if only_active and not is_active_thread(posted_at):
            continue

        if post.id in seen_ids:
            continue

        urls.append(post.url)
        seen_ids.add(post.id)

    return urls

# Run with: pipenv run python -m app.threads.search
if __name__ == "__main__":
    print("[SEARCH] Fetching recent 'Anything Goes' thread URLs...\n")
    urls = get_thread_urls()
    for url in urls:
        print(url)
    print(f"\n[DONE] Found {len(urls)} valid active thread URL(s).")
