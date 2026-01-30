"""
Debug script - Resume Selection Tester
"""
from browser import BrowserManager
import time

browser = BrowserManager()
page = browser.launch()

print("="*60)
print("Resume Selection Tester")
print("="*60)

print("\nGo to the RESUME step of an Easy Apply and press Enter...")
input()

# Step 1: Expand
print("\n[Step 1] Expanding resume list...")
expand_btn = page.locator("button:has-text('more resumes')")
if expand_btn.count() > 0 and expand_btn.first.is_visible():
    expand_btn.first.click()
    print("  Clicked expand button")
    time.sleep(2)
else:
    print("  No expand button found (already expanded?)")

# Step 2: Find all resume cards and their actual names
print("\n[Step 2] Finding all resumes...")
radios = page.locator("input[type='radio'][id^='jobsDocumentCardToggle']:visible")
print(f"  Found {radios.count()} resume radio buttons\n")

resume_map = {}
for i in range(radios.count()):
    radio = radios.nth(i)
    radio_id = radio.get_attribute("id")
    checked = radio.is_checked()
    
    # Find the download button to get real filename
    try:
        # Go up to card container
        card = radio.locator("xpath=ancestor::div[contains(@class, 'jobs-document-upload')]").first
        if card:
            download_btn = card.locator("button[aria-label*='Download']")
            if download_btn.count() > 0:
                aria = download_btn.first.get_attribute("aria-label")
                # Extract filename from "Download resume Filename.pdf"
                filename = aria.replace("Download resume ", "").strip() if aria else "Unknown"
            else:
                filename = "Unknown (no download btn)"
        else:
            filename = "Unknown (no card)"
    except Exception as e:
        filename = f"Error: {e}"
    
    status = "✓ SELECTED" if checked else ""
    print(f"  [{i}] {filename} {status}")
    resume_map[i] = filename

# Step 3: Let user select one
print("\n[Step 3] Which resume to select? Enter number (or 'skip'): ", end="")
choice = input().strip()

if choice != 'skip' and choice.isdigit():
    idx = int(choice)
    if idx < radios.count():
        radio = radios.nth(idx)
        print(f"\n  Attempting to select: {resume_map.get(idx, 'Unknown')}")
        
        # Use JavaScript click
        try:
            radio.evaluate("el => el.click()")
            time.sleep(1)
            
            # Verify
            if radio.is_checked():
                print("  ✓ SUCCESS! Resume selected.")
            else:
                print("  ✗ FAILED - radio not checked after click")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

print("\n--- Done! Press Enter to close ---")
input()
browser.close()