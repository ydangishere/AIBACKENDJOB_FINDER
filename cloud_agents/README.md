# Cloud Job Agents

GitHub Actions scheduled Monday 04:00 Asia/Ho_Chi_Minh (21:00 UTC Sunday); manual workflow_dispatch available.

**Current scope:** Agent 1 public search discovery and conservative verification, JSON manifest and Drive upload; Drive CV-folder read-only check. Agent 2 intentionally does NOT alter CVs until a verifiable JD and authenticated Drive access exist. Agent 3 publishes status as GitHub Actions artifact. No job applications submitted.

**Required GitHub Actions secrets:** GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_REFRESH_TOKEN (OAuth scope drive.file or suitable Drive access; consent must authorize both existing CV folder and destination). OPENAI_API_KEY reserved for future LLM tailoring. Configure in Settings > Secrets and variables > Actions.

**Facebook private groups:** Not connected. Facebook browser login requires an independently authenticated persistent browser; do not place Facebook credentials or cookies in GitHub secrets. Public web search cannot see private group posts.

**Limitations:** Search engine RSS leads do not prove posting date or open application status. Unverified leads are excluded. This deliberately does not invent valid jobs or claim CVs were tailored. GitHub Actions schedule can run late; trigger manually to test.
