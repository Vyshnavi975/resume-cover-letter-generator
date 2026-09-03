"""Command-line entry point for the Resume & Cover Letter Generator."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from . import llm, templates
from .matcher import match_background_to_job

REQUIRED_BACKGROUND_FIELDS = ["name", "skills", "experience"]


class InputError(ValueError):
    """Raised for problems with user-supplied input files."""


def load_background(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise InputError(f"Background file not found: {path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise InputError(
                "Reading a .yaml background file requires PyYAML. Install "
                "it with `pip install pyyaml` (see requirements.txt), or "
                "supply a .json background file instead."
            ) from exc
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise InputError(
            f"Unsupported background file type '{suffix}'. Use .yaml, .yml, "
            "or .json."
        )

    if not isinstance(data, dict):
        raise InputError("Background file must contain a top-level object/mapping.")

    missing = [f for f in REQUIRED_BACKGROUND_FIELDS if f not in data]
    if missing:
        raise InputError(
            "Background file is missing required field(s): "
            + ", ".join(missing)
            + ". See examples/background.yaml for the expected format."
        )

    return data


def load_job_description(path: Path) -> str:
    if not path.exists():
        raise InputError(f"Job description file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise InputError(f"Job description file is empty: {path}")
    return text


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-cover-letter-generator",
        description=(
            "Generate tailored resume bullet points and a cover letter "
            "draft from a candidate background file and a target job "
            "description."
        ),
    )
    parser.add_argument(
        "--background",
        "-b",
        required=True,
        type=Path,
        help="Path to a background.yaml or background.json file "
        "(see examples/background.yaml).",
    )
    parser.add_argument(
        "--job-description",
        "-j",
        required=True,
        type=Path,
        help="Path to a plain-text job description file.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("."),
        help="Directory to write resume_bullets.md and cover_letter.md "
        "into (default: current directory).",
    )
    parser.add_argument(
        "--company",
        help="Company name to address the cover letter to, if you want to "
        "override what's auto-detected from the job description.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Force demo (keyword-matching) mode even if an API key is set.",
    )
    return parser


def run(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        background = load_background(args.background)
        job_description = load_job_description(args.job_description)
    except InputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)

    resume_bullets_md: str
    cover_letter_md: str
    mode_used = "demo"

    provider = None if args.demo else llm.get_provider()
    llm_failed = False

    if provider:
        print(f"Using {provider} to generate tailored content...")
        try:
            resume_bullets_md, cover_letter_md = llm.generate_with_llm(
                background, job_description, provider=provider
            )
            mode_used = provider
        except llm.LLMError as exc:
            print(
                f"Warning: LLM generation failed ({exc}). Falling back to "
                "demo (keyword-matching) mode.",
                file=sys.stderr,
            )
            provider = None
            llm_failed = True

    if not provider:
        if args.demo:
            print("Running in demo mode (--demo flag set): using keyword matching, no LLM call.")
        elif llm_failed:
            print("Running in demo mode: using keyword matching, not an LLM.")
        else:
            print(
                "No OPENAI_API_KEY found. Running in demo mode: using "
                "keyword matching, not an LLM."
            )
        match = match_background_to_job(background, job_description)
        resume_bullets_md = templates.render_resume_bullets(background, match)
        cover_letter_md = templates.render_cover_letter(
            background, job_description, match, company_name=args.company
        )
        mode_used = "demo"

    resume_path = args.output_dir / "resume_bullets.md"
    cover_path = args.output_dir / "cover_letter.md"
    resume_path.write_text(resume_bullets_md, encoding="utf-8")
    cover_path.write_text(cover_letter_md, encoding="utf-8")

    print(f"Mode: {mode_used}")
    print(f"Wrote {resume_path}")
    print(f"Wrote {cover_path}")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
