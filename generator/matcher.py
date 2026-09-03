"""Keyword extraction and background-to-job matching.

This module contains no LLM calls -- it is pure, deterministic text
processing so it can be unit tested without any API key and is also
what powers "demo mode" when no LLM key is available.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# A small, generic stopword list -- enough to keep frequency-based keyword
# extraction from job descriptions from being dominated by function words.
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "to", "of",
    "in", "on", "at", "for", "with", "by", "from", "as", "is", "are",
    "was", "were", "be", "been", "being", "this", "that", "these",
    "those", "we", "you", "your", "our", "us", "it", "its", "their",
    "they", "he", "she", "his", "her", "will", "would", "should", "can",
    "could", "may", "might", "must", "shall", "have", "has", "had",
    "do", "does", "did", "not", "no", "yes", "about", "into", "than",
    "which", "who", "whom", "what", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "too", "very", "just",
    "up", "down", "out", "off", "over", "under", "again", "further",
    "once", "here", "there", "also", "etc", "including", "include",
    "role", "job", "work", "working", "team", "years", "year",
    "experience", "required", "preferred", "responsibilities",
    "qualifications", "requirements", "ability", "strong", "including",
    "plus", "within", "across", "using", "use", "used", "new", "one",
    "least", "e.g", "eg", "i.e", "ie", "etc.", "company", "we're",
    "help", "improve", "similar", "per", "day", "core",
}

# Words shorter than this are dropped from frequency-based keyword lists
# (acronyms are special-cased below because they matter a lot in tech job
# descriptions, e.g. "SQL", "AWS", "API").
_MIN_KEYWORD_LEN = 3

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.#/-]*")


def tokenize(text: str) -> List[str]:
    """Lowercase word tokens, keeping tech-flavoured punctuation like
    ``c++``, ``node.js``, or ``ci/cd`` intact."""
    if not text:
        return []
    return [tok.lower().strip(".-/") for tok in _WORD_RE.findall(text)]


def _is_meaningful(token: str, original_had_upper: bool) -> bool:
    if not token:
        return False
    if token in STOPWORDS:
        return False
    if token.isdigit():
        return False
    if len(token) < _MIN_KEYWORD_LEN and not original_had_upper:
        # keep short tokens only if they looked like an acronym (e.g. "SQL")
        return False
    return True


def extract_keywords(text: str, top_n: int = 25) -> List[str]:
    """Return the ``top_n`` most frequent meaningful keywords in ``text``,
    ordered by descending frequency (ties broken by first appearance).

    Multi-word "phrases" separated by commas/semicolons/bullets (a common
    pattern in "Requirements:" lists) are also captured whole, in addition
    to individual word tokens, so that e.g. "project management" survives
    as a phrase rather than being lost as two generic-looking words.
    """
    if not text:
        return []

    counts: Counter = Counter()
    order: Dict[str, int] = {}
    position = 0

    raw_words = _WORD_RE.findall(text)
    for raw in raw_words:
        token = raw.lower().strip(".-/")
        if _is_meaningful(token, raw[:1].isupper() and not raw.islower()):
            counts[token] += 1
            order.setdefault(token, position)
            position += 1

    # Capture short comma/semicolon separated phrases (2-3 words) from
    # bullet-style requirement lines, e.g. "Python, SQL, and data
    # visualization" or "5+ years of project management experience".
    for line in re.split(r"[\n]", text):
        for chunk in re.split(r"[,;•]| and | or ", line):
            phrase = chunk.strip(" .-\t")
            words = phrase.split()
            if 2 <= len(words) <= 3 and all(_WORD_RE.match(w) for w in words):
                key = phrase.lower()
                if not any(w.lower() in STOPWORDS for w in words) and len(key) > 5:
                    counts[key] += 1
                    order.setdefault(key, position)
                    position += 1

    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], order[kv[0]]))
    return [word for word, _ in ranked[:top_n]]


_TITLE_PATTERNS = [
    r"^\s*(?:job\s*title|position|role)\s*[:\-]\s*(.+)$",
]
_COMPANY_PATTERNS = [
    r"^\s*(?:company|employer|organization)\s*[:\-]\s*(.+)$",
]


def extract_job_meta(job_description: str) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort extraction of a job title and company name from free-form
    job description text. Returns ``(title, company)``, either of which may
    be ``None`` if nothing confident was found."""
    title = None
    company = None
    lines = [ln.strip() for ln in job_description.splitlines() if ln.strip()]

    for line in lines:
        if title is None:
            for pat in _TITLE_PATTERNS:
                m = re.match(pat, line, re.IGNORECASE)
                if m:
                    title = m.group(1).strip().rstrip(".")
        if company is None:
            for pat in _COMPANY_PATTERNS:
                m = re.match(pat, line, re.IGNORECASE)
                if m:
                    company = m.group(1).strip().rstrip(".")
        if title and company:
            break

    # Fallback: treat the very first non-empty line as the job title if it
    # is short and doesn't look like a sentence (no trailing period, not too
    # long) -- a common convention for plain-text job postings.
    if title is None and lines:
        first = lines[0]
        if len(first) <= 80 and not first.endswith("."):
            title = first.rstrip(":").strip()

    return title, company


