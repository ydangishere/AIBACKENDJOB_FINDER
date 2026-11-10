# Weekly Multi-Agent Job Finder — GPT-6-Sol High

New independent-agent pipeline alongside the original repository scraper (unchanged).

## Architecture

1. GitHub Actions triggers Monday at 04:00 (Asia/Ho_Chi_Minh), or via manual "Run workflow".
2. A deterministic Python Orchestrator runs three **separate OpenAI Agents SDK agents** through Runner.run.
3. Agent 1: Two independent research passes (AI/LLM and UI/UX/Product Design). Searches accessible public sources, records short JD-specific requirements, checks direct URLs and dates conservatively, and retains all 25 prior leads even when unverified. It does NOT claim to access private Facebook groups or independently run Codex research.
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

## One-time Google Drive OAuth setup (local computer)

Google Drive linked to ChatGPT does not automatically provide an OAuth refresh token to Python running on GitHub Actions. To grant the Python service access without sharing passwords:

1. In Google Cloud Console, create an OAuth consent screen and OAuth Client ID of type **Desktop app** under a project you control. Ensure your Google account is allowed as a test user if the consent screen is in Testing mode.
2. Download the OAuth client JSON as `multi_agent/google_oauth_client.json` locally. Never commit or upload it.
3. Install dependencies and run `python multi_agent/setup_drive_oauth.py` **on your own computer**; sign into the Google account that owns the `updated` folder and approve Drive access.
4. Before relying on a weekly unattended refresh token, ensure **Google Auth Platform → Audience** is configured for a production-grade OAuth grant. For External apps in **Testing**, Google generally expires refresh tokens in **7 days** when using Drive scopes, so a weekly job would break. Where applicable, move the app to **In production** and review Google's verification requirements for the scopes requested.
5. The script writes three secrets into a local ignored file `multi_agent/.env.drive.secrets`. Enter these three values in GitHub → repository Settings → Secrets and variables → Actions → Repository secrets. Do not paste them into chat.
6. In OpenAI Platform, first open https://platform.openai.com/settings/organization/billing/overview and set up API billing under your own account, then create a project API key at https://platform.openai.com/api-keys. Add that key as `OPENAI_API_KEY` in the same repository secrets area. This requires an OpenAI API account with billing.
7. From GitHub Actions, manually run **Weekly independent GPT-6-Sol agents** with `live=true`; inspect the complete 25+ job table, CV Google Drive folders, and logs. Enable the Actions variable `LIVE_ENABLED=true` **only after a verified successful live run**.

**Important security:** The Drive permission scope is broad because the pipeline must read existing templates and write new CV files. Keep secrets in GitHub Actions Secrets, never repository files. If access is no longer needed, revoke the OAuth grant in Google Account settings. The five CV files deleted from the branch may still exist in git history.

## Quality gates

- `.github/workflows/test-multi-agent.yml` runs Python syntax validation, offline regression tests, full 25-lead dry-run report check, and timezone validation on relevant pushes.
- The live workflow refuses a paid run when required GitHub Secrets are missing, or Google Drive `updated` is not writable.
- The orchestrator checkpoints the complete job report and master after each agent stage, so an Agent 2/3 failure does not silently lose the job list.
- CVs are written to Drive, read back byte-for-byte, and PDFs are checked when created.
- Github Actions holds job metadata and report artifacts, never CV HTML or PDF bytes.

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
- The five CV HTML files mistakenly committed earlier have now been removed from the active GitHub branch. Their bytes may remain accessible in Git history until repository history is purged separately.
- The new GitHub Actions run does not automatically send a report into a ChatGPT Project; a separate authorized notification integration is required. The existing ChatGPT Scheduled Task remains independent until the new pipeline is confirmed.
- No automatic job application, email, or personal-data outbound dispatch.

## Limitations / TODO

- Date validation requires the exact cited posting-date text to be present on the destination JD page; blocked sites remain unverified.
- Google OAuth refresh-token setup must be done by an authorized user. Without it, Agent 2 cannot write CVs to Drive.
- Full live test depends on real credentials and API spend. Do not silently downgrade model or switch storage target.
