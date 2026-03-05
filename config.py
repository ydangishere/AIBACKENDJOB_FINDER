"""
Configuration for AI Backend Job Finder.
Set your API keys and preferences here.
"""

import os
from pathlib import Path

# OpenAI API - get key from https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Job source: "topcv" (không Cloudflare) | "itviec" (dùng FlareSolverr bypass Cloudflare)
JOB_SOURCE = "itviec"
JOB_SOURCE_URL = "https://itviec.com/it-jobs"  # Chỉ dùng khi JOB_SOURCE = "itviec"

# FlareSolverr - bypass Cloudflare cho ITviec. Chạy: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191/v1")

# Scraping
MAX_JOBS_TO_SCRAPE = 20  # Limit to avoid rate limiting
REQUEST_DELAY_SECONDS = 2  # Delay between requests

# LLM
LLM_MODEL = "gpt-4o-mini"  # Cheaper, fast. Use gpt-4o for better accuracy.
BACKEND_KEYWORDS_PROMPT = """
Backend roles include: backend engineer, server-side, API, database, microservices,
Java, Python, Node.js, Go, C#, .NET, Spring Boot, Django, FastAPI, REST, GraphQL,
SQL, NoSQL, Redis, message queues, DevOps, cloud (AWS, GCP, Azure).
Exclude: pure frontend (React/Vue only), mobile-only, design, marketing.
"""

# Output
RESULTS_FILE = Path(__file__).parent / "results.json"
NOTIFICATION_MODE = "email"  # "json" | "print" | "email"

# Email - gửi đến dangvany@gmail.com
# Chỉ cần: tạo App Password tại https://myaccount.google.com/apppasswords rồi dán vào dưới
EMAIL_TO = os.getenv("EMAIL_TO", "your-email@example.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "YOUR_APP_PASSWORD_HERE")  # Thay bang App Password Gmail
