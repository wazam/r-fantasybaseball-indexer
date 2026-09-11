import hashlib
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from sqlalchemy import func

from app.db import SessionLocal
from app.models import Comment, ListItem, Setting, Thread
from app.web.markdown_render import highlight_terms, render_markdown
from app.web.search_query import apply_search_filters, parse_search_query

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def _compute_static_version() -> str:
    static_dir = Path(__file__).resolve().parent.parent / "static"
    h = hashlib.md5()
    for name in ("style.css", "app.js"):
        h.update((static_dir / name).read_bytes())
    return h.hexdigest()[:8]


static_version = _compute_static_version()
templates.env.globals["static_version"] = static_version


def _get_tz():
    try:
        return ZoneInfo(os.getenv("TZ", "UTC"))
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _localdt(dt, fmt="%b %-d, %-I:%M %p"):
    return dt.replace(tzinfo=UTC).astimezone(_get_tz()).strftime(fmt)


def _smart_time(dt):
    tz = _get_tz()
    local = dt.replace(tzinfo=UTC).astimezone(tz)
    time_str = local.strftime("%-I:%M") + local.strftime("%p").lower()
    if local.year != datetime.now(tz).year:
        return local.strftime("%b %-d, %y") + " " + time_str
    return local.strftime("%b %-d") + ", " + time_str


templates.env.filters["localdt"] = _localdt
templates.env.filters["smart_time"] = _smart_time
templates.env.filters["render_markdown"] = render_markdown
templates.env.filters["highlight"] = highlight_terms


def get_highlight_terms(q: str) -> list:
    if not q:
        return []
    parsed = parse_search_query(q)
    return parsed.or_terms + parsed.required_terms


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


ALLOWED_LISTS = {"blocked_users", "favorited_users", "saved_comments"}


class ListItemIn(BaseModel):
    item: str


@router.get("/api/lists/{list_name}")
def get_list_items(list_name: str, db: Session = Depends(get_db)):
    if list_name not in ALLOWED_LISTS:
        raise HTTPException(status_code=404, detail="Unknown list")
    rows = (
        db.query(ListItem.item_value)
        .filter(ListItem.list_name == list_name)
        .order_by(ListItem.created_at)
        .all()
    )
    return [r[0] for r in rows]


@router.post("/api/lists/{list_name}")
def add_list_item(list_name: str, body: ListItemIn, db: Session = Depends(get_db)):
    if list_name not in ALLOWED_LISTS:
        raise HTTPException(status_code=404, detail="Unknown list")
    item_value = body.item.strip()
    if not item_value:
        raise HTTPException(status_code=400, detail="item is required")
    existing = (
        db.query(ListItem)
        .filter(ListItem.list_name == list_name, ListItem.item_value == item_value)
        .first()
    )
    if not existing:
        db.add(ListItem(list_name=list_name, item_value=item_value))
        db.commit()
    return {"status": "ok"}


@router.delete("/api/lists/{list_name}/{item_value}")
def delete_list_item(list_name: str, item_value: str, db: Session = Depends(get_db)):
    if list_name not in ALLOWED_LISTS:
        raise HTTPException(status_code=404, detail="Unknown list")
    db.query(ListItem).filter(
        ListItem.list_name == list_name, ListItem.item_value == item_value
    ).delete()
    db.commit()
    return {"status": "ok"}


ALLOWED_SETTINGS = {"aga_relative_timestamps", "aga_hide_flairs", "aga_auto_collapse"}


class SettingIn(BaseModel):
    value: str


@router.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    rows = db.query(Setting).all()
    return {row.key: row.value for row in rows}


@router.put("/api/settings/{key}")
def set_setting(key: str, body: SettingIn, db: Session = Depends(get_db)):
    if key not in ALLOWED_SETTINGS:
        raise HTTPException(status_code=404, detail="Unknown setting")
    existing = db.query(Setting).filter(Setting.key == key).first()
    if existing:
        existing.value = body.value
    else:
        db.add(Setting(key=key, value=body.value))
    db.commit()
    return {"status": "ok"}


@router.delete("/api/settings/{key}")
def delete_setting(key: str, db: Session = Depends(get_db)):
    if key not in ALLOWED_SETTINGS:
        raise HTTPException(status_code=404, detail="Unknown setting")
    db.query(Setting).filter(Setting.key == key).delete()
    db.commit()
    return {"status": "ok"}


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
    return templates.TemplateResponse(request, "search.html", {"q": q, "results": results, "pag": pag, "days_back": days_back, "sort_by": sort_by, "highlight_terms": get_highlight_terms(q)})


@router.get("/comment/{comment_id}/context", response_class=HTMLResponse)
def comment_context(comment_id: str, request: Request, q: str = "", db: Session = Depends(get_db)):
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
        {"ancestors": ancestors, "comment": comment, "children": children, "highlight_terms": get_highlight_terms(q)}
    )


@router.get("/saved/comments", response_class=HTMLResponse)
def saved_comments_partial(request: Request, ids: str = "", db: Session = Depends(get_db)):
    id_list = [i for i in ids.split(",") if i]
    items = []
    if id_list:
        rows = (
            db.query(Comment, Thread)
            .join(Thread, Comment.thread_id == Thread.id)
            .filter(Comment.id.in_(id_list))
            .all()
        )
        by_id = {c.id: (c, t) for c, t in rows}
        items = [{"comment": c, "thread": t} for c, t in (by_id[i] for i in id_list if i in by_id)]
    return templates.TemplateResponse(request, "_saved_comments.html", {"items": items})


@router.get("/author/{username}/summary", response_class=HTMLResponse)
def author_summary(username: str, request: Request, db: Session = Depends(get_db)):
    stats = (
        db.query(
            func.count(Comment.id),
            func.sum(Comment.score),
            func.min(Comment.created_utc),
            func.max(Comment.created_utc),
        )
        .filter(Comment.author == username)
        .first()
    )
    total, total_score, first_seen, last_seen = stats
    if not total:
        raise HTTPException(status_code=404, detail="No comments found for this author")

    recent = (
        db.query(Comment, Thread)
        .join(Thread, Comment.thread_id == Thread.id)
        .filter(Comment.author == username)
        .order_by(Comment.created_utc.desc())
        .limit(15)
        .all()
    )
    recent_comments = [{"comment": c, "thread": t} for c, t in recent]
    latest_flair = recent_comments[0]["comment"].flair if recent_comments else None

    return templates.TemplateResponse(
        request, "_author_summary.html",
        {
            "username": username,
            "total": total,
            "total_score": total_score or 0,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "latest_flair": latest_flair,
            "recent_comments": recent_comments,
        }
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {})


@router.get("/saved", response_class=HTMLResponse)
def saved_page(request: Request):
    return templates.TemplateResponse(request, "saved.html", {})
