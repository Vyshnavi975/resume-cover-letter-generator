"""Unit tests for generator.matcher -- pure keyword-matching logic that
requires no API key and no network access."""

from generator.matcher import (
    extract_keywords,
    match_background_to_job,
    score_bullet,
    tokenize,
)

SAMPLE_JD = """
Job Title: Backend Software Engineer

We are looking for a Backend Software Engineer with strong Python and
PostgreSQL skills. You will design REST APIs, work with Docker and AWS,
and collaborate in an Agile/Scrum team. Experience with Kubernetes and
CI/CD pipelines is a plus.
"""

SAMPLE_BACKGROUND = {
    "name": "Test Candidate",
    "skills": ["Python", "PostgreSQL", "Docker", "Excel"],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "Acme Corp",
            "achievements": [
                "Built REST APIs in Python and PostgreSQL for a logistics platform.",
                "Organized the company holiday party.",
                "Deployed services with Docker and AWS to improve reliability.",
            ],
        }
    ],
}


def test_tokenize_lowercases_and_splits():
    tokens = tokenize("Python, REST APIs, and PostgreSQL!")
    assert "python" in tokens
    assert "postgresql" in tokens
    assert all(t == t.lower() for t in tokens)


def test_tokenize_empty_string():
    assert tokenize("") == []
    assert tokenize(None) == []


def test_extract_keywords_returns_relevant_terms():
    keywords = extract_keywords(SAMPLE_JD, top_n=15)
    assert "python" in keywords
    assert "postgresql" in keywords
    assert "docker" in keywords
    # generic stopwords / boilerplate should not show up
    assert "with" not in keywords
    assert "and" not in keywords
    assert "the" not in keywords


def test_extract_keywords_respects_top_n():
    keywords = extract_keywords(SAMPLE_JD, top_n=3)
    assert len(keywords) <= 3


def test_extract_keywords_empty_text():
    assert extract_keywords("") == []


def test_score_bullet_counts_matches():
    keywords = ["python", "postgresql", "docker"]
    score, matched = score_bullet(
        "Built REST APIs in Python and PostgreSQL for scale.", keywords
    )
    assert score == 2
    assert set(matched) == {"python", "postgresql"}


def test_score_bullet_no_matches():
    score, matched = score_bullet("Organized the company holiday party.", ["python", "aws"])
    assert score == 0
    assert matched == []


def test_match_background_to_job_identifies_matched_skills():
    result = match_background_to_job(SAMPLE_BACKGROUND, SAMPLE_JD)
    assert "Python" in result.matched_skills
    assert "PostgreSQL" in result.matched_skills
    assert "Docker" in result.matched_skills
    # "Excel" never appears in the JD, so it should not be counted as matched
    assert "Excel" not in result.matched_skills
    assert "Excel" in result.unmatched_skills


def test_match_background_to_job_ranks_relevant_bullets_first():
    result = match_background_to_job(SAMPLE_BACKGROUND, SAMPLE_JD)
    assert len(result.bullets) == 3
    top_bullet = result.bullets[0]
    assert top_bullet.score >= result.bullets[1].score
    assert top_bullet.score >= result.bullets[2].score
    # the holiday-party bullet is irrelevant and should score lowest
    lowest_bullet = result.bullets[-1]
    assert "holiday party" in lowest_bullet.text


def test_match_background_to_job_flags_missing_keywords():
    result = match_background_to_job(SAMPLE_BACKGROUND, SAMPLE_JD)
    # the background never mentions Kubernetes or CI/CD, both called out
    # in the JD, so they should surface as gaps
    missing_joined = " ".join(result.missing_keywords)
    assert "kubernetes" in missing_joined

def test_match_background_handles_empty_experience():
    background = {"name": "Nobody", "skills": [], "experience": []}
    result = match_background_to_job(background, SAMPLE_JD)
    assert result.bullets == []
    assert result.matched_skills == []
