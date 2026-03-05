"""
Notification module.
Supports: JSON file, print to terminal, or email.
"""

import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

import config


def save_to_json(results: List[dict], path: Optional[Path] = None) -> None:
    """Save filtered jobs to JSON file."""
    path = path or config.RESULTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} jobs to {path}")


def print_to_terminal(results: List[dict]) -> None:
    """Print results to terminal."""
    if not results:
        print("No backend jobs found.")
        return
    print(f"\n--- Found {len(results)} backend job(s) ---\n")
    for i, job in enumerate(results, 1):
        print(f"{i}. {job.get('title', '')} @ {job.get('company', '')}")
        print(f"   Skills: {', '.join(job.get('skills', []))}")
        print(f"   Link: {job.get('link', '')}\n")


def send_email(results: List[dict]) -> None:
    """Send results via Gmail."""
    pwd = config.EMAIL_APP_PASSWORD
    to_addr = config.EMAIL_TO
    if not pwd:
        print("Chua cau hinh email. Them EMAIL_APP_PASSWORD vao config hoac: $env:EMAIL_APP_PASSWORD='xxx'")
        save_to_json(results)
        return

    body = _format_email_body(results)
    msg = MIMEMultipart()
    msg["From"] = to_addr
    msg["To"] = to_addr
    msg["Subject"] = f"AI Job Finder: {len(results)} backend job(s)"

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(to_addr, pwd)
            server.sendmail(to_addr, to_addr, msg.as_string())
        print(f"Da gui email den {to_addr}")
    except Exception as e:
        print(f"Gui email loi: {e}")


def _format_email_body(results: List[dict]) -> str:
    """Format job list as plain text for email."""
    if not results:
        return "No backend jobs found."
    lines = [f"Found {len(results)} backend job(s):\n"]
    for i, job in enumerate(results, 1):
        lines.append(f"{i}. {job.get('title', '')} @ {job.get('company', '')}")
        lines.append(f"   Skills: {', '.join(job.get('skills', []))}")
        lines.append(f"   Link: {job.get('link', '')}\n")
    return "\n".join(lines)


def notify(results: List[dict], mode: Optional[str] = None) -> None:
    """
    Send notification based on config.NOTIFICATION_MODE.
    Options: "json", "print", "email"
    """
    mode = mode or config.NOTIFICATION_MODE
    if mode == "json":
        save_to_json(results)
    elif mode == "print":
        print_to_terminal(results)
    elif mode == "email":
        send_email(results)
    else:
        save_to_json(results)
        print_to_terminal(results)
