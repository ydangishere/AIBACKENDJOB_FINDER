# Weekly Multi-Agent Job Finder — GPT-6-Sol High

New independent-agent pipeline alongside the original repository scraper (unchanged).

## Architecture

1. GitHub Actions triggers Monday at 04:00 (Asia/Ho_Chi_Minh), or via manual "Run workflow".
2. A deterministic Python Orchestrator runs three **separate OpenAI Agents SDK agents** through Runner.run.
3. Agent 1: Web research on HCMC AI, LLM/RAG, Product Design and UI/UX jobs; verifies real URLs and dates, merges an accumulated list of historical job leads without dropping any.
4. Agent 2: Reads original CV, proposes truthful Position Applied and Introduction edits; Python code copies the **full original** HTML/other assets into a job-specific subfolder **under the Google Drive updated folder**, updates HTML via Drive API, reads back bytes, creates and checks PDF when browser is available.
5. Agent 3: Reviews outcomes and blockers. **The full table is rendered deterministically by Python**, so a model cannot omit jobs in its final report.

Every agent is explicitly pinned to the API model `gpt-6-sol` with `reasoning.effort=high`. There is **no lower-model fallback**: an unsupported model or missing key fails the live run.

## Important: safe default, not live yet

Workflow is deployed with **DRY_RUN by default**. A weekly scheduled dry-run does not invoke any model or change Google Drive. This protects against surprise API charges. A successful dry-run does not mean the entire workflow works.

To enable a real weekly run, set the following GitHub repository **Actions secrets** using an authorized OpenAI API account and Google OAuth account:

- `OPENAI_API_KEY` — requires separately billed OpenAI API access (ChatGPT Plus does not include API tokens).
- `GOOGLE_DRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET`
- `GOOGLE_DRIVE_REFRESH_TOKEN` — must have OAuth Drive write scope on the same account owning the CVs.

Then test **Actions → Weekly independent GPT-6-Sol agents → Run workflow → live**. Only after a successful live test, set the repository Actions **variable** `LIVE_ENABLED=true`.

No API key, Google OAuth refresh token, billing, or browser access has been provisioned by this commit. Do not claim the system has performed a live full run before verifying it.

## Commands

Install: `pip install -r multi_agent/requirements.txt`

Safe local dry-run: `python multi_agent/run.py`

Live run, after setting the environment variables and running `python -m playwright install chromium`: `python multi_agent/run.py --live`

## Output

- 25 historical leads initialized in `multi_agent/data/master_jobs.json`; all begin as **unverified**, not magically current jobs.
- A full report with every lead is written to `multi_agent/output/report.md`, to GitHub Actions job summary, and an Actions artifact.
- CVs go **only** to the connected Google Drive `updated` folder ID `1LGIhOhVuPbHjhHjX3w52rmDDLKABeHtM`, in private job-specific subfolders. CVs are **never committed to GitHub**.
- The earlier 5 publicly committed CV HTML files are separate legacy artifacts. This new workflow does not update them.
- The new GitHub Actions run does not automatically send a report into a ChatGPT Project; a separate authorized notification integration is required. The existing ChatGPT Scheduled Task remains independent until the new pipeline is confirmed.
- No automatic job application, email, or personal-data outbound dispatch.

## Limitations / TODO

- Date validation requires the exact cited posting-date text to be present on the destination JD page; blocked sites remain unverified.
- Google OAuth refresh-token setup must be done by an authorized user. Without it, Agent 2 cannot write CVs to Drive.
- Full live test depends on real credentials and API spend. Do not silently downgrade model or switch storage target.
