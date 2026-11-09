"""Deterministic orchestrator over three independent GPT-6-Sol Agents.

Dry-run is the default. Never commits CV content to GitHub.
"""
import argparse
import asyncio
from datetime import date, datetime, timedelta, timezone
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent
MASTER = BASE / "data" / "master_jobs.json"
REPORT = BASE / "output" / "report.md"
MODEL = "gpt-6-sol"
EFFORT = "high"
UPDATED_FOLDER = "1LGIhOhVuPbHjhHjX3w52rmDDLKABeHtM"
SOURCE_FOLDERS = {
    "AI": "1GeQuwE3ACU9Ju-4AQmizo94x-TuvoFxu",
    "UX": "1KoKa3M6ZWe67FsjpHJdnYpspCvWHvrkc",
}
SOURCE_HTML = {
    "AI": "15OobItVkc_Omj6qIOklXEZj8Ds0juanN",
    "UX": "1w3DY88K3P99WCiwfHOnuMB1t9kgDs_rE",
}


def normalize(value):
    return re.sub(r"\W+", "", str(value).casefold())


def key(job):
    return normalize(job.get("company", "")) + ":" + normalize(job.get("position", ""))


def load_master():
    value = json.loads(MASTER.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("Master job list is missing or empty")
    return value


def merge_jobs(master, new_jobs):
    rows = {key(job): dict(job) for job in master}
    for job in new_jobs:
        if not job.get("company") or not job.get("position"):
            continue
        identity = key(job)
        previous = rows.get(identity, {})
        merged = {**previous}
        for field, value in job.items():
            if value is not None and value != "":
                merged[field] = value
        merged.setdefault("status", "unverified")
        rows[identity] = merged
    if len(rows) < len({key(j) for j in master}):
        raise RuntimeError("Master list lost rows")
    return list(rows.values())


def verify_recent(job):
    """Never mark a posting verified-new without independent date and link evidence."""
    url = job.get("url") or ""
    posted = job.get("posted_on") or ""
    evidence = job.get("date_evidence") or ""
    if not url.startswith("https://") or not evidence:
        return "unverified", "Missing direct HTTPS URL or dated source evidence"
    if "linkedin.com" in (urlparse(url).hostname or "").lower():
        return "unverified", "LinkedIn is not an accessible application URL for this user"
    try:
        when = date.fromisoformat(posted)
        today = datetime.now(timezone(timedelta(hours=7))).date()
        if when > today or (today - when).days > 7:
            return "old_or_future", "Outside the last seven days"
    except ValueError:
        return "unverified", "No exact ISO posting date"
    try:
        response = requests.get(url, timeout=20, allow_redirects=True,
                                headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        if "linkedin.com" in (urlparse(response.url).hostname or "").lower():
            return "unverified", "Application redirects to LinkedIn"
        text = re.sub(r"\s+", " ", response.text).casefold()
        if re.sub(r"\s+", " ", evidence).casefold() not in text:
            return "unverified", "Posting-date evidence not independently found on the page"
        return "verified_new", "Exact posting-date evidence found on accessible job page"
    except Exception as exc:
        return "unverified", f"Could not verify application URL: {type(exc).__name__}"


def decide_cv_type(position):
    value = position.casefold()
    if any(x in value for x in ("ui", "ux", "designer", "design lead", "researcher")):
        return "UX"
    if any(x in value for x in ("ai", "llm", "agent", "rag")):
        return "AI"
    return None


def apply_html_changes(html, position, summary):
    title_re = r"(<p><strong>Position Applied:</strong>\s*)([^<]*)(</p>)"
    html, count = re.subn(title_re, lambda m: m.group(1) + escape(position) + m.group(3), html, count=1)
    if count != 1:
        raise ValueError("Position Applied field not found in original CV")
    intro_re = r"(<h2>(?:Introduction|Professional Summary)</h2>\s*<p>)([\s\S]*?)(</p>)"
    html, count = re.subn(intro_re, lambda m: m.group(1) + escape(summary) + m.group(3), html, count=1)
    if count != 1:
        raise ValueError("Introduction/Professional Summary not found in original CV")
    html, _ = re.subn(r"<title>[^<]*</title>",
                       lambda m: "<title>CV - Dang Van Y - " + escape(position) + "</title>",
                       html, count=1)
    return html


def drive_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    required = ("GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing Google Drive OAuth secrets: " + ", ".join(missing))
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_DRIVE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_DRIVE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_DRIVE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_children(drive, folder_id):
    query = "'" + folder_id.replace("'", r"\'") + "' in parents and trashed = false"
    found = []
    token = None
    while True:
        response = drive.files().list(
            q=query,
            fields="nextPageToken,files(id,name,mimeType)",
            page_size=100,
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        found.extend(response.get("files", []))
        token = response.get("nextPageToken")
        if not token:
            return found


def ensure_folder(drive, parent, name):
    for file in list_children(drive, parent):
        if file["name"] == name and file.get("mimeType") == "application/vnd.google-apps.folder":
            return file["id"]
    return drive.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]},
        fields="id",
    ).execute()["id"]


