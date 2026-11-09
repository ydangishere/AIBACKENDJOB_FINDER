"""Cloud-first job research and CV tailoring. No Windows filesystem required."""
import datetime as dt
import html
import json
import os
import pathlib
import re
import requests
from bs4 import BeautifulSoup

OUT = pathlib.Path(__file__).parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
TZ = dt.timezone(dt.timedelta(hours=7))
TODAY = dt.datetime.now(TZ).date()
CUTOFF = TODAY - dt.timedelta(days=7)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobResearchBot/1.0)"}
QUERIES = [
    '"AI Engineer" "Ho Chi Minh" jobs',
    '"AI Solution Architect" "Ho Chi Minh" hiring',
    '"UI UX Designer" "Ho Chi Minh" jobs',
    '"Product Designer" "Ho Chi Minh" hiring',
]

def discover():
    """Search public Bing RSS. Search results are leads, NEVER verified jobs."""
    leads = []
    for query in QUERIES:
        try:
            response = requests.get("https://www.bing.com/search",
                params={"q": query, "format": "rss"}, headers=HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "xml")
            for item in soup.find_all("item")[:15]:
                link = item.find("link")
                title = item.find("title")
                if not link or not title:
                    continue
                url = link.get_text(strip=True)
                if not url.startswith("https://"):
                    continue
                leads.append({"query": query, "position": title.get_text(strip=True),
                              "jd_url": url, "source": "Bing RSS",
                              "verification": "unverified"})
        except (requests.RequestException, ValueError) as exc:
            print(f"Discovery failed for {query}: {exc}")
    return list({x["jd_url"]: x for x in leads}.values())

def verify(lead):
    """Conservative gate: date and accepting-applications evidence must be explicit."""
    try:
        r = requests.get(lead["jd_url"], headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code != 200 or len(r.text) < 200:
            return None, "Page inaccessible"
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        body = " ".join(soup.stripped_strings)[:20000]
        if not re.search(r"Ho Chi Minh|Hồ Chí Minh|HCMC|Saigon|Sài Gòn|Vietnam remote", body, re.I):
            return None, "HCMC eligibility not evidenced"
        if re.search(r"job closed|no longer accepting|expired|đã hết hạn|ngừng nhận", body, re.I):
            return None, "Closed/expired"
        # Publication timestamp and application status are NOT safely inferable from snippets.
        return None, "Publication date and active application status not independently verified"
    except requests.RequestException:
        return None, "Page could not be opened"

def drive_token():
    keys = ["GOOGLE_DRIVE_REFRESH_TOKEN", "GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET"]
    if not all(os.getenv(k) for k in keys):
        return None
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_DRIVE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_DRIVE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_DRIVE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=20)
    response.raise_for_status()
    return response.json()["access_token"]

def drive_list(token, parent):
    r = requests.get("https://www.googleapis.com/drive/v3/files", params={
        "q": f"'{parent}' in parents and trashed = false",
        "fields": "nextPageToken,files(id,name,mimeType,webViewLink)",
        "page_size": 100}, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    r.raise_for_status()
    return r.json().get("files", [])

def drive_upload(token, parent, name, content, mime="application/json"):
    metadata = {"name": name, "parents": [parent]}
    r = requests.post("https://www.googleapis.com/upload/drive/v3/files",
        params={"uploadType": "multipart", "fields": "id,name,webViewLink"},
        headers={"Authorization": f"Bearer {token}"},
        files={"metadata": ("metadata", json.dumps(metadata), "application/json"),
               "file": (name, content.encode("utf-8"), mime)}, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    leads = discover()
    excluded = []
    jobs = []
    for lead in leads:
        verified, reason = verify(lead)
        if verified:
            jobs.append(verified)
        else:
            excluded.append({"company": "Unverified", "position": lead["position"],
                             "reason": reason, "source_url": lead["jd_url"]})
    report = {"run_date_local": str(TODAY), "window_start_local": str(CUTOFF),
              "window_end_local": str(TODAY), "jobs": jobs, "excluded": excluded,
              "facebook_private_groups": "not connected; no access claimed"}
    filename = f"jobs-{TODAY}.json"
    (OUT / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    token = drive_token()
    status = {"leads": len(leads), "verified_jobs": len(jobs),
              "agent2": "not run: no independently verified JD",
              "facebook": "not connected"}
    if token:
        try:
            folders = drive_list(token, os.environ["CV_FOLDER_ID"])
            status["cv_folder_count"] = len(folders)
            status["cv_template_folders"] = [f["name"] for f in folders if f["mimeType"] == "application/vnd.google-apps.folder"]
            status["drive_manifest"] = drive_upload(token, os.environ["JD_FOLDER_ID"],
                filename, json.dumps(report, ensure_ascii=False, indent=2))
        except (requests.RequestException, KeyError) as exc:
            status["drive_error"] = str(exc)
    else:
        status["drive_error"] = "Google Drive OAuth secrets not configured"
    (OUT / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
