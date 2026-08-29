import math
import os
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db import SessionLocal
from app.models import Comment, Thread
from app.web.markdown_render import render_markdown
from app.web.search_query import apply_search_filters, parse_search_query

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def _localdt(dt, fmt="%b %-d, %-I:%M %p"):
    try:
        tz = ZoneInfo(os.getenv("TZ", "UTC"))
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return dt.replace(tzinfo=UTC).astimezone(tz).strftime(fmt)


templates.env.filters["localdt"] = _localdt
templates.env.filters["render_markdown"] = render_markdown


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_comment_tree(comments, sort_by: str = "new"):
    children = {}
    roots = []
    comment_map = {c.id: c for c in comments}

    for c in comments:
        if c.parent_id is None:
            roots.append(c)
        else:
            children.setdefault(c.parent_id, []).append(c)

    if sort_by == "top":
        def max_subtree_score(cid):
            score = comment_map[cid].score
            stack = list(children.get(cid, []))
            while stack:
                child = stack.pop()
                score = max(score, child.score)
                stack.extend(children.get(child.id, []))
            return score

        roots.sort(key=lambda c: max_subtree_score(c.id), reverse=True)
        for parent_id in children:
            children[parent_id].sort(key=lambda c: c.score, reverse=True)

    elif sort_by == "new":
        roots.sort(key=lambda c: c.created_utc, reverse=True)
        for parent_id in children:
            children[parent_id].sort(key=lambda c: c.created_utc, reverse=True)

    elif sort_by == "qa":
        roots.sort(key=lambda c: c.replies_all, reverse=True)
        for parent_id in children:
            children[parent_id].sort(key=lambda c: c.replies_all, reverse=True)

    result = []
    stack = [(c, 0) for c in reversed(roots)]
    while stack:
        node, depth = stack.pop()
        result.append({"comment": node, "depth": depth})
        for child in reversed(children.get(node.id, [])):
            stack.append((child, depth + 1))
    return result


def get_pagination(total: int, page: int, per_page: int) -> dict:
    if per_page == 0:
        total_pages = 1
        page = 1
    else:
        total_pages = max(1, math.ceil(total / per_page))
        page = max(1, min(page, total_pages))

    def page_range(current, total_p):
        if total_p <= 5:
            return list(range(1, total_p + 1))
        shown = set()
        shown.add(1)
        shown.add(total_p)
        shown.update(range(max(1, current - 1), min(total_p, current + 1) + 1))
        result = []
        prev = 0
        for p in sorted(shown):
            if p - prev > 1:
                result.append(None)
            result.append(p)
            prev = p
        return result

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "pages": page_range(page, total_pages),
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def get_cutoff(days_back: int):
    if days_back <= 0:
        return None
    return datetime.now(UTC) - timedelta(days=days_back)


@router.get("/", response_class=HTMLResponse)
def index(request: Request, page: int = 1, per_page: int = 100, days_back: int = 0, sort_by: str = "new", db: Session = Depends(get_db)):
    if sort_by not in ("old", "new", "top", "qa"):
        sort_by = "new"
    if sort_by == "old":
        query = db.query(Thread).order_by(Thread.posted_at.asc())
    elif sort_by == "top":
        query = db.query(Thread).order_by(Thread.score.desc())
    elif sort_by == "qa":
        query = db.query(Thread).order_by(Thread.comment_count.desc())
    else:
        query = db.query(Thread).order_by(Thread.posted_at.desc())
    cutoff = get_cutoff(days_back)
    if cutoff:
        query = query.filter(Thread.posted_at >= cutoff)
    total = query.count()
    pag = get_pagination(total, page, per_page)
    if pag["per_page"] > 0:
        query = query.offset((pag["page"] - 1) * pag["per_page"]).limit(pag["per_page"])
    threads = query.all()
    return templates.TemplateResponse(request, "index.html", {"threads": threads, "pag": pag, "days_back": days_back, "sort_by": sort_by})


@router.get("/threads/{thread_id}", response_class=HTMLResponse)
def thread_detail(thread_id: int, request: Request, page: int = 1, per_page: int = 100, days_back: int = 0, sort_by: str = "new", db: Session = Depends(get_db)):
    if sort_by not in ("old", "new", "top", "qa"):
        sort_by = "new"
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    comment_query = db.query(Comment).filter(Comment.thread_id == thread_id)
    cutoff = get_cutoff(days_back)
    if cutoff:
        comment_query = comment_query.filter(Comment.created_utc >= cutoff)
    comments = comment_query.order_by(Comment.created_utc).all()
    all_nodes = build_comment_tree(comments, sort_by=sort_by)
    pag = get_pagination(len(all_nodes), page, per_page)
    if pag["per_page"] > 0:
        start = (pag["page"] - 1) * pag["per_page"]
        comment_tree = all_nodes[start: start + pag["per_page"]]
    else:
        comment_tree = all_nodes
    return templates.TemplateResponse(request, "thread.html", {"thread": thread, "comment_tree": comment_tree, "pag": pag, "days_back": days_back, "sort_by": sort_by})


@router.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = "", page: int = 1, per_page: int = 100, days_back: int = 0, sort_by: str = "new", db: Session = Depends(get_db)):
    if sort_by not in ("old", "new", "top", "qa"):
        sort_by = "new"
    base_query = db.query(Comment, Thread).join(Thread, Comment.thread_id == Thread.id)
    if q:
        base_query = apply_search_filters(base_query, parse_search_query(q))
    cutoff = get_cutoff(days_back)
    if cutoff:
        base_query = base_query.filter(Comment.created_utc >= cutoff)
    total = base_query.count()
    pag = get_pagination(total, page, per_page)
    if sort_by == "top":
        base_query = base_query.order_by(Comment.score.desc())
    elif sort_by == "old":
        base_query = base_query.order_by(Comment.created_utc.asc())
    else:
        base_query = base_query.order_by(Comment.created_utc.desc())
    if pag["per_page"] > 0:
        base_query = base_query.offset((pag["page"] - 1) * pag["per_page"]).limit(pag["per_page"])
    results = [{"comment": c, "thread": t} for c, t in base_query.all()]
    return templates.TemplateResponse(request, "search.html", {"q": q, "results": results, "pag": pag, "days_back": days_back, "sort_by": sort_by})


@router.get("/comment/{comment_id}/context", response_class=HTMLResponse)
def comment_context(comment_id: str, request: Request, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    ancestors = []
    current = comment
    while current.parent_id:
        parent = db.query(Comment).filter(Comment.id == current.parent_id).first()
        if not parent:
            break
        ancestors.insert(0, parent)
        current = parent
    children = (
        db.query(Comment)
        .filter(Comment.parent_id == comment_id)
        .order_by(Comment.created_utc)
        .all()
    )
    return templates.TemplateResponse(
        request, "_comment_context.html",
        {"ancestors": ancestors, "comment": comment, "children": children}
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {})
