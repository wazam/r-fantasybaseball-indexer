import logging

from sqlalchemy import text

from app.db import engine

logger = logging.getLogger(__name__)

# PRAGMA user_version is 0 in databases from before v0.4.0, whose reply counts stopped
# updating after each comment's first save, and 1 once they've been recounted.
RECOUNTED_VERSION = 1


def recount_replies_once():
    """Recount every stored comment's replies from the archive, once per database."""
    with engine.begin() as conn:
        if conn.execute(text("PRAGMA user_version")).scalar() >= RECOUNTED_VERSION:
            return

        rows = conn.execute(text("SELECT id, parent_id, replies_direct, replies_all FROM comments")).all()
        children = {}
        for cid, parent_id, _, _ in rows:
            if parent_id:
                children.setdefault(parent_id, []).append(cid)
        totals = _descendant_counts(children)

        updates = [
            {"id": cid, "direct": len(children.get(cid, [])), "total": totals.get(cid, 0)}
            for cid, _, direct, total in rows
            if (direct, total) != (len(children.get(cid, [])), totals.get(cid, 0))
        ]
        if updates:
            conn.execute(
                text("UPDATE comments SET replies_direct = :direct, replies_all = :total WHERE id = :id"), updates
            )
        conn.execute(text(f"PRAGMA user_version = {RECOUNTED_VERSION}"))

    logger.info(f"Recounted replies: corrected {len(updates)} of {len(rows)} stored comments.")


def _descendant_counts(children):
    """All descendants of each comment that has replies, walking the tree without recursion."""
    totals = {}
    for root in children:
        if root in totals:
            continue
        stack = [(root, False)]
        while stack:
            cid, kids_done = stack.pop()
            if kids_done:
                totals[cid] = sum(1 + totals.get(kid, 0) for kid in children[cid])
            elif cid not in totals:
                stack.append((cid, True))
                stack.extend((kid, False) for kid in children[cid] if kid in children and kid not in totals)
    return totals
