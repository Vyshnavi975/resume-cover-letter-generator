"""Resume & Cover Letter Generator.

A small toolkit that takes a candidate's background (skills, roles,
achievements) and a target job description and produces:

* tailored resume bullet points (``resume_bullets.md``)
* a draft cover letter (``cover_letter.md``)

If ``OPENAI_API_KEY`` is set in the environment, generation is
delegated to that LLM for genuinely tailored writing.
Otherwise the tool falls back to a deterministic, keyword-matching
"demo mode" that still produces a coherent, readable draft.
"""

__version__ = "1.0.0"
