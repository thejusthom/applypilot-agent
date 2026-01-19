from browser import BrowserManager
import time


def main():
    browser = BrowserManager()
    page = browser.launch()

    print("[ApplyPilot Agent] Browser launched.")

    # Navigate to LinkedIn
    page.goto("https://www.linkedin.com/", timeout=60000)

    print("[ApplyPilot Agent] If not logged in, please log in manually.")
    print("[ApplyPilot Agent] Waiting 60 seconds before closing...")

    # Give user time to log in on first run
    time.sleep(60)

    browser.close()
    print("[ApplyPilot Agent] Browser session closed.")


if __name__ == "__main__":
    main()
