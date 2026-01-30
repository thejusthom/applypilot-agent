"""
Debug script - will actually TRY to click things
"""
from browser import BrowserManager
import time

browser = BrowserManager()
page = browser.launch()

print("="*60)
print("LinkedIn Click Tester")
print("="*60)

# TEST 1: Resume selection
print("\n>>> TEST 1: RESUME SELECTION")
print("Go to the RESUME step and press Enter...")
input()

# Try to expand
expand_btn = page.locator("button:has-text('more resumes')")
print(f"Expand button found: {expand_btn.count()}")
if expand_btn.count() > 0:
    print("Clicking expand...")
    expand_btn.first.click()
    time.sleep(2)
    print("Expanded!")

# Now find radios
radios = page.locator("input[type='radio']:visible")
print(f"\nVisible radios after expand: {radios.count()}")

# Get the page HTML around radios to understand structure
for i in range(radios.count()):
    radio = radios.nth(i)
    radio_id = radio.get_attribute("id")
    checked = radio.is_checked()
    
    # Get outer HTML of parent
    try:
        outer = radio.evaluate("el => el.parentElement.parentElement.parentElement.innerText.substring(0, 100)")
        print(f"\n  Radio [{i}]: id={radio_id}, checked={checked}")
        print(f"    Context: {outer.replace(chr(10), ' ')}")
    except Exception as e:
        print(f"  Radio [{i}]: id={radio_id}, checked={checked}, context error: {e}")

# Ask which one to click
print("\nWhich radio index to click? (or 'skip'): ", end="")
choice = input().strip()
if choice != 'skip' and choice.isdigit():
    idx = int(choice)
    radios.nth(idx).click()
    print(f"Clicked radio {idx}!")
    time.sleep(1)

# TEST 2: Follow checkbox
print("\n>>> TEST 2: FOLLOW CHECKBOX")
print("Go to the REVIEW step (with Follow checkbox) and press Enter...")
input()

# Try direct ID
follow_cb = page.locator("#follow-company-checkbox")
print(f"#follow-company-checkbox found: {follow_cb.count()}")
if follow_cb.count() > 0:
    visible = follow_cb.first.is_visible()
    checked = follow_cb.first.is_checked()
    print(f"  visible={visible}, checked={checked}")
    
    if checked:
        print("Attempting to uncheck...")
        follow_cb.first.click()
        time.sleep(1)
        print(f"  Now checked: {follow_cb.first.is_checked()}")
else:
    # Try other methods
    print("\nTrying alternative selectors...")
    alts = [
        "input[name='follow-company-checkbox']",
        "input[id*='follow']",
        "input[type='checkbox']:visible",
    ]
    for sel in alts:
        els = page.locator(sel)
        print(f"  {sel}: {els.count()} found")

print("\n--- Done! Press Enter to close ---")
input()
browser.close()