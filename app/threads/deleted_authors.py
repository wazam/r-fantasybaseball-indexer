import logging

from sqlalchemy import text

from app.db import engine

logger = logging.getLogger(__name__)

# PRAGMA user_version 2: comments from deleted accounts, stored as "None" before v0.4.0,
# are relabeled "[deleted]" as Reddit shows them. Runs after the reply recount (version 1).
RELABELED_VERSION = 2


def relabel_deleted_authors_once():
    """Rename the "None" author to "[deleted]" in stored comments and the user lists, once per database."""
    with engine.begin() as conn:
        if conn.execute(text("PRAGMA user_version")).scalar() != RELABELED_VERSION - 1:
            return

        comments = conn.execute(text("UPDATE comments SET author = '[deleted]' WHERE author = 'None'")).rowcount
        # keep a block or favorite of "None", without a duplicate if "[deleted]" is already listed
        conn.execute(text(
            "INSERT OR IGNORE INTO list_items (list_name, item_value, created_at) "
            "SELECT list_name, '[deleted]', created_at FROM list_items "
            "WHERE item_value = 'None' AND list_name IN ('blocked_users', 'favorited_users')"
        ))
        lists = conn.execute(text(
            "DELETE FROM list_items WHERE item_value = 'None' AND list_name IN ('blocked_users', 'favorited_users')"
        )).rowcount
        conn.execute(text(f"PRAGMA user_version = {RELABELED_VERSION}"))

    logger.info(f"Relabeled deleted accounts: {comments} comment(s) and {lists} list entry(ies) from None to [deleted].")
