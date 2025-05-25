from datetime import datetime, timedelta, UTC
from prawcore.exceptions import TooManyRequests
import time

from app.config import get_reddit_client, get_cutoff_hours
from app.db import SessionLocal
from app.models import Thread, Comment

reddit = get_reddit_client()

def fetch_and_store_thread(submission_url: str, assume_active: bool = True):
    session = SessionLocal()

    try:
        retries = 3
        delay = 15  # seconds between retries

        for attempt in range(1, retries + 1):
            try:
                submission = reddit.submission(url=submission_url)
                submission.comments.replace_more(limit=None)
                all_comments = submission.comments.list()
                break  # success
            except TooManyRequests as e:
                if attempt < retries:
                    print(f"[ERROR] 429 TooManyRequests — retrying in {delay}s (attempt {attempt}/{retries})...")
                    time.sleep(delay)
                else:
                    print(f"[ERROR] Thread failed after {retries} retries: {submission_url}")
                    session.rollback()
                    session.close()
                    return
            except Exception as e:
                print("[ERROR] Can't retrieve submission:", e)
                session.rollback()
                session.close()
                return

        reddit_id = submission.id
        existing_thread = session.query(Thread).filter_by(reddit_id=reddit_id).first()
        if existing_thread and not existing_thread.is_active:
            print("[DONE] Thread already archived:", existing_thread.title)
            return

        print(f"[INFO] Storing thread: {submission.title}")

        def is_active_thread(posted_at: datetime) -> bool:
            cutoff_hours = get_cutoff_hours()
            return datetime.now(UTC) - posted_at < timedelta(hours=cutoff_hours)

        # Set posted_at as timezone-aware UTC datetime
        posted_at = datetime.fromtimestamp(submission.created_utc, UTC)
        active = is_active_thread(posted_at)

        # Create or update the Thread
        if not existing_thread:
            thread = Thread(
                reddit_id=reddit_id,
                title=submission.title,
                permalink=submission_url,
                score=submission.score,
                posted_at=posted_at,
                comment_count=len(all_comments),
                is_active=active
            )
            session.add(thread)
            session.commit()
        else:
            # Update existing thread
            if existing_thread.is_active:
                existing_thread.score = submission.score
                existing_thread.comment_count = len(all_comments)
                existing_thread.last_saved = datetime.now(UTC)
                existing_thread.is_active = active  # turn off if expired
                session.commit()
                thread = existing_thread
            else:
                print("[DONE] Thread is archived, skipping update.")
                return

        # Build reply tree index
        replies_map = {}  # comment.id -> list of its direct replies
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
                # Skip update if the new body or author is [deleted]
                if body == "[deleted]" or author == "[deleted]":
                    continue

                # Update if the body was edited
                if body != existing_comment.body:
                    existing_comment.body = body

                # Always update score and last_saved if not deleted
                existing_comment.score = c.score
                existing_comment.last_saved = datetime.now(UTC)
                continue

            # If it's a new comment (even if deleted), store it anyway
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
        print(f"[DONE] Stored {len(all_comments)} comments.")

    except Exception as e:
        session.rollback()
        print("[ERROR] Could not store thread:", e)

    finally:
        session.close()

# Run with: pipenv run python -m app.reddit
if __name__ == "__main__":
    print("[REDDIT] Standalone thread fetcher active.")
    print("[REDDIT] Starting test import using hardcoded URL...")

    test_url = "https://www.reddit.com/r/fantasybaseball/comments/1ksagtd/nightly_anything_goes_thread_21_may_2025/"
    print(f"[INPUT] Target URL: {test_url}")

    try:
        fetch_and_store_thread(test_url)
        print("[REDDIT] Thread fetch completed successfully.")
    except Exception as e:
        print(f"[ERROR] Unhandled exception during fetch: {e}")
