import operator
import re
from dataclasses import dataclass, field

from sqlalchemy import or_

from app.models import Comment

_SCORE_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "=": operator.eq,
}

_TOKEN_PATTERN = re.compile(
    r'(?P<sign>[+-])?'
    r'(?:(?P<fieldname>author|flair|score):)?'
    r'(?:"(?P<quoted>[^"]*)"|(?P<word>[^\s"]+))'
)

_SCORE_PATTERN = re.compile(r'^(?P<op>>=|<=|>|<)?(?P<num>-?\d+)$')


@dataclass
class ParsedQuery:
    or_terms: list = field(default_factory=list)
    required_terms: list = field(default_factory=list)
    excluded_terms: list = field(default_factory=list)
    authors: list = field(default_factory=list)
    flairs: list = field(default_factory=list)
    score_filters: list = field(default_factory=list)  # list of (op, int)


def parse_search_query(q: str) -> ParsedQuery:
    parsed = ParsedQuery()
    if not q:
        return parsed

    for m in _TOKEN_PATTERN.finditer(q):
        value = m.group("quoted") if m.group("quoted") is not None else m.group("word")
        if not value:
            continue

        sign = m.group("sign")
        fieldname = m.group("fieldname")

        if fieldname == "author":
            parsed.authors.append(value)
        elif fieldname == "flair":
            parsed.flairs.append(value)
        elif fieldname == "score":
            score_match = _SCORE_PATTERN.match(value)
            if score_match:
                op = score_match.group("op") or "="
                parsed.score_filters.append((op, int(score_match.group("num"))))
        elif sign == "+":
            parsed.required_terms.append(value)
        elif sign == "-":
            parsed.excluded_terms.append(value)
        else:
            parsed.or_terms.append(value)

    return parsed


def apply_search_filters(query, parsed: ParsedQuery):
    if parsed.or_terms:
        query = query.filter(or_(*[Comment.body.ilike(f"%{t}%") for t in parsed.or_terms]))
    for term in parsed.required_terms:
        query = query.filter(Comment.body.ilike(f"%{term}%"))
    for term in parsed.excluded_terms:
        query = query.filter(~Comment.body.ilike(f"%{term}%"))
    for author in parsed.authors:
        query = query.filter(Comment.author.ilike(f"%{author}%"))
    for flair in parsed.flairs:
        query = query.filter(Comment.flair.ilike(f"%{flair}%"))
    for op, num in parsed.score_filters:
        query = query.filter(_SCORE_OPS[op](Comment.score, num))
    return query
