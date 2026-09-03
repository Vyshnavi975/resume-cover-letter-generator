# Resume & Cover Letter Generator

Turn a candidate's background (skills, roles, achievements) and a target
job description into **tailored resume bullet points** and a **draft
cover letter** — with the candidate's real experience mapped onto the
job's actual requirements.

If `OPENAI_API_KEY` is set, the tool calls that LLM to genuinely
rewrite and tailor the content (an Anthropic/Claude alternative is
also supported — see [Setup](#setup)). Otherwise it falls
back to a deterministic **demo mode** that does keyword matching
between the background and job description and fills in a structured
template — no API key required, and the output is clearly labeled as
demo-generated.

## Features

- **CLI tool**: point it at a background file and a job description,
  get back two Markdown files.
- **Two generation modes**, selected automatically:
  - **LLM mode** (OpenAI) — genuinely rewritten,
    tailored bullets and a fresh cover letter draft, grounded in the
    candidate's real background (the prompt explicitly forbids
    inventing facts).
  - **Demo mode** (no API key needed) — deterministic keyword
    extraction from the job description, matched against the
    candidate's skills and achievements, used to rank and tag the most
    relevant resume bullets and to fill in a cover letter template.
- **Flexible input**: background as YAML or JSON.
- **Job title / company auto-detection** from free-form job description
  text (or override with `--company`).
- **Graceful fallback**: if an API key is set but the call fails (no
  network, bad key, SDK not installed, etc.), the tool automatically
  falls back to demo mode instead of crashing.
- Clean, importable module structure (`generator/matcher.py`,
  `generator/templates.py`, `generator/llm.py`, `generator/cli.py`) with
  unit tests for the keyword-matching/template logic that run with no
  API key and no network access.

## How it works (demo mode)

1. `generator/matcher.py` extracts the most frequent meaningful
   keywords from the job description (filtering out stopwords and
   boilerplate), and also picks up short comma-separated requirement
   phrases like `project management`.
2. It checks which of the candidate's listed `skills` actually appear
   in the job description (`matched_skills`), and which top JD
   keywords are absent from the candidate's background entirely
   (`missing_keywords`) — useful as a gap-check.
3. Every achievement bullet in the background is scored by how many JD
   keywords it contains, and bullets are ranked so the most relevant
   ones surface first, per role.
4. `generator/templates.py` renders that into two Markdown documents:
   a resume-bullets doc grouped by role (each bullet tagged with which
   keywords it matches), and a cover letter that opens with the
   detected job title/company, highlights the top 3 scoring
   achievements, and calls out the specific matched skills.

In **LLM mode**, `generator/llm.py` instead sends the full structured
background plus the job description to GPT with instructions
to rewrite (not invent) the candidate's real experience into tailored,
well-written bullets and a cover letter, requesting a JSON response
with `resume_bullets` and `cover_letter` Markdown fields that are
written straight to the output files.

## Setup

Requires Python 3.9+.

```bash
cd resume-cover-letter-generator
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

`requirements.txt` includes `PyYAML` (needed to read `.yaml` background
files) and `pytest` (for the test suite). `openai` and `anthropic` are
also listed but are only actually *used* if you set the corresponding
API key — demo mode works with neither installed.

To enable LLM mode, set:

```bash
export OPENAI_API_KEY="sk-..."
```

An Anthropic (Claude) backend is also supported as a secondary option
— set `ANTHROPIC_API_KEY` instead if you'd rather use that. If both are
set, OpenAI is used. You can force demo mode even with a key set via
`--demo`.

## Usage

```bash
python3 -m generator.cli \
  --background examples/background.yaml \
  --job-description examples/job_description.txt \
  --output-dir .
```

This writes `resume_bullets.md` and `cover_letter.md` into
`--output-dir` (defaults to the current directory).

### CLI options

| Flag | Short | Required | Description |
|---|---|---|---|
| `--background PATH` | `-b` | yes | Path to a `.yaml`/`.yml`/`.json` background file |
| `--job-description PATH` | `-j` | yes | Path to a plain-text job description file |
| `--output-dir PATH` | `-o` | no | Where to write the two output files (default: `.`) |
| `--company NAME` | | no | Override the company name used in the cover letter |
| `--demo` | | no | Force demo (keyword-matching) mode even if an API key is set |

### Example run (demo mode, no API key set)

```
$ python3 -m generator.cli -b examples/background.yaml -j examples/job_description.txt -o /tmp/out
No OPENAI_API_KEY or ANTHROPIC_API_KEY found. Running in demo mode: using keyword matching, not an LLM.
Mode: demo
Wrote /tmp/out/resume_bullets.md
Wrote /tmp/out/cover_letter.md
```

**Excerpt of `resume_bullets.md`:**

```markdown
# Tailored Resume Bullets for Jordan Alvarez

> _Generated in **demo mode** (no `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` found) using deterministic keyword matching, not an LLM. Set one of those environment variables for genuinely tailored, freshly written content._

## Skills to Highlight (matched to this job)

Python, Django, PostgreSQL, AWS, Docker, CI/CD, Kubernetes, Data pipelines, SQL, Agile/Scrum, Mentoring, System design, Unit testing

## Job Keywords Not Yet Reflected in Your Background

Consider addressing these in your resume or cover letter if you have relevant experience: services, millions, engineering, write

## Bullets by Role

### Senior Software Engineer, Northlake Analytics (2022 - Present)

- Led the redesign of the core billing service, migrating a monolithic Django app to a set of REST APIs and cutting average response time by 45%. _(relevant: apis, design, rest)_
- Built a data pipeline processing 2M+ events per day using Python and PostgreSQL, replacing a brittle nightly batch job with near real-time updates. _(relevant: data, events, python)_
...
```

**Excerpt of `cover_letter.md`:**

```markdown
# Cover Letter

> _Generated in **demo mode** ..._

jordan.alvarez@example.com | 555-201-4488 | Austin, TX

September 3, 2026

Dear Hiring Manager at Riverstone Digital,

I am writing to apply for the Backend Software Engineer position at Riverstone Digital. As a Senior Software Engineer with hands-on experience in Python, Django, PostgreSQL, AWS, Docker, I am confident I can contribute quickly and meaningfully to your team.

A few highlights from my background that align closely with what you're looking for in this role:

- Developed and maintained REST APIs in Python/Django powering a B2B SaaS platform with over 500 enterprise customers.
- Led the redesign of the core billing service, migrating a monolithic Django app to a set of REST APIs and cutting average response time by 45%.
- Built a data pipeline processing 2M+ events per day using Python and PostgreSQL, replacing a brittle nightly batch job with near real-time updates.

Your posting emphasizes Python, Django, PostgreSQL, AWS, Docker, CI/CD, all areas where I have direct, applied experience -- not just familiarity.

I would welcome the opportunity to discuss how my background can support Riverstone Digital's goals for this role. Thank you for your time and consideration.

Sincerely,
Jordan Alvarez
```

Run the same command with `OPENAI_API_KEY` set (and the `openai`
package installed) to get freshly written, LLM-generated content
instead — same CLI, same output files, the `Mode:` line in the console
output tells you which path ran.

## Input file format

### Background file (`--background`)

YAML (or equivalent JSON) with this shape. `name`, `skills`, and
`experience` are required; everything else is optional but improves
output quality.

```yaml
name: Jordan Alvarez
email: jordan.alvarez@example.com
phone: "555-201-4488"
location: Austin, TX
linkedin: linkedin.com/in/jordan-alvarez-example

summary: >
  A couple of sentences describing your overall profile.

skills:
  - Python
  - Django
  - PostgreSQL
  # ... a flat list of skills/tools/technologies

experience:
  - title: Senior Software Engineer
    company: Northlake Analytics
    dates: "2022 - Present"
    achievements:
      - Led the redesign of the core billing service, cutting response time by 45%.
      - Mentored 3 junior engineers through onboarding and code review.
  # ... one entry per role, most recent first

education:
  - degree: B.S. in Computer Science
    school: University of Texas at Austin
    year: "2019"

certifications:
  - AWS Certified Solutions Architect - Associate
```

See [`examples/background.yaml`](examples/background.yaml) for a full,
realistic example. A `.json` file with the same structure works too —
the CLI picks the parser based on file extension.

### Job description file (`--job-description`)

Plain text — paste the job posting as-is. The tool works better if the
first line or an early `Job Title:` / `Company:` line names the role
and employer (see [`examples/job_description.txt`](examples/job_description.txt)),
but it will still produce reasonable output from an unstructured
posting; you can also always override the company name with
`--company`.

## Project structure

```
resume-cover-letter-generator/
├── generator/
│   ├── __init__.py
│   ├── matcher.py      # keyword extraction + background/JD matching (no API key needed)
│   ├── templates.py    # demo-mode Markdown rendering (no API key needed)
│   ├── llm.py           # OpenAI-backed generation
│   └── cli.py           # argument parsing, file I/O, mode selection
├── examples/
│   ├── background.yaml
│   └── job_description.txt
├── tests/
│   ├── test_matcher.py
│   └── test_templates.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Running the tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

All 20 tests cover `generator/matcher.py` and `generator/templates.py`
only — pure Python logic with no network calls and no API key
required, so they run the same way in CI as on your machine.

## Notes & limitations

- Demo mode uses simple frequency-based keyword extraction and
  substring matching — it's good enough to produce a coherent,
  genuinely useful first draft, but it won't paraphrase or invent
  wording the way an LLM will. That's intentional: it's a transparent,
  zero-cost fallback, not a second AI engine.
- LLM mode is explicitly instructed not to fabricate employers,
  titles, or achievements — it rewrites and prioritizes what's in your
  background file, it doesn't invent new accomplishments. Always
  proofread the output before sending it anywhere.
- `resume_bullets.md` and `cover_letter.md` are the CLI's default
  output filenames; re-running the tool overwrites them, so pass a
  different `--output-dir` per job application if you want to keep
  multiple drafts around.

## License

MIT — see [LICENSE](LICENSE).
