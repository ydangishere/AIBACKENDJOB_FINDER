"""
UI đơn giản (tkinter): dán link + API key -> Run -> Xem kết quả.
Chạy run_ui.bat (Windows) hoặc run_ui.sh (Mac).
"""

import asyncio
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from llm_filter import analyze_job, filter_backend_jobs
from scraper import scrape_jobs


def run_pipeline(url: str, api_key: str, result_text, status_label):
    """Chạy pipeline trong thread riêng."""
    try:
        status_label.config(text="Scraping...")
        result_text.delete(1.0, tk.END)
        result_text.update()

        jobs = asyncio.run(scrape_jobs(max_jobs=20, url=url))
        if not jobs:
            status_label.config(text="No jobs scraped. Check link or FlareSolverr (ITviec).")
            return

        status_label.config(text="Analyzing with LLM...")
        result_text.update()

        analyses = []
        for job in jobs:
            try:
                analysis = analyze_job(job.description, job.title, api_key=api_key)
                job_dict = {
                    "title": job.title,
                    "company": job.company,
                    "description": job.description,
                    "link": job.link,
                }
                analyses.append((job_dict, analysis))
            except Exception as e:
                pass

        results = filter_backend_jobs(analyses)
        status_label.config(text=f"Found {len(results)} backend job(s)")

        out = []
        for i, job in enumerate(results, 1):
            title = job.get("title", "") or "N/A"
            company = job.get("company", "") or ""
            req = ", ".join(job.get("skills", [])) if job.get("skills") else "N/A"
            link = job.get("link", "")
            out.append(f"{'─'*50}\n{i}. {title}\n   Company: {company}\n   Requirements: {req}\n   Link: {link}\n")
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "\n".join(out) if out else "No backend jobs found.")

    except Exception as e:
        status_label.config(text="Error")
        messagebox.showerror("Error", str(e))


def on_run():
    api_key = key_entry.get().strip()
    url = url_entry.get("1.0", tk.END).strip()
    import config
    key = api_key or config.OPENAI_API_KEY
    if not key:
        messagebox.showwarning("Missing key", "Enter OpenAI API key or configure in config.")
        return
    if not url:
        messagebox.showwarning("Missing link", "Paste ITviec or TopCV link.")
        return
    threading.Thread(target=run_pipeline, args=(url, key, result_text, status_label), daemon=True).start()


root = tk.Tk()
root.title("AI Backend Job Finder")
root.geometry("600x550")
root.minsize(500, 450)

main = ttk.Frame(root, padding=10)
main.pack(fill=tk.BOTH, expand=True)

ttk.Label(main, text="OpenAI API key:").pack(anchor=tk.W)
key_entry = ttk.Entry(main, width=70, show="*")
key_entry.pack(fill=tk.X, pady=(0, 5))
ttk.Label(main, text="Get key at: https://platform.openai.com/api-keys", font=("", 8), foreground="gray").pack(anchor=tk.W)

ttk.Label(main, text="ITviec or TopCV link:").pack(anchor=tk.W, pady=(10, 0))
url_entry = scrolledtext.ScrolledText(main, height=3, width=70, wrap=tk.WORD)
url_entry.pack(fill=tk.X, pady=(0, 5))
url_entry.insert(tk.END, "https://itviec.com/it-jobs")

ttk.Button(main, text="Run Scraper & Analysis", command=on_run).pack(pady=10)

status_label = ttk.Label(main, text="")
status_label.pack(anchor=tk.W)

ttk.Label(main, text="Results:").pack(anchor=tk.W, pady=(10, 0))
result_text = scrolledtext.ScrolledText(main, height=15, wrap=tk.WORD)
result_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

root.mainloop()