def fetch_bytes(drive, file_id):
    content = drive.files().get_media(fileId=file_id).execute()
    if not isinstance(content, bytes):
        raise RuntimeError("Drive returned non-binary content")
    return content


def replace_bytes(drive, file_id, data, mime):
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(BytesIO(data), mimetype=mime, resumable=False)
    drive.files().update(fileId=file_id, media_body=media, fields="id,size").execute()
    if fetch_bytes(drive, file_id) != data:
        raise RuntimeError("Drive write/read-back byte verification failed")


async def render_pdf(html, image_files):
    from playwright.async_api import async_playwright
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "index.html").write_text(html, encoding="utf-8")
        for name, content in image_files.items():
            if "/" not in name and "\\" not in name:
                (base / name).write_bytes(content)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            await page.goto((base / "index.html").as_uri(), wait_until="load")
            output = base / "updated.pdf"
            await page.pdf(path=str(output), format="A4", print_background=True)
            await browser.close()
            return output.read_bytes()


async def write_cv(drive, job, position, summary):
    """Create a private, job-specific folder INSIDE Google Drive's updated folder."""
    category = decide_cv_type(job["position"])
    if category is None:
        return {"status": "not_target_role"}
    suffix = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", job["company"] + "_" + job["position"])[:90]
    folder_id = ensure_folder(drive, UPDATED_FOLDER, suffix + "_" + safe)
    source_assets = list_children(drive, SOURCE_FOLDERS[category])
    destination_assets = {f["name"]: f for f in list_children(drive, folder_id)}
    source_html_bytes = fetch_bytes(drive, SOURCE_HTML[category])
    tailored_html = apply_html_changes(source_html_bytes.decode("utf-8"), position, summary)
    for asset in source_assets:
        name = asset["name"]
        if name not in destination_assets:
            copied = drive.files().copy(fileId=asset["id"],
                body={"name": name, "parents": [folder_id]}, fields="id,name").execute()
            destination_assets[name] = copied
    if "index.html" not in destination_assets:
        copied = drive.files().copy(fileId=SOURCE_HTML[category],
            body={"name": "index.html", "parents": [folder_id]}, fields="id,name").execute()
        destination_assets["index.html"] = copied
    replace_bytes(drive, destination_assets["index.html"]["id"],
                  tailored_html.encode("utf-8"), "text/html")
    result = {"status": "html_verified", "folder": "https://drive.google.com/drive/folders/" + folder_id}
    images = {}
    for asset in source_assets:
        if asset["name"].lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
            images[asset["name"]] = fetch_bytes(drive, asset["id"])
    try:
        pdf = await render_pdf(tailored_html, images)
        existing_pdf = next((x for n, x in destination_assets.items() if n.lower().endswith(".pdf")), None)
        if existing_pdf:
            replace_bytes(drive, existing_pdf["id"], pdf, "application/pdf")
        else:
            from googleapiclient.http import MediaIoBaseUpload
            uploaded = drive.files().create(
                body={"name": "CV.pdf", "parents": [folder_id]},
                media_body=MediaIoBaseUpload(BytesIO(pdf), mimetype="application/pdf"),
                fields="id",
            ).execute()
            if fetch_bytes(drive, uploaded["id"]) != pdf:
                raise RuntimeError("PDF read-back mismatch")
        result["status"] = "html_and_pdf_verified"
    except Exception as exc:
        result["pdf_issue"] = f"{type(exc).__name__}: {exc}"
    return result


