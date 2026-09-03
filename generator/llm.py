"""LLM-backed generation of resume bullets and a cover letter.

Supports OpenAI and Anthropic (Claude) as an optional secondary
alternative, selected automatically based on which API key is present
in the environment. OpenAI is preferred if both are set. Both SDKs are
imported lazily inside the functions that need them, so the rest of
the package (and the test suite) has no hard dependency on either
being installed.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional, Tuple

DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")


class LLMError(RuntimeError):
    """Raised when LLM generation fails (missing SDK, API error, bad
    response format, etc.) so callers can cleanly fall back to demo mode."""


def get_provider() -> Optional[str]:
    """Return ``"openai"``, ``"anthropic"``, or ``None`` based on which API
    key is present in the environment. OpenAI wins if both are set."""
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


_PROMPT_TEMPLATE = """You are an expert resume writer and career coach. \
Given a candidate's background and a target job description, produce two \
pieces of tailored content that map the candidate's real experience onto \
the job's actual requirements. Do not invent facts, employers, titles, \
or metrics that are not supported by the background provided -- rephrase \
and prioritize what is there, don't fabricate new achievements.

Respond with ONLY a single JSON object (no markdown fences, no commentary) \
with exactly two string fields:
  "resume_bullets": a Markdown document with an H1 title, a short section \
    listing the skills most worth highlighting for this job, then the \
    candidate's experience grouped by role (use the role titles/companies/\
    dates given) with 3-6 rewritten, quantified-where-possible bullet \
    points per role, each rephrased to emphasize relevance to the job \
    description.
  "cover_letter": a complete, ready-to-send Markdown cover letter (3-4 \
    paragraphs) addressed to the hiring manager, referencing the target \
    role and company if identifiable from the job description, and \
    connecting 2-3 specific achievements from the background to specific \
    requirements in the job description.

CANDIDATE BACKGROUND (structured data):
{background_json}

TARGET JOB DESCRIPTION:
{job_description}
"""


def _build_prompt(background: Dict[str, Any], job_description: str) -> str:
    return _PROMPT_TEMPLATE.format(
        background_json=json.dumps(background, indent=2, ensure_ascii=False),
        job_description=job_description.strip(),
    )


def _parse_json_response(raw_text: str) -> Dict[str, str]:
    text = raw_text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if the model added them
    # despite instructions not to.
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        # Last resort: grab the outermost {...} block.
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not brace_match:
            raise LLMError(f"Could not parse LLM response as JSON: {exc}") from exc
        try:
            data = json.loads(brace_match.group(0))
        except json.JSONDecodeError as exc2:
            raise LLMError(f"Could not parse LLM response as JSON: {exc2}") from exc2

    if "resume_bullets" not in data or "cover_letter" not in data:
        raise LLMError(
            "LLM response JSON is missing 'resume_bullets' and/or "
            "'cover_letter' keys."
        )
    return {
        "resume_bullets": data["resume_bullets"],
        "cover_letter": data["cover_letter"],
    }


def _generate_with_openai(prompt: str) -> str:
    try:
        import openai
    except ImportError as exc:
        raise LLMError(
            "The 'openai' package is not installed. Run `pip install "
            "openai` or unset OPENAI_API_KEY to use demo mode."
        ) from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=DEFAULT_OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"OpenAI API call failed: {exc}") from exc

    return response.choices[0].message.content or ""


def _generate_with_anthropic(prompt: str) -> str:
    # Secondary/alternative provider — used only when ANTHROPIC_API_KEY is
    # set and OPENAI_API_KEY is not.
    try:
        import anthropic
    except ImportError as exc:
        raise LLMError(
            "The 'anthropic' package is not installed. Run "
            "`pip install anthropic` or unset ANTHROPIC_API_KEY to use "
            "demo mode."
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=DEFAULT_ANTHROPIC_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface any SDK/API error uniformly
        raise LLMError(f"Anthropic API call failed: {exc}") from exc

    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )


def generate_with_llm(
    background: Dict[str, Any], job_description: str, provider: Optional[str] = None
) -> Tuple[str, str]:
    """Generate tailored resume bullets and a cover letter via an LLM.

    Returns ``(resume_bullets_markdown, cover_letter_markdown)``.
    Raises :class:`LLMError` on any failure (missing key, missing SDK,
    network/API error, unparseable response) so the caller can fall back
    to demo mode.
    """
    provider = provider or get_provider()
    if provider is None:
        raise LLMError(
            "No LLM provider available: set OPENAI_API_KEY or "
            "ANTHROPIC_API_KEY to enable LLM generation."
        )

    prompt = _build_prompt(background, job_description)

    if provider == "openai":
        raw = _generate_with_openai(prompt)
    elif provider == "anthropic":
        raw = _generate_with_anthropic(prompt)
    else:
        raise LLMError(f"Unknown provider: {provider!r}")

    parsed = _parse_json_response(raw)
    return parsed["resume_bullets"], parsed["cover_letter"]
