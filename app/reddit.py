from datetime import datetime, timedelta, UTC
from prawcore.exceptions import TooManyRequests
import logging
import time

from app.config import check_settings, get_reddit_client, get_active_hours
from app.db import SessionLocal, check_data_folder
from app.models import Thread, Comment

logger = logging.getLogger(__name__)

FETCH_RETRIES = 3
RETRY_DELAY_SECONDS = 15


def fetch_and_store_thread(submission_url: str):
    fetched = _fetch_submission(submission_url)
    if fetched is None:
        return
    submission, all_comments = fetched

    with SessionLocal() as session:
        try:
            thread = _store_thread(session, submission, submission_url, len(all_comments))
            if thread is None:
                return
            _store_comments(session, thread, all_comments)
            session.commit()
            logger.info(f"Stored {len(all_comments)} comments.")
        except Exception as e:
            session.rollback()
            logger.error(f"Could not store thread: {e}")


def _fetch_submission(submission_url: str):
    """Fetch a thread and its full comment list, retrying when Reddit rate limits. None if it fails."""
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            submission = get_reddit_client().submission(url=submission_url)
            submission.comments.replace_more(limit=None)
            return submission, submission.comments.list()
        except TooManyRequests:
            if attempt < FETCH_RETRIES:
                logger.warning(
                    f"429 TooManyRequests, retrying in {RETRY_DELAY_SECONDS}s (attempt {attempt}/{FETCH_RETRIES})..."
                )
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                logger.error(f"Thread failed after {FETCH_RETRIES} retries: {submission_url}")
        except Exception as e:
            logger.error(f"Couldn't fetch thread: {e}")
            return None
    return None


def _store_thread(session, submission, submission_url: str, comment_count: int):
    """Add or update the thread's row and commit it. None if the thread is already archived."""
    existing = session.query(Thread).filter_by(reddit_id=submission.id).first()
    if existing and not existing.is_active:
        logger.info(f"Skipping already archived thread: {existing.title}")
        return None

    logger.info(f"Storing thread: {submission.title}")

    posted_at = datetime.fromtimestamp(submission.created_utc, UTC)
    is_active = datetime.now(UTC) - posted_at < timedelta(hours=get_active_hours())

    if existing:
        existing.score = submission.score
        existing.comment_count = comment_count
        existing.last_saved = datetime.now(UTC)
        existing.is_active = is_active
        thread = existing
    else:
        thread = Thread(
            reddit_id=submission.id,
            title=submission.title,
            permalink=submission_url,
            score=submission.score,
            posted_at=posted_at,
            comment_count=comment_count,
            is_active=is_active
        )
        session.add(thread)
    session.commit()
    return thread


def _store_comments(session, thread: Thread, all_comments):
    """Add new comments and update stored ones. Deleted and removed comments keep their archived text."""
    replies_direct, replies_all = _reply_counts(all_comments)

    for c in all_comments:
        author = c.author.name if c.author else "[deleted]"  # PRAW gives None for a deleted account
        body = c.body
        existing = session.query(Comment).filter_by(id=c.id).first()

        if existing:
            existing.replies_direct = replies_direct.get(c.id, 0)  # counts change as replies arrive
            existing.replies_all = replies_all.get(c.id, 0)
            if body in ("[deleted]", "[removed]"):
                continue
            existing.body = body
            existing.score = c.score
            existing.last_saved = datetime.now(UTC)
            continue

        session.add(Comment(
            id=c.id,
            thread_id=thread.id,
            parent_id=_parent_id(c),
            body=body,
            author=author,
            flair=c.author_flair_text,
            score=c.score,
            created_utc=datetime.fromtimestamp(c.created_utc, UTC),
            permalink=f"https://www.reddit.com{c.permalink}",
            replies_direct=replies_direct.get(c.id, 0),
            replies_all=replies_all.get(c.id, 0)
        ))


def _parent_id(comment):
    """The parent comment's id, or None for a top-level comment (whose parent is the thread)."""
    return comment.parent_id.split("_")[-1] if comment.parent_id.startswith("t1_") else None


def _reply_counts(all_comments):
    """Direct and total (all descendants) reply counts per comment id, from this fetch's comments."""
    children = {}
    for c in all_comments:
        parent = _parent_id(c)
        if parent:
            children.setdefault(parent, []).append(c.id)

    def descendants(cid):
        count = 0
        stack = list(children.get(cid, []))
        while stack:
            count += 1
            stack.extend(children.get(stack.pop(), []))
        return count

    return {cid: len(kids) for cid, kids in children.items()}, {cid: descendants(cid) for cid in children}


# Run with: docker exec anything-goes-archive ./.venv/bin/python -m app.reddit
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
    check_settings()
    check_data_folder()
    logger.info("Standalone thread fetcher using hardcoded URL.")

    valid_url = "https://www.reddit.com/r/fantasybaseball/comments/1s6t89c/daily_anything_goes_thread_march_29_2026/"
    logger.info(f"Target URL: {valid_url}")

    try:
        fetch_and_store_thread(valid_url)
        logger.info("Thread fetch completed successfully.")
    except Exception as e:
        logger.error(f"Unhandled exception during fetch: {e}")
