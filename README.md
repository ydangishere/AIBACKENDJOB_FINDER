# AI Backend Job Finder

Automated tool that scrapes job listings from TopCV or ITviec, uses an LLM to identify backend-related jobs, then displays results in a desktop window.

---

## How to Run (Step-by-Step)

**Prerequisites:** Installation and configuration done (see below).

### Step 1: Start the app

- **Windows:** Double-click `run_ui.bat` in the project folder
- **Mac:** Double-click `run_ui.sh` in the project folder (or open Terminal, run `chmod +x run_ui.sh` once, then `./run_ui.sh`)
- A single window titled **"AI Backend Job Finder"** will open

### Step 2: Enter your OpenAI API key

- In the first input field (labeled **"OpenAI API key"**), paste your key
- Format: `sk-...` (starts with `sk-`)
- Don't have a key? Get one at https://platform.openai.com/api-keys (new accounts get free credits)
- If you already set the key in config or environment, you can leave this blank

### Step 3: Paste a job link

- In the text area (labeled **"Link ITviec hoặc TopCV"**), paste one of these URLs:

  - **ITviec:** `https://itviec.com/it-jobs`
  - **TopCV:** `https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026` ← paste this link for TopCV

- Or paste any other job listing page or single job URL from ITviec or TopCV

### Step 4: Run the scraper

- Click the **"Run Scraper & Analysis"** button
- Wait while the app scrapes and analyzes (status shows "Đang scrape..." then "Đang phân tích LLM...")

### Step 5: View results

- Results appear in the **"Kết quả"** area below
- Each job shows: Job title, Company, Requirements (skills), Link
- Copy the link to open the job in your browser

### Step 6: Close the app

- Close the window when done

---

## Installation

**Directory:** `d:\AI\AIbackendjobscraper`

```powershell
cd d:\AI\AIbackendjobscraper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

**Note:** `playwright install chromium` downloads a headless browser (only needed for ITviec). TopCV does not require Playwright.

## Configuration

1. **OpenAI API key** (required for LLM):
   ```powershell
   $env:OPENAI_API_KEY = "sk-..."
   ```
   Or edit `config.py`: `OPENAI_API_KEY = "sk-..."`

2. **Job source** in `config.py`:
   - `JOB_SOURCE = "topcv"` (default, no Cloudflare)
   - `JOB_SOURCE = "itviec"` – uses FlareSolverr to bypass Cloudflare. Run Docker first:
     ```powershell
     docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
     ```

3. **Notification mode** in `config.py`:
   - `NOTIFICATION_MODE = "json"` – save to `results.json`
   - `NOTIFICATION_MODE = "print"` – print to terminal
   - `NOTIFICATION_MODE = "email"` – send email (requires SMTP config)

## Supported links

| Source | Link |
|--------|------|
| **ITviec** (IT jobs listing) | `https://itviec.com/it-jobs` |
| **TopCV** (IT software jobs listing) | `https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026` |

**Note:** ITviec requires FlareSolverr (Docker) to be running. TopCV works without it.

## Using ITviec with FlareSolverr

1. Install Docker and run FlareSolverr:
   ```powershell
   docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
   ```
2. In `config.py`: `JOB_SOURCE = "itviec"`
3. Run the app via `run_ui.bat` and paste an ITviec link.

If FlareSolverr runs on a different host/port: `$env:FLARESOLVERR_URL = "http://host:8191/v1"`

## Email notification

1. In `config.py`: `NOTIFICATION_MODE = "email"`
2. Set `EMAIL_TO` (recipient address)
3. Create a Gmail App Password at https://myaccount.google.com/apppasswords (requires 2-Step Verification)
4. Set `EMAIL_APP_PASSWORD` in `config.py` or: `$env:EMAIL_APP_PASSWORD = "xxxx-xxxx-xxxx-xxxx"`

## Sample output

```json
[
  {
    "title": "Senior Java Engineer",
    "company": "ABC Fintech",
    "skills": ["Java", "Spring Boot", "REST API"],
    "link": "https://itviec.com/it-jobs/..."
  }
]
```

## Project structure

```
ai-job-finder/
├── scraper.py      # Scrape TopCV (requests) or ITviec (FlareSolverr/Playwright)
├── llm_filter.py   # Job analysis via OpenAI
├── notifier.py     # JSON / print / email output
├── main.py         # Main pipeline
├── config.py       # Configuration
├── app.py          # Desktop UI (tkinter)
├── run_ui.bat      # Run UI on Windows (double-click)
├── run_ui.sh       # Run UI on Mac (./run_ui.sh)
├── results.json    # Output (auto-created)
└── requirements.txt
```
