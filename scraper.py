"""
Scraper for job listings.
- TopCV: requests + BeautifulSoup (no Cloudflare)
- ITviec: FlareSolverr (bypass Cloudflare) hoặc Playwright (fallback, có thể bị chặn)
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

import config


@dataclass
class JobListing:
    """Raw job data from scraping."""

    title: str
    company: str
    description: str
    link: str
    raw: Optional[Dict[str, Any]] = None


def _scrape_topcv(max_jobs: int, custom_url: Optional[str] = None) -> List[JobListing]:
    """
    Scrape TopCV - dùng requests + BeautifulSoup, không bị Cloudflare.
    custom_url: URL tùy chỉnh (listing hoặc job đơn). None = dùng URL mặc định.
    """
    jobs: List[JobListing] = []
    base = "https://www.topcv.vn"
    url = custom_url or "https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }

    seen_links = set()
    page = 1

    is_single_job = "/viec-lam/" in url and ".html" in url
    if is_single_job:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            title_el = soup.select_one("h1, .job-title, [class*='title']")
            title = title_el.get_text(strip=True)[:200] if title_el else ""
            company_el = soup.select_one("[class*='company'], .company-name")
            company = company_el.get_text(strip=True)[:100] if company_el else ""
            desc_el = soup.select_one(".job-detail, .description, [class*='content']")
            desc = desc_el.get_text(strip=True)[:3000] if desc_el else ""
            jobs.append(JobListing(title=title, company=company, description=desc, link=url.split("?")[0]))
        except Exception:
            pass
        return jobs

    while len(jobs) < max_jobs:
        try:
            fetch_url = f"{url}?page={page}" if "?page=" not in url else url.replace("page=1", f"page={page}")
            resp = requests.get(
                fetch_url,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Job cards - TopCV dùng nhiều class, thử nhiều selector
            cards = (
                soup.select(".job-item")
                or soup.select(".job-list .item")
                or soup.select('div[class*="job-item"]')
                or soup.select('article[class*="job"]')
            )

            if not cards:
                # Fallback: lấy link job từ mọi a[href*="/viec-lam/"]
                links = soup.select('a[href*="/viec-lam/"]')
                for a in links:
                    href = a.get("href", "")
                    if "tim-viec" in href or href in seen_links:
                        continue
                    full_url = href if href.startswith("http") else base + href
                    if full_url in seen_links:
                        continue
                    seen_links.add(full_url)

                    # Lấy title từ text hoặc parent
                    title = a.get_text(strip=True) or ""
                    if len(title) < 5:
                        parent = a.find_parent(["div", "li", "article"])
                        if parent:
                            h3 = parent.select_one("h3, .title, [class*='title']")
                            title = h3.get_text(strip=True) if h3 else ""
                    company = ""
                    parent = a.find_parent(["div", "li", "article"])
                    if parent:
                        comp_el = parent.select_one("[class*='company'], .company-name")
                        company = comp_el.get_text(strip=True) if comp_el else ""

                    if title and full_url:
                        jobs.append(
                            JobListing(
                                title=title[:200],
                                company=company[:100],
                                description="",
                                link=full_url.split("?")[0],
                            )
                        )
                        if len(jobs) >= max_jobs:
                            break
            else:
                for card in cards:
                    if len(jobs) >= max_jobs:
                        break
                    a = card.select_one('a[href*="/viec-lam/"]')
                    if not a:
                        continue
                    href = a.get("href", "")
                    if "tim-viec" in href:
                        continue
                    full_url = (href if href.startswith("http") else base + href).split("?")[0]
                    if full_url in seen_links:
                        continue
                    seen_links.add(full_url)

                    title = a.get_text(strip=True) or ""
                    if len(title) < 5:
                        h3 = card.select_one("h3, .title, [class*='title']")
                        title = h3.get_text(strip=True) if h3 else ""
                    comp_el = card.select_one("[class*='company'], .company-name")
                    company = comp_el.get_text(strip=True) if comp_el else ""
                    desc_el = card.select_one("p, .description, [class*='desc']")
                    desc = desc_el.get_text(strip=True)[:3000] if desc_el else ""

                    if title:
                        jobs.append(
                            JobListing(
                                title=title[:200],
                                company=company[:100],
                                description=desc,
                                link=full_url,
                            )
                        )

            if len(jobs) >= max_jobs:
                break
            page += 1
            time.sleep(config.REQUEST_DELAY_SECONDS)

        except Exception as e:
            break

    return jobs[:max_jobs]


def _scrape_itviec_flaresolverr(max_jobs: int, custom_url: Optional[str] = None) -> List[JobListing]:
    """
    Scrape ITviec qua FlareSolverr - bypass Cloudflare.
    Cần chạy: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
    """
    jobs: List[JobListing] = []
    url = custom_url or config.JOB_SOURCE_URL
    fs_url = config.FLARESOLVERR_URL

    try:
        resp = requests.post(
            fs_url,
            json={
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000,
            },
            headers={"Content-Type": "application/json"},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            return jobs

        solution = data.get("solution", {})
        html = solution.get("response", "")

        if not html:
            return jobs

        # Thử parse __NEXT_DATA__ (Next.js)
        soup = BeautifulSoup(html, "html.parser")
        script = soup.select_one("script#__NEXT_DATA__")
        if script and script.string:
            try:
                nd = json.loads(script.string)
                jobs = _parse_itviec_next_data(nd, max_jobs)
            except json.JSONDecodeError:
                pass

        # Fallback: parse DOM
        if not jobs:
            base = "https://itviec.com"
            seen = set()
            for a in soup.select('a[href*="/it-jobs/"]'):
                href = a.get("href", "")
                if not href or "it-jobs" not in href:
                    continue
                link = (href if href.startswith("http") else base + href).split("?")[0]
                if link in seen:
                    continue
                seen.add(link)
                title_el = a.select_one("h2, h3, .title, [class*='title']") or a
                title = title_el.get_text(strip=True) if title_el else ""
                parent = a.find_parent(["div", "li", "article"])
                company = ""
                if parent:
                    comp_el = parent.select_one("[class*='company'], .company-name")
                    company = comp_el.get_text(strip=True) if comp_el else ""
                if title and link:
                    jobs.append(
                        JobListing(
                            title=title[:200],
                            company=company[:100],
                            description="",
                            link=link.split("?")[0],
                        )
                    )
                    if len(jobs) >= max_jobs:
                        break

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "FlareSolverr không chạy. Chạy: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest"
        )
    except Exception as e:
        raise RuntimeError(f"FlareSolverr lỗi: {e}")

    return jobs[:max_jobs]


async def _scrape_itviec_playwright(max_jobs: int, custom_url: Optional[str] = None) -> List[JobListing]:
    """
    Scrape ITviec - Playwright (fallback khi không có FlareSolverr).
    Lưu ý: ITviec dùng Cloudflare, thường bị chặn. Ưu tiên dùng FlareSolverr.
    """
    jobs: List[JobListing] = []
    url = custom_url or config.JOB_SOURCE_URL

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)

            script_content = await page.evaluate(
                "() => { const s = document.querySelector('script#__NEXT_DATA__'); return s ? s.textContent : null; }"
            )

            if script_content:
                try:
                    data = json.loads(script_content)
                    jobs = _parse_itviec_next_data(data, max_jobs)
                except json.JSONDecodeError:
                    pass

            if not jobs:
                jobs = await _scrape_itviec_dom(page, max_jobs)

        finally:
            await browser.close()

    return jobs[:max_jobs]


async def _scrape_itviec(max_jobs: int, custom_url: Optional[str] = None) -> List[JobListing]:
    """ITviec: thử FlareSolverr trước, fallback Playwright nếu FlareSolverr lỗi."""
    try:
        return _scrape_itviec_flaresolverr(max_jobs, custom_url)
    except RuntimeError:
        return await _scrape_itviec_playwright(max_jobs, custom_url)


def _parse_itviec_next_data(data: dict, max_jobs: int) -> List[JobListing]:
    """Parse Next.js data from ITviec."""
    jobs: List[JobListing] = []
    try:
        props = data.get("props", {}).get("pageProps", {})
        job_list = props.get("jobs", []) or props.get("jobsData", {}).get("jobs", [])

        for item in job_list[:max_jobs]:
            title = item.get("title", "") or item.get("name", "")
            company = (
                item.get("company", {}).get("name", "")
                if isinstance(item.get("company"), dict)
                else str(item.get("company", ""))
            )
            desc = item.get("description", "") or item.get("job_description", "") or ""
            slug = item.get("slug", "") or item.get("id", "")
            link = f"https://itviec.com/it-jobs/{slug}" if slug else item.get("url", "")

            jobs.append(
                JobListing(
                    title=title,
                    company=company,
                    description=desc[:3000] if desc else "",
                    link=link,
                    raw=item,
                )
            )
    except Exception:
        pass
    return jobs


async def _scrape_itviec_dom(page, max_jobs: int) -> List[JobListing]:
    """Fallback: scrape job cards from DOM."""
    jobs: List[JobListing] = []
    base = "https://itviec.com"
    selectors = [
        'a[href*="/it-jobs/"]',
        '[data-testid="job-card"]',
        ".job-card",
        ".job-item",
        "article",
    ]

    for sel in selectors:
        elements = await page.query_selector_all(sel)
        if not elements:
            continue
        for el in elements[:max_jobs]:
            try:
                link_el = await el.query_selector("a[href*='it-jobs']") or el
                href = await link_el.get_attribute("href")
                if not href:
                    continue
                link = href if href.startswith("http") else f"{base}{href}"

                title_el = await el.query_selector("h2, h3, .title, [class*='title']")
                title = await title_el.inner_text() if title_el else ""

                company_el = await el.query_selector("[class*='company'], .company-name")
                company = await company_el.inner_text() if company_el else ""

                desc_el = await el.query_selector("p, .description, [class*='desc']")
                description = await desc_el.inner_text() if desc_el else ""

                if title and link:
                    jobs.append(
                        JobListing(
                            title=title.strip(),
                            company=company.strip() if company else "",
                            description=description.strip()[:3000] if description else "",
                            link=link,
                        )
                    )
            except Exception:
                continue
        if jobs:
            break
    return jobs


async def scrape_jobs(max_jobs=None, url: Optional[str] = None) -> List[JobListing]:
    """
    Main entry. url: custom URL (itviec hoặc topcv). None = dùng config.
    """
    max_jobs = max_jobs or config.MAX_JOBS_TO_SCRAPE

    if url:
        url_clean = url.strip()
        if "itviec.com" in url_clean:
            return await _scrape_itviec(max_jobs, url_clean)
        if "topcv.vn" in url_clean:
            return _scrape_topcv(max_jobs, url_clean)
        return []

    if config.JOB_SOURCE == "topcv":
        return _scrape_topcv(max_jobs)

    if config.JOB_SOURCE == "itviec":
        return await _scrape_itviec(max_jobs)

    return _scrape_topcv(max_jobs)


if __name__ == "__main__":
    result = asyncio.run(scrape_jobs(max_jobs=5))
    for j in result:
        print(f"{j.title} @ {j.company} | {j.link}")
