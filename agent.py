from browser import BrowserManager
from playwright.sync_api import TimeoutError
import time


LINKEDIN_JOB_SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords=software%20new%20grad"
    "&geoId=103644278"
    "&distance=25"
    "&f_TPR=r8640"
)


def main():
    browser = BrowserManager()
    page = browser.launch()

    print("[ApplyPilot Agent] Browser launched.")

    page.goto(LINKEDIN_JOB_SEARCH_URL, timeout=60000)
    print("[ApplyPilot Agent] Job search loaded.")

    try:
        # Wait for at least one job card to appear
        page.wait_for_selector(
            "div.job-card-container, li.jobs-search-results__list-item",
            timeout=60000
        )

        print("[ApplyPilot Agent] Job cards detected.")

        # Scroll to load more jobs
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            time.sleep(2)

        # Capture job cards (handle multiple layouts)
        job_cards = page.locator(
            "div.job-card-container, li.jobs-search-results__list-item"
        )
        total_jobs = job_cards.count()

        print(f"[ApplyPilot Agent] Found {total_jobs} job cards.")

        if total_jobs == 0:
            print("[ApplyPilot Agent] No jobs detected after load. Exiting.")
            browser.close()
            return

        for idx in range(min(total_jobs, 10)):
            job = job_cards.nth(idx)
            job.scroll_into_view_if_needed()
            job.click()
            time.sleep(3)

            print(f"\n[ApplyPilot Agent] Checking job #{idx + 1}")

            easy_apply_button = page.locator("button.jobs-apply-button")

            if easy_apply_button.count() > 0:
                print("[ApplyPilot Agent] Easy Apply detected. Opening modal.")
                easy_apply_button.first.click()
                time.sleep(5)

                dismiss = page.locator("button[aria-label='Dismiss']")
                if dismiss.count() > 0:
                    dismiss.first.click()
                    time.sleep(2)
            else:
                print("[ApplyPilot Agent] Easy Apply not available.")

    except TimeoutError:
        print("[ApplyPilot Agent] Timed out waiting for job cards.") 
        print("[ApplyPilot Agent] LinkedIn layout may have changed.")

    browser.close()
    print("\n[ApplyPilot Agent] Phase 2 complete. Browser closed.")


if __name__ == "__main__":
    main()