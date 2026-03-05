"""
AI Backend Job Finder - Main entry.
Pipeline: website -> scraper -> job description -> LLM analysis -> filter -> notification
"""

import asyncio
from typing import List, Tuple

import config
from llm_filter import analyze_job, filter_backend_jobs
from notifier import notify
from scraper import JobListing, scrape_jobs


def run_llm_analysis(jobs: List[JobListing]) -> List[Tuple[dict, dict]]:
    """Run LLM analysis on each job, return (job_dict, analysis) pairs."""
    analyses = []
    for job in jobs:
        try:
            analysis = analyze_job(job.description, job.title)
            job_dict = {
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "link": job.link,
            }
            analyses.append((job_dict, analysis))
        except Exception as e:
            print(f"LLM error for '{job.title}': {e}")
    return analyses


async def main() -> None:
    print("1. Scraping job listings...")
    jobs = await scrape_jobs()

    if not jobs:
        print("No jobs scraped. Check URL or selectors in scraper.py.")
        notify([])
        return

    print(f"   Scraped {len(jobs)} job(s)")

    print("2. Analyzing with LLM...")
    analyses = run_llm_analysis(jobs)

    print("3. Filtering backend jobs...")
    results = filter_backend_jobs(analyses)

    print(f"   Found {len(results)} backend job(s)")

    print("4. Saving / notifying...")
    notify(results)


if __name__ == "__main__":
    asyncio.run(main())
