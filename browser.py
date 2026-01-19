from playwright.sync_api import sync_playwright
from pathlib import Path


class BrowserManager:
    """
    Manages a persistent Playwright browser session.
    This allows ApplyPilot Agent to reuse login state across runs.
    """

    def __init__(self, profile_dir: str = "browser_profile"):
        self.profile_path = Path(profile_dir)
        self.playwright = None
        self.browser_context = None
        self.page = None

    def launch(self):
        """
        Launch a persistent Chromium browser with a saved user profile.
        """
        self.playwright = sync_playwright().start()

        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=False,  # IMPORTANT: keep this false to avoid detection
            slow_mo=100,     # Slight delay to mimic human interaction
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ],
        )

        self.page = self.browser_context.pages[0]
        return self.page

    def close(self):
        """
        Gracefully close browser and Playwright instance.
        """
        if self.browser_context:
            self.browser_context.close()
        if self.playwright:
            self.playwright.stop()
