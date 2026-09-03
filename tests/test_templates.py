"""Unit tests for generator.templates -- deterministic Markdown rendering
used in demo mode. No API key or network access required."""

from generator.matcher import match_background_to_job
from generator.templates import (
    DEMO_MODE_NOTICE,
    extract_job_meta,
    render_cover_letter,
    render_resume_bullets,
)

JOB_DESCRIPTION = """Job Title: Backend Software Engineer
Company: Riverstone Digital

We are looking for a Backend Software Engineer with strong Python and
PostgreSQL skills. You will design REST APIs, work with Docker and AWS.
"""

BACKGROUND = {
    "name": "Taylor Kim",
    "email": "taylor@example.com",
    "phone": "555-0100",
    "location": "Remote",
    "skills": ["Python", "PostgreSQL", "Docker", "Public Speaking"],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "Acme Corp",
            "dates": "2021 - Present",
            "achievements": [
                "Built REST APIs in Python and PostgreSQL for a logistics platform.",
                "Deployed services with Docker and AWS to improve reliability.",
                "Gave a talk at a local meetup.",
            ],
        }
    ],
}


def test_extract_job_meta_finds_labeled_title_and_company():
    title, company = extract_job_meta(JOB_DESCRIPTION)
    assert title == "Backend Software Engineer"
    assert company == "Riverstone Digital"


def test_extract_job_meta_falls_back_to_first_line():
    title, company = extract_job_meta("Data Analyst\n\nWe need someone great.")
    assert title == "Data Analyst"
    assert company is None


def test_extract_job_meta_handles_empty_text():
    title, company = extract_job_meta("")
    assert title is None
    assert company is None


def test_render_resume_bullets_includes_demo_notice_and_name():
    match = match_background_to_job(BACKGROUND, JOB_DESCRIPTION)
    output = render_resume_bullets(BACKGROUND, match)
    assert "Taylor Kim" in output
    assert DEMO_MODE_NOTICE in output
    assert "Software Engineer" in output
    assert "Acme Corp" in output


def test_render_resume_bullets_surfaces_matched_skills():
    match = match_background_to_job(BACKGROUND, JOB_DESCRIPTION)
    output = render_resume_bullets(BACKGROUND, match)
    assert "Python" in output
    assert "PostgreSQL" in output


def test_render_resume_bullets_handles_no_experience():
    background = {"name": "Empty Person", "skills": [], "experience": []}
    match = match_background_to_job(background, JOB_DESCRIPTION)
    output = render_resume_bullets(background, match)
    assert "No experience entries found" in output


def test_render_cover_letter_includes_company_and_name():
    match = match_background_to_job(BACKGROUND, JOB_DESCRIPTION)
    output = render_cover_letter(BACKGROUND, JOB_DESCRIPTION, match)
    assert "Riverstone Digital" in output
    assert "Taylor Kim" in output
    assert DEMO_MODE_NOTICE in output


def test_render_cover_letter_respects_company_override():
    match = match_background_to_job(BACKGROUND, JOB_DESCRIPTION)
    output = render_cover_letter(
        BACKGROUND, JOB_DESCRIPTION, match, company_name="Custom Co"
    )
    assert "Custom Co" in output


def test_render_cover_letter_mentions_top_achievement():
    match = match_background_to_job(BACKGROUND, JOB_DESCRIPTION)
    output = render_cover_letter(BACKGROUND, JOB_DESCRIPTION, match)
    assert "REST APIs" in output or "PostgreSQL" in output
