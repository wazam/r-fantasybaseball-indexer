from datetime import datetime, timedelta, UTC
from prawcore.exceptions import TooManyRequests
import logging
import time

from app.config import get_reddit_client, get_active_hours
from app.db import SessionLocal
from app.models import Thread, Comment

logger = logging.getLogger(__name__)

reddit = get_reddit_client()

def fetch_and_store_thread(submission_url: str):
    session = SessionLocal()

    try:
        retries = 3
        delay = 15  # seconds

        for attempt in range(1, retries + 1):
            try:
                submission = reddit.submission(url=submission_url)
                submission.comments.replace_more(limit=None)
                all_comments = submission.comments.list()
                break  # success
            except TooManyRequests as e:
                if attempt < retries:
                    logger.warning(f"429 TooManyRequests — retrying in {delay}s (attempt {attempt}/{retries})...")
                    time.sleep(delay)
                else:
                    logger.error(f"Thread failed after {retries} retries: {submission_url}")
                    session.rollback()
                    session.close()
                    return
            except Exception as e:
                logger.error(f"Couldn't fetch thread: {e}")
                session.rollback()
                session.close()
                return

        reddit_id = submission.id
        existing_thread = session.query(Thread).filter_by(reddit_id=reddit_id).first()
        if existing_thread and not existing_thread.is_active:
            logger.info(f"Skipping already archived thread: {existing_thread.title}")
            return

        logger.info(f"Storing thread: {submission.title}")

        def is_active_thread(posted_at: datetime) -> bool:
            hours = get_active_hours()
            return datetime.now(UTC) - posted_at < timedelta(hours=hours)

        posted_at = datetime.fromtimestamp(submission.created_utc, UTC)
        active_status = is_active_thread(posted_at)

        if not existing_thread:
            thread = Thread(
                reddit_id=reddit_id,
                title=submission.title,
                permalink=submission_url,
                score=submission.score,
                posted_at=posted_at,
                comment_count=len(all_comments),
                is_active=active_status
            )
            session.add(thread)
            session.commit()
        else:
            # Update existing thread
            if existing_thread.is_active:
                existing_thread.score = submission.score
                existing_thread.comment_count = len(all_comments)
                existing_thread.last_saved = datetime.now(UTC)
                existing_thread.is_active = active_status
                session.commit()
                thread = existing_thread
            else:
                logger.info("Skipping update for inactive thread.")
                return

        replies_map = {}
        for c in all_comments:
            parent = c.parent_id.split("_")[-1] if c.parent_id.startswith("t1_") else None
            if parent:
                replies_map.setdefault(parent, []).append(c.id)

        def count_all_descendants(cid):
            count = 0
            stack = replies_map.get(cid, [])
            while stack:
                child = stack.pop()
                count += 1
                stack.extend(replies_map.get(child, []))
            return count

        for c in all_comments:
            cid = c.id
            author = str(c.author)
            body = c.body

            existing_comment = session.query(Comment).filter_by(id=cid).first()

            if existing_comment:
                if body == "[deleted]" or body == "[removed]" or author == "[deleted]":
                    continue

                if body != existing_comment.body:
                    existing_comment.body = body

                existing_comment.score = c.score
                existing_comment.last_saved = datetime.now(UTC)
                continue

            comment = Comment(
                id=cid,
                thread_id=thread.id,
                parent_id=c.parent_id.split("_")[-1] if c.parent_id.startswith("t1_") else None,
                body=body,
                author=author,
                flair=c.author_flair_text,
                score=c.score,
                created_utc=datetime.fromtimestamp(c.created_utc, UTC),
                permalink=f"https://www.reddit.com{c.permalink}",
                replies_direct=len(replies_map.get(cid, [])),
                replies_all=count_all_descendants(cid)
            )
            session.add(comment)

        session.commit()
        logger.info(f"Stored {len(all_comments)} comments.")

    except Exception as e:
        session.rollback()
        logger.error(f"Could not store thread: {e}")

    finally:
        session.close()

# Run with: pipenv run python -m app.reddit
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
    logger.info("Standalone thread fetcher using hardcoded URL.")

    valid_url = "https://www.reddit.com/r/fantasybaseball/comments/1s6t89c/daily_anything_goes_thread_march_29_2026/"
    logger.info(f"Target URL: {valid_url}")

    try:
        fetch_and_store_thread(valid_url)
        logger.info("Thread fetch completed successfully.")
    except Exception as e:
        logger.error(f"Unhandled exception during fetch: {e}")
