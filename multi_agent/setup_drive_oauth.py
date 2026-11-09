"""One-time LOCAL OAuth setup. Never commit or print generated credentials."""
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPE = ["https://www.googleapis.com/auth/drive"]
HERE = Path(__file__).resolve().parent
CLIENT_JSON = HERE / "google_oauth_client.json"
SECRET_FILE = HERE / ".env.drive.secrets"


def main():
    if not CLIENT_JSON.is_file():
        raise SystemExit(
            "Place your Google Cloud OAuth Desktop client JSON at "
            + str(CLIENT_JSON) + " (never commit this file)."
        )
    if SECRET_FILE.exists():
        raise SystemExit("Existing local token file found. Move it safely before regenerating.")
    config = json.loads(CLIENT_JSON.read_text(encoding="utf-8"))
    client = config.get("installed") or config.get("web")
    if not client:
        raise SystemExit("OAuth JSON must contain an installed or web client.")
    flow = InstalledAppFlow.from_client_config(config, scopes=SCOPE)
    credentials = flow.run_local_server(
        host="localhost", port=0, open_browser=True, access_type="offline", prompt="consent"
    )
    if not credentials.refresh_token:
        raise SystemExit(
            "No OAuth refresh token was issued. Revoke this test grant in Google Account "
            "third-party access and retry with prompt=consent."
        )
    values = {
        "GOOGLE_DRIVE_CLIENT_ID": client["client_id"],
        "GOOGLE_DRIVE_CLIENT_SECRET": client["client_secret"],
        "GOOGLE_DRIVE_REFRESH_TOKEN": credentials.refresh_token,
    }
    data = "".join(f"{name}={value}\n" for name, value in values.items())
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(SECRET_FILE, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as target:
        target.write(data)
    print("OAuth succeeded; secrets saved ONLY in local ignored file:", SECRET_FILE)
    print("Add the three GOOGLE_DRIVE_* values to GitHub repo Settings -> Secrets and variables -> Actions -> Secrets.")
    print("Never paste these secrets into ChatGPT, Issues, commits, or PRs.")


if __name__ == "__main__":
    main()