def markdown_report(rows, notes, run_mode):
    lines = [
        "# Complete job report",
        "",
        "Run mode: " + run_mode,
        "Model (live only): " + MODEL + "; reasoning effort: " + EFFORT,
        "Total unique job leads: " + str(len(rows)),
        "Verified recent jobs: " + str(sum(j.get("status") == "verified_new" for j in rows)),
        "CVs completed: " + str(sum(j.get("cv_status") == "html_and_pdf_verified" for j in rows)),
        "",
        str(notes or ""),
        "",
        "| # | Company | Position | Source | JD link | Posted | Status | CV |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, job in enumerate(rows, 1):
        cells = [str(i), job.get("company"), job.get("position"), job.get("source"),
                 job.get("url") or "not verified", job.get("posted_on") or "unknown",
                 job.get("status") or "unverified",
                 job.get("cv_folder") or job.get("cv_status") or "not created"]
        lines.append("| " + " | ".join(str(c or "").replace("|", r"\|").replace("\n", " ") for c in cells) + " |")
    return "\n".join(lines) + "\n"


def checkpoint(rows, notes, run_mode="LIVE"):
    """Persist all leads and the FULL report after each completed agent stage."""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(markdown_report(rows, notes, run_mode), encoding="utf-8")
    if run_mode == "LIVE":
        MASTER.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def run_live(rows):
    from agents import Agent, ModelSettings, Runner, WebSearchTool
    from openai.types.shared import Reasoning
    from pydantic import BaseModel, Field

    required = ("OPENAI_API_KEY", "GOOGLE_DRIVE_CLIENT_ID",
                "GOOGLE_DRIVE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Refusing incomplete paid live run; missing credentials: " + ", ".join(missing))

    # Fail before paid LLM calls when Drive OAuth lacks access to 'updated'.
    drive = drive_client()
    folder = drive.files().get(
        fileId=UPDATED_FOLDER,
        fields="id,mimeType,capabilities(canAddChildren)",
        supportsAllDrives=True,
    ).execute()
    if folder.get("mimeType") != "application/vnd.google-apps.folder":
        raise RuntimeError("The 'updated' destination is not a Google Drive folder")
    if not folder.get("capabilities", {}).get("canAddChildren", False):
        raise RuntimeError("Google Drive OAuth lacks write permission in 'updated'")

    class JobLead(BaseModel):
        company: str
        position: str
        source: str
        url: str | None = None
        posted_on: str | None = None
        date_evidence: str | None = None
        location: str | None = None
        salary: str | None = None

    class ResearchResult(BaseModel):
        jobs: list[JobLead] = Field(default_factory=list)

    class CVPlan(BaseModel):
        position_applied: str
        summary: str

    class ReportNotes(BaseModel):
        summary: str
        remaining_issues: str

    def agent(name, instructions, output_type, tools=None):
        return Agent(name=name, instructions=instructions, output_type=output_type,
                     tools=tools or [], model=MODEL,
                     model_settings=ModelSettings(reasoning=Reasoning(effort=EFFORT)))

    finder = agent("Agent 1 — Job Finder",
        "Search for HCMC or HCMC-eligible remote roles in AI Engineering, AI Solutions, LLM/RAG/Agents, UI/UX and Product Design. "
        "Find jobs posted during the last seven days. Use primary original JD pages and cross-check employers, dates, status. "
        "Return ALL leads found with original URL and exact on-page date evidence when possible; never invent dates, URLs, or claims. "
        "Look across ITviec, TopCV, company career pages, public Facebook, VietnamWorks; treat LinkedIn only as discovery. "
        "Never silently drop old or unverifiable jobs.", ResearchResult,
        [WebSearchTool(search_context_size="high")])

    tailor = agent("Agent 2 — CV Adjuster",
        "Given the complete original CV information and a JD, produce only a truthful, specific position title and concise "
        "Professional Summary/Introduction. Never fabricate employment, skills or certifications. "
        "Do not write to GitHub; the deterministic controller saves the modified original HTML to private Google Drive.",
        CVPlan)

    reporter = agent("Agent 3 — Reporter",
        "Review the provided aggregated jobs and CV statuses. Return a compact Vietnamese summary and explicit outstanding issues. "
        "Do not omit any jobs; the controller renders every job row without your discretion. Never claim incomplete as complete.",
        ReportNotes)

    result = await Runner.run(finder,
        "Today's date is " + str(datetime.now(timezone(timedelta(hours=7))).date()) +
        ". Search HCMC jobs and provide original verifiable links and dates. "
        "Previously recorded leads (do not assume current): " +
        json.dumps([{"company": j.get("company"), "position": j.get("position")}
                    for j in rows], ensure_ascii=False))
    discovered = [job.model_dump() for job in result.final_output.jobs]
    rows = merge_jobs(rows, discovered)
    new_keys = {key(job) for job in discovered}
    for row in rows:
        if key(row) in new_keys:
            row["status"], row["verification_note"] = verify_recent(row)
        else:
            row["status"] = "unverified"
            row["verification_note"] = "Previous lead not reverified this run"
    checkpoint(rows, "Agent 1 completed. Agent 2 and Agent 3 are pending.")
    eligible = [row for row in rows if row["status"] == "verified_new" and decide_cv_type(row["position"])]
    for row in eligible:
        try:
            original = fetch_bytes(drive, SOURCE_HTML[decide_cv_type(row["position"])]).decode("utf-8")
            description = "Target JD: " + json.dumps(row, ensure_ascii=False)
            plan = await Runner.run(tailor,
                "Existing CV source (do not invent experience): " + re.sub(r"<[^>]+>", " ", original)[:13500]
                + "\n" + description)
            result_cv = await write_cv(drive, row,
                plan.final_output.position_applied, plan.final_output.summary)
            row["cv_status"] = result_cv["status"]
            row["cv_folder"] = result_cv.get("folder")
            if result_cv.get("pdf_issue"):
                row["cv_issue"] = result_cv["pdf_issue"]
        except Exception as exc:
            row["cv_status"] = "blocked"
            row["cv_issue"] = f"{type(exc).__name__}: {exc}"
        finally:
            checkpoint(rows, "Agent 1 complete. Agent 2 result recorded. Agent 3 pending.")
    checkpoint(rows, "Agent 1 and Agent 2 finished; Agent 3 pending.")
    reviewed = await Runner.run(reporter,
        json.dumps([{"company": x.get("company"), "position": x.get("position"),
                     "status": x.get("status"), "cv_status": x.get("cv_status")}
                    for x in rows], ensure_ascii=False))
    notes = reviewed.final_output.summary + "\n\nUnfinished: " + reviewed.final_output.remaining_issues
    checkpoint(rows, notes)
    return rows, notes


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Requires OpenAI API and Google Drive OAuth")
    args = parser.parse_args()
    rows = load_master()
    if args.live:
        rows, notes = await run_live(rows)
    else:
        notes = "DRY RUN ONLY: no API calls, no independent agents invoked, no Google Drive writes."
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(markdown_report(rows, notes, "LIVE" if args.live else "DRY_RUN"), encoding="utf-8")
    if args.live:
        MASTER.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(REPORT.read_text(encoding="utf-8"))
    print("Report:", REPORT, "| jobs:", len(rows), "| live:", args.live)


if __name__ == "__main__":
    asyncio.run(main())
