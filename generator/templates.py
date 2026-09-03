"""Demo-mode rendering: turns a :class:`~generator.matcher.MatchResult`
into readable Markdown without calling any LLM.

Everything here is deterministic string templating so it can run (and be
unit tested) with zero external dependencies and zero API key.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from .matcher import MatchResult, extract_job_meta

DEMO_MODE_NOTICE = (
    "> _Generated in **demo mode** (no `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`"
    " found) using deterministic keyword matching, not an LLM. Set one of"
    " those environment variables for genuinely tailored, freshly written"
    " content._"
)

def _rewrite_bullet(text: str) -> str:
    """Light touch-up: ensure the bullet reads as a complete sentence
    fragment starting with a capitalized action word and ending cleanly."""
    text = text.strip()
    if not text:
        return text
    if not text[0].isupper():
        text = text[0].upper() + text[1:]
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


def render_resume_bullets(
    background: Dict[str, Any], match: MatchResult, max_bullets_per_role: int = 6
) -> str:
    """Render a Markdown document of tailored resume bullets, grouped by
    role, with the highest-scoring (most job-relevant) bullets surfaced
    first within each role."""
    name = background.get("name", "Candidate")
    lines: List[str] = [f"# Tailored Resume Bullets for {name}", "", DEMO_MODE_NOTICE, ""]

    if match.matched_skills:
        lines.append("## Skills to Highlight (matched to this job)")
        lines.append("")
        lines.append(", ".join(match.matched_skills))
        lines.append("")

    if match.missing_keywords:
        lines.append("## Job Keywords Not Yet Reflected in Your Background")
        lines.append("")
        lines.append(
            "Consider addressing these in your resume or cover letter if you "
            "have relevant experience: " + ", ".join(match.missing_keywords[:12])
        )
        lines.append("")

    experience = background.get("experience", []) or []
    if not experience:
        lines.append("_No experience entries found in the background file._")
        return "\n".join(lines) + "\n"

    lines.append("## Bullets by Role")
    lines.append("")

    for exp in experience:
        title = exp.get("title", "Role")
        company = exp.get("company", "")
        dates = exp.get("dates", "")
        header = f"### {title}" + (f", {company}" if company else "")
        if dates:
            header += f" ({dates})"
        lines.append(header)
        lines.append("")

        role_bullets = match.bullets_for_role(title, company)
        if not role_bullets:
            lines.append("_No achievements listed for this role._")
            lines.append("")
            continue

        for b in role_bullets[:max_bullets_per_role]:
            bullet = _rewrite_bullet(b.text)
            if b.matched_keywords:
                tag = ", ".join(sorted(set(b.matched_keywords)))
                lines.append(f"- {bullet} _(relevant: {tag})_")
            else:
                lines.append(f"- {bullet}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _pick_top_achievements(match: MatchResult, n: int = 3) -> List[str]:
    top = [b for b in match.bullets if b.score > 0][:n]
    if len(top) < n:
        # pad with whatever bullets exist, even unmatched, so the letter
        # never looks empty for a thin background/JD overlap.
        seen = {id(b) for b in top}
        for b in match.bullets:
            if id(b) not in seen:
                top.append(b)
                seen.add(id(b))
            if len(top) >= n:
                break
    return [_rewrite_bullet(b.text) for b in top]


def render_cover_letter(
    background: Dict[str, Any],
    job_description: str,
    match: MatchResult,
    company_name: Optional[str] = None,
) -> str:
    """Render a Markdown cover letter draft using simple mail-merge style
    templating filled in from the matched background/job data."""
    name = background.get("name", "Candidate")
    email = background.get("email", "")
    phone = background.get("phone", "")
    location = background.get("location", "")

    job_title, detected_company = extract_job_meta(job_description)
    company = company_name or detected_company or "your company"
    role_phrase = job_title or "this position"

    experience = background.get("experience", []) or []
    most_recent = experience[0] if experience else {}
    current_title = most_recent.get("title", "a related professional")

    top_skills = (match.matched_skills or background.get("skills", []))[:5]
    skills_phrase = ", ".join(top_skills) if top_skills else "a strong, relevant skill set"

    achievements = _pick_top_achievements(match, n=3)

    _today = date.today()
    today = f"{_today.strftime('%B')} {_today.day}, {_today.year}"

    contact_line = " | ".join(p for p in [email, phone, location] if p)

    article = "an" if current_title[:1].lower() in "aeiou" else "a"
    body_paragraphs = [
        f"I am writing to apply for the {role_phrase} position at {company}. "
        f"As {article} {current_title} with hands-on experience in {skills_phrase}, "
        f"I am confident I can contribute quickly and meaningfully to your team.",
    ]

    if achievements:
        body_paragraphs.append(
            "A few highlights from my background that align closely with what "
            f"you're looking for in this role:\n\n"
            + "\n".join(f"- {a}" for a in achievements)
        )

    if match.matched_skills:
        body_paragraphs.append(
            "Your posting emphasizes " + ", ".join(match.matched_skills[:6]) + ", all areas "
            "where I have direct, applied experience -- not just familiarity."
        )

    body_paragraphs.append(
        f"I would welcome the opportunity to discuss how my background can support "
        f"{company}'s goals for this role. Thank you for your time and consideration."
    )

    lines: List[str] = [
        "# Cover Letter",
        "",
        DEMO_MODE_NOTICE,
        "",
    ]
    if contact_line:
        lines.append(contact_line)
        lines.append("")
    if today:
        lines.append(today)
        lines.append("")

    lines.append(f"Dear Hiring Manager at {company},")
    lines.append("")
    for para in body_paragraphs:
        lines.append(para)
        lines.append("")

    lines.append("Sincerely,")
    lines.append(name)

    return "\n".join(lines).rstrip() + "\n"
