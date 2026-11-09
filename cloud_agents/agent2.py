"""Agent 2: copy a Drive HTML CV and tailor only permitted sections, preserving original."""
import json
import os
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"

def headers(token):
    return {"Authorization": f"Bearer {token}"}

def children(token, folder):
    result = []
    page = None
    while True:
        r = requests.get(API, headers=headers(token), params={
            "q": f"'{folder}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType,webViewLink)",
            "pageSize": 100, **({"pageToken": page} if page else {})}, timeout=30)
        r.raise_for_status()
        data = r.json()
        result.extend(data.get("files", []))
        page = data.get("nextPageToken")
        if not page:
            return result

def download_text(token, file_id):
    r = requests.get(f"{API}/{file_id}", headers=headers(token),
                     params={"alt": "media"}, timeout=30)
    r.raise_for_status()
    return r.text

def make_folder(token, parent, name):
    r = requests.post(API, headers={**headers(token), "Content-Type": "application/json"},
        json={"name": name, "mimeType": "application/vnd.google-apps.folder",
              "parents": [parent]}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def copy_file(token, source, parent, name=None):
    body = {"parents": [parent]}
    if name:
        body["name"] = name
    r = requests.post(f"{API}/{source}/copy",
        headers={**headers(token), "Content-Type": "application/json"},
        json=body, timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def replace_html(token, file_id, text):
    r = requests.patch(f"{UPLOAD}/{file_id}", params={"uploadType": "media"},
        headers={**headers(token), "Content-Type": "text/html; charset=utf-8"},
        data=text.encode("utf-8"), timeout=30)
    r.raise_for_status()

def select_template(token, root, job):
    folders = [f for f in children(token, root) if f["mimeType"] == "application/vnd.google-apps.folder"]
    category = job.get("category", "").lower()
    keywords = ("uiux", "ui ux", "product designer", "design") if "design" in category or "ux" in category else ("python", "backend", "engineer", "full stack")
    folders.sort(key=lambda f: sum(word in f["name"].lower() for word in keywords), reverse=True)
    for folder in folders:
        entries = children(token, folder["id"])
        if any(f["name"] == "index.html" for f in entries):
            return folder, entries
    raise ValueError("No suitable HTML CV found")

def tailor_html(source_html, job):
    """Only modify Position Applied and Introduction text nodes, never invent experience."""
    soup = BeautifulSoup(source_html, "html.parser")
    candidate = []
    for node in soup.find_all(["h1", "h2", "h3", "h4", "dt", "label", "strong", "b"]):
        label = node.get_text(" ", strip=True).lower()
        if label in ("position applied", "position applied:", "introduction", "introduction:"):
            candidate.append((label, node))
    if not candidate:
        raise ValueError("No reliably identifiable editable CV sections; preserve original")
    existing_intro = ""
    intro_node = None
    position_node = None
    for label, node in candidate:
        sibling = node.find_next_sibling()
        if sibling is None:
            continue
        if "introduction" in label:
            intro_node = sibling
            existing_intro = sibling.get_text(" ", strip=True)
        if "position applied" in label:
            position_node = sibling
    if not intro_node or not position_node or not existing_intro:
        raise ValueError("Could not safely locate Introduction and Position Applied")
    client = OpenAI()
    prompt = {"job_title": job["position"], "job_description": job["jd_text"][:12000],
              "existing_introduction": existing_intro}
    response = client.responses.create(model=os.getenv("CV_MODEL", "gpt-4.1-mini"),
        instructions=("Rewrite the existing CV introduction for the job. Use ONLY skills and experience "
          "explicitly present in the original introduction. Do not invent experience, certifications, "
          "percentages, numerical outcomes, or credentials. Return JSON object with one key: introduction."),
        input=json.dumps(prompt, ensure_ascii=False))
    result = json.loads(response.output_text)
    new_intro = result["introduction"].strip()
    if not new_intro or len(new_intro) > 1500:
        raise ValueError("Unsafe or empty generated introduction")
    position_node.clear()
    position_node.append(job["position"])
    intro_node.clear()
    intro_node.append(new_intro)
    return str(soup)

def process(token, root, output_parent, job):
    """Make an isolated full CV folder copy; originals remain unchanged."""
    if not job.get("jd_text") or not job.get("verified"):
        raise ValueError("Agent 2 requires a verified JD with text")
    folder, files = select_template(token, root, job)
    original = next(f for f in files if f["name"] == "index.html")
    original_html = download_text(token, original["id"])
    revised = tailor_html(original_html, job)  # Fail before creating Drive artifacts
    safe_company = re.sub(r"[^A-Za-z0-9_-]+", "-", job.get("company", "Company"))[:50]
    new_folder = make_folder(token, output_parent, f"CV-{safe_company}-{job['position'][:45]}")
    copied_index = None
    for item in files:
        if item["mimeType"] == "application/vnd.google-apps.folder":
            continue
        new_id = copy_file(token, item["id"], new_folder, item["name"])
        if item["name"] == "index.html":
            copied_index = new_id
    if not copied_index:
        raise RuntimeError("Copied CV missing index.html")
    replace_html(token, copied_index, revised)
    return {"folder_id": new_folder, "index_file_id": copied_index,
            "source_template": folder["name"]}
