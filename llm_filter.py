"""
LLM-based job filter.
Sends job description to OpenAI and determines if it's backend-related.
"""

import json
import re
from typing import Any, Dict, List, Tuple

from openai import OpenAI

import config


SYSTEM_PROMPT = f"""You are a job classifier. Analyze the job description and determine if it is a BACKEND development role.

{config.BACKEND_KEYWORDS_PROMPT}

Respond with ONLY a valid JSON object, no other text:
{{
  "role_type": "backend" | "frontend" | "fullstack" | "other",
  "skills": ["skill1", "skill2", ...],
  "relevant": true | false
}}

Set "relevant" to true only if the job is backend-focused (backend engineer, API developer, server-side, etc.).
Set "relevant" to false for frontend-only, mobile-only, design, or non-technical roles."""


def analyze_job(description: str, title: str = "", api_key: str = None) -> Dict[str, Any]:
    """
    Send job description to LLM and get structured analysis.
    Returns dict with role_type, skills, relevant.
    api_key: optional override; if not provided, uses config.OPENAI_API_KEY
    """
    key = api_key or config.OPENAI_API_KEY
    if not key:
        raise ValueError("OPENAI_API_KEY not set. Paste your key in the UI or set in config/environment.")

    client = OpenAI(api_key=key)

    user_content = f"Job title: {title}\n\nDescription:\n{description[:4000]}"

    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
    )

    text = response.choices[0].message.content.strip()

    # Remove markdown code block if present
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    return json.loads(text)


def is_backend_job(analysis: Dict[str, Any]) -> bool:
    """Check if LLM analysis marks job as backend-relevant."""
    return analysis.get("relevant", False)


def filter_backend_jobs(analyses: List[Tuple[dict, dict]]) -> List[dict]:
    """
    Filter jobs where analysis.relevant is True.
    Returns list of final output format (title, company, skills, link).
    """
    results = []
    for job_data, analysis in analyses:
        if not is_backend_job(analysis):
            continue
        results.append(
            {
                "title": job_data.get("title", ""),
                "company": job_data.get("company", ""),
                "skills": analysis.get("skills", []),
                "link": job_data.get("link", ""),
            }
        )
    return results
