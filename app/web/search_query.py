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
    r'(?:(?P<fieldname>author|user|flair|score):)?'
    r'(?:"(?P<quoted>[^"]*)"|(?P<word>[^\s"]+))',
    re.IGNORECASE,
)

_SCORE_PATTERN = re.compile(r'^(?P<op>>=|<=|>|<|=)?(?P<num>-?\d+)$')


@dataclass
class ParsedQuery:
    or_terms: list = field(default_factory=list)
    required_terms: list = field(default_factory=list)
    excluded_terms: list = field(default_factory=list)
    authors: list = field(default_factory=list)
    excluded_authors: list = field(default_factory=list)
    flairs: list = field(default_factory=list)
    excluded_flairs: list = field(default_factory=list)
    score_filters: list = field(default_factory=list)  # list of (op, int)
    excluded_score_filters: list = field(default_factory=list)  # list of (op, int)


# Where a token's value goes, by field keyword: (the list without a - sign, the list with one)
_FIELD_LISTS = {
    "": ("or_terms", "excluded_terms"),
    "author": ("authors", "excluded_authors"),
    "user": ("authors", "excluded_authors"),
    "flair": ("flairs", "excluded_flairs"),
    "score": ("score_filters", "excluded_score_filters"),
}


def parse_search_query(q: str) -> ParsedQuery:
    parsed = ParsedQuery()
    for m in _TOKEN_PATTERN.finditer(q or ""):
        value = m.group("quoted") if m.group("quoted") is not None else m.group("word")
        if value:
            _add_term(parsed, (m.group("fieldname") or "").lower(), m.group("sign"), value)
    return parsed


def _add_term(parsed: ParsedQuery, fieldname: str, sign, value: str):
    """Put one search token's value in the list it belongs to."""
    if fieldname == "score":
        score_match = _SCORE_PATTERN.match(value)
        if not score_match:
            return
        value = (score_match.group("op") or "=", int(score_match.group("num")))
    if fieldname == "" and sign == "+":
        target = "required_terms"
    else:
        target = _FIELD_LISTS[fieldname][sign == "-"]
    getattr(parsed, target).append(value)


def _contains(column, text: str):
    """Case-insensitive substring match, with % and _ in the text matched literally."""
    return column.icontains(text, autoescape=True)


def _lacks(column, text: str):
    """The opposite of _contains, counting an empty (NULL) column as not containing the text."""
    return or_(column.is_(None), ~_contains(column, text))


def apply_search_filters(query, parsed: ParsedQuery):
    """Bare words match any of them, and repeated author: or flair: values match any of them.
    Everything else must all hold: + and - words, - fields and each score comparison."""
    conditions = []
    for column, any_of in ((Comment.body, parsed.or_terms), (Comment.author, parsed.authors), (Comment.flair, parsed.flairs)):
        if any_of:
            conditions.append(or_(*[_contains(column, t) for t in any_of]))
    conditions += [_contains(Comment.body, t) for t in parsed.required_terms]
    for column, none_of in ((Comment.body, parsed.excluded_terms), (Comment.author, parsed.excluded_authors),
                            (Comment.flair, parsed.excluded_flairs)):
        conditions += [_lacks(column, t) for t in none_of]
    conditions += [_SCORE_OPS[op](Comment.score, num) for op, num in parsed.score_filters]
    conditions += [~_SCORE_OPS[op](Comment.score, num) for op, num in parsed.excluded_score_filters]
    return query.filter(*conditions) if conditions else query