def _flatten_background_text(background: Dict[str, Any]) -> str:
    """Concatenate every free-text field of a background dict into one
    lowercase blob, used for substring containment checks."""
    parts: List[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                add(item)
        elif isinstance(value, dict):
            for item in value.values():
                add(item)

    add(background.get("summary"))
    add(background.get("skills"))
    for exp in background.get("experience", []) or []:
        add(exp.get("title"))
        add(exp.get("company"))
        add(exp.get("achievements"))
    for edu in background.get("education", []) or []:
        add(edu.get("degree"))
        add(edu.get("field"))
    add(background.get("certifications"))

    return " ".join(parts).lower()


@dataclass
class BulletMatch:
    """A single achievement bullet scored against the job description."""

    text: str
    role_title: str
    company: str
    score: int
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    top_keywords: List[str]
    matched_skills: List[str]
    unmatched_skills: List[str]
    missing_keywords: List[str]
    bullets: List[BulletMatch]

    def bullets_for_role(self, role_title: str, company: str) -> List[BulletMatch]:
        return [
            b for b in self.bullets
            if b.role_title == role_title and b.company == company
        ]


def score_bullet(bullet_text: str, keywords: List[str]) -> Tuple[int, List[str]]:
    """Score one achievement bullet by how many job-description keywords
    it contains (case-insensitive substring match). Returns
    ``(score, matched_keywords)``."""
    lowered = bullet_text.lower()
    matched = [kw for kw in keywords if kw in lowered]
    return len(matched), matched


def match_background_to_job(
    background: Dict[str, Any], job_description: str, top_n_keywords: int = 25
) -> MatchResult:
    """Compare a structured ``background`` dict against ``job_description``
    text and return a :class:`MatchResult` used to drive template
    rendering in demo mode (and to give the LLM useful context in
    LLM mode)."""

    keywords = extract_keywords(job_description, top_n=top_n_keywords)

    # Exclude words that are purely part of the detected company name (e.g.
    # "Riverstone", "Digital") -- they're frequent in the JD text simply
    # because they're the letterhead, not because they're a skill or
    # requirement worth flagging as "missing" from the candidate's
    # background. (Job title words are kept -- they're often genuinely
    # relevant, e.g. "Backend" in "Backend Software Engineer".)
    _, company = extract_job_meta(job_description)
    company_words = set()
    if company:
        company_words.update(w.lower() for w in re.findall(r"[A-Za-z]+", company))
    keywords = [kw for kw in keywords if kw not in company_words]

    jd_lower = job_description.lower()

    skills = background.get("skills", []) or []
    matched_skills = [s for s in skills if s.lower() in jd_lower]
    unmatched_skills = [s for s in skills if s not in matched_skills]

    background_text = _flatten_background_text(background)
    missing_keywords = [kw for kw in keywords if kw not in background_text]

    bullets: List[BulletMatch] = []
    for exp in background.get("experience", []) or []:
        title = exp.get("title", "")
        company = exp.get("company", "")
        for achievement in exp.get("achievements", []) or []:
            score, matched = score_bullet(achievement, keywords)
            bullets.append(
                BulletMatch(
                    text=achievement,
                    role_title=title,
                    company=company,
                    score=score,
                    matched_keywords=matched,
                )
            )

    bullets.sort(key=lambda b: b.score, reverse=True)

    return MatchResult(
        top_keywords=keywords,
        matched_skills=matched_skills,
        unmatched_skills=unmatched_skills,
        missing_keywords=missing_keywords,
        bullets=bullets,
    )
