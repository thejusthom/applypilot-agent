import time
import random
import argparse
import json
from pathlib import Path
from datetime import datetime
from browser import BrowserManager
from form_filler import FormFiller
from config import (
    build_search_url, MAX_APPLICATIONS_PER_RUN, MAX_JOBS_TO_PROCESS,
    ENABLE_PAGINATION, MAX_PAGES, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS,
    APPLICATION_LOG_PATH
)
from playwright.sync_api import TimeoutError


def random_sleep(min_sec=None, max_sec=None):
    min_sec = min_sec or MIN_DELAY_SECONDS
    max_sec = max_sec or MAX_DELAY_SECONDS
    time.sleep(random.uniform(min_sec, max_sec))


def log_application(job_title, company, status, resume_type):
    """Log application to JSON file for tracking."""
    log_path = Path(APPLICATION_LOG_PATH)
    
    if log_path.exists():
        with open(log_path, "r") as f:
            log = json.load(f)
    else:
        log = []
    
    log.append({
        "timestamp": datetime.now().isoformat(),
        "job_title": job_title,
        "company": company,
        "status": status,
        "resume_type": resume_type
    })
    
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)


def check_already_applied(page):
    """Check if we've already applied to this job."""
    # LinkedIn shows "Applied" badge or disabled button
    applied_badge = page.locator("span.artdeco-inline-feedback__message:has-text('Applied')")
    applied_badge2 = page.locator("li-icon[type='success-pebble-icon']")
    applied_text = page.locator(".jobs-s-apply__application-link")
    
    if applied_badge.count() > 0 or applied_badge2.count() > 0 or applied_text.count() > 0:
        return True
    
    # Check button text
    apply_btn = page.locator("button.jobs-apply-button")
    if apply_btn.count() > 0:
        btn_text = apply_btn.first.inner_text().strip().lower()
        if "applied" in btn_text:
            return True
    
    return False


def uncheck_follow_company(page):
    """Uncheck the 'Follow company' checkbox if present."""
    try:
        # Direct ID selector - LinkedIn uses 'follow-company-checkbox'
        checkbox = page.locator("#follow-company-checkbox")
        if checkbox.count() > 0 and checkbox.first.is_visible():
            if checkbox.first.is_checked():
                # Use JavaScript click to bypass any overlay issues
                checkbox.first.evaluate("el => el.click()")
                print("   [Form] Unchecked 'Follow company'")
                return True
            else:
                print("   [Form] 'Follow company' already unchecked")
                return True
    except Exception as e:
        print(f"   [Form] Follow checkbox error: {e}")
    
    return False


def select_resume_in_dropdown(page, resume_dropdown_name):
    """
    Select the correct resume from LinkedIn's resume list.
    """
    try:
        print(f"   [Resume] Looking for: {resume_dropdown_name}")
        
        # FIRST: Expand the resume list if collapsed
        expand_btn = page.locator("button:has-text('more resumes')")
        if expand_btn.count() > 0 and expand_btn.first.is_visible():
            expand_btn.first.click()
            print("   [Resume] Expanded resume list")
            random_sleep(1, 2)
        
        # Find all visible radio buttons
        radios = page.locator("input[type='radio'][id^='jobsDocumentCardToggle']:visible")
        print(f"   [Resume] Found {radios.count()} resume radio buttons")
        
        # For each radio, check the download button's aria-label (it has the real filename)
        for i in range(radios.count()):
            radio = radios.nth(i)
            radio_id = radio.get_attribute("id")
            
            try:
                # The download button near this radio has aria-label with the actual filename
                # e.g., "Download resume Thejus_Thomson_Resume.pdf"
                # Get the parent card container
                card = radio.locator("xpath=ancestor::div[contains(@class, 'jobs-document')]").first
                if card:
                    # Find the download button which has the real filename
                    download_btn = card.locator("button[aria-label*='Download resume']")
                    if download_btn.count() > 0:
                        aria_label = download_btn.first.get_attribute("aria-label") or ""
                        # aria_label is like "Download resume Thejus_Thomson_Resume.pdf"
                        if resume_dropdown_name.lower() in aria_label.lower():
                            if not radio.is_checked():
                                # Use JavaScript click to bypass the overlay
                                radio.evaluate("el => el.click()")
                                print(f"   [Resume] Selected: {resume_dropdown_name}")
                                return True
                            else:
                                print(f"   [Resume] Already selected: {resume_dropdown_name}")
                                return True
            except Exception as e:
                continue
        
        # Fallback: Try clicking by finding the card with our resume name
        cards = page.locator("div[class*='jobs-document-upload']")
        for i in range(cards.count()):
            card = cards.nth(i)
            if not card.is_visible():
                continue
            
            card_text = card.inner_text()
            if resume_dropdown_name.lower() in card_text.lower():
                radio = card.locator("input[type='radio']")
                if radio.count() > 0 and not radio.first.is_checked():
                    radio.first.evaluate("el => el.click()")
                    print(f"   [Resume] Selected via card: {resume_dropdown_name}")
                    return True

        print(f"   [Resume] Could not find: {resume_dropdown_name}")
        return False
        
    except Exception as e:
        print(f"   [Resume] Error: {e}")
        return False


def detect_and_fill_fields(page, form_filler, job_title="", company="", resume_dropdown_name=""):
    """Detect form fields and attempt to fill them."""
    all_filled = True
    unknown_count = 0
    
    # Fields to ignore (not actual application fields)
    IGNORED_FIELDS = [
        "search by title",
        "search by skill", 
        "search by company",
        "search",
        "city, state, or zip code",
        "location"
    ]

    # FIRST: Handle resume selection if we see resume-related elements
    resume_section = page.locator("div[class*='resume'], div[class*='document'], h3:has-text('Resume')")
    if resume_section.count() > 0 and resume_dropdown_name:
        select_resume_in_dropdown(page, resume_dropdown_name)

    # SECOND: Uncheck "Follow company" if present
    uncheck_follow_company(page)

    # Text inputs
    text_inputs = page.locator("input[type='text'], input:not([type])")
    for i in range(text_inputs.count()):
        try:
            field = text_inputs.nth(i)
            if not field.is_visible():
                continue

            field_id = field.get_attribute("id") or ""
            label = page.locator(f"label[for='{field_id}']")
            
            if label.count() > 0:
                question = label.first.inner_text().strip()
            else:
                question = field.get_attribute("placeholder") or field.get_attribute("aria-label") or "Unknown field"

            # Skip ignored fields
            if any(ignored in question.lower() for ignored in IGNORED_FIELDS):
                continue

            current_value = field.input_value()
            if current_value:
                continue

            answer, source = form_filler.get_answer(question, "text")

            if answer:
                field.fill(answer)
                print(f"   [Fill] '{question[:30]}...' -> '{answer[:20]}...' ({source})")
            else:
                form_filler.log_unknown_field(question, "text", job_title, company)
                all_filled = False
                unknown_count += 1
        except:
            continue

    # Select dropdowns
    selects = page.locator("select:visible")
    for i in range(selects.count()):
        try:
            field = selects.nth(i)
            if not field.is_visible():
                continue

            field_id = field.get_attribute("id") or ""
            label = page.locator(f"label[for='{field_id}']")
            
            if label.count() > 0:
                question = label.first.inner_text().strip()
            else:
                question = field.get_attribute("aria-label") or "Unknown dropdown"

            # Skip ignored fields
            if any(ignored in question.lower() for ignored in IGNORED_FIELDS):
                continue

            current = field.input_value()
            if current and current != "Select an option" and current != "":
                continue

            answer, source = form_filler.get_answer(question, "select")

            if answer:
                try:
                    field.select_option(label=answer)
                    print(f"   [Fill] '{question[:30]}...' -> '{answer}' ({source})")
                except:
                    try:
                        field.select_option(value=answer)
                    except:
                        # Capture all options for learning
                        options = []
                        try:
                            option_els = field.locator("option")
                            for j in range(option_els.count()):
                                opt_text = option_els.nth(j).inner_text().strip()
                                if opt_text and opt_text != "Select an option":
                                    options.append(opt_text)
                        except:
                            pass
                        form_filler.log_unknown_field(question, "select", job_title, company, options)
                        all_filled = False
                        unknown_count += 1
            else:
                # Capture all options for learning
                options = []
                try:
                    option_els = field.locator("option")
                    for j in range(option_els.count()):
                        opt_text = option_els.nth(j).inner_text().strip()
                        if opt_text and opt_text != "Select an option":
                            options.append(opt_text)
                except:
                    pass
                form_filler.log_unknown_field(question, "select", job_title, company, options)
                all_filled = False
                unknown_count += 1
        except:
            continue

    # Radio buttons
    fieldsets = page.locator("fieldset")
    for i in range(fieldsets.count()):
        try:
            fieldset = fieldsets.nth(i)
            if not fieldset.is_visible():
                continue

            legend = fieldset.locator("legend")
            if legend.count() == 0:
                continue

            question = legend.first.inner_text().strip()
            
            checked = fieldset.locator("input[type='radio']:checked")
            if checked.count() > 0:
                continue

            answer, source = form_filler.get_answer(question, "radio")

            if answer:
                radio_labels = fieldset.locator("label")
                for j in range(radio_labels.count()):
                    label_text = radio_labels.nth(j).inner_text().strip().lower()
                    if answer.lower() in label_text or label_text in answer.lower():
                        radio_labels.nth(j).click()
                        print(f"   [Fill] '{question[:30]}...' -> '{answer}' ({source})")
                        break
            else:
                form_filler.log_unknown_field(question, "radio", job_title, company)
                all_filled = False
                unknown_count += 1
        except:
            continue

    # Textareas
    textareas = page.locator("textarea")
    for i in range(textareas.count()):
        try:
            field = textareas.nth(i)
            if not field.is_visible():
                continue

            field_id = field.get_attribute("id") or ""
            label = page.locator(f"label[for='{field_id}']")
            
            if label.count() > 0:
                question = label.first.inner_text().strip()
            else:
                question = field.get_attribute("placeholder") or "Unknown textarea"

            current_value = field.input_value()
            if current_value:
                continue

            answer, source = form_filler.get_answer(question, "textarea")

            if answer:
                field.fill(answer)
                print(f"   [Fill] '{question[:30]}...' -> '{answer[:30]}...' ({source})")
            else:
                form_filler.log_unknown_field(question, "textarea", job_title, company)
                all_filled = False
                unknown_count += 1
        except:
            continue

    return all_filled, unknown_count


def handle_application_modal(page, form_filler, job_title="", company="", resume_dropdown_name=""):
    """Navigate through Easy Apply modal with form filling."""
    print("   [Form] Attempting to navigate form...")
    max_steps = 10

    for step in range(max_steps):
        random_sleep(1, 2)

        # Fill fields on current step (we don't track unknown count anymore)
        detect_and_fill_fields(
            page, form_filler, job_title, company, resume_dropdown_name
        )

        # Check for "Submit application" button
        submit_btn = page.locator("button[aria-label='Submit application']")
        if submit_btn.count() > 0 and submit_btn.first.is_visible():
            # Check for validation errors before submitting
            error_msg = page.locator("div.artdeco-inline-feedback--error")
            if error_msg.count() > 0 and error_msg.first.is_visible():
                print("   [Form] Validation error on submit page. Skipping.")
                break
            
            print("   [Form] Clicking SUBMIT!")
            submit_btn.first.click()
            random_sleep(3, 5)

            close_btn = page.locator("button[aria-label='Dismiss']")
            if close_btn.count() > 0 and close_btn.first.is_visible():
                close_btn.first.click()
            return True

        # Check for "Next" or "Review" buttons
        next_btn = page.locator("button[aria-label='Continue to next step']")
        review_btn = page.locator("button[aria-label='Review your application']")

        if next_btn.count() > 0 and next_btn.first.is_visible():
            # Check for validation errors before clicking Next
            error_msg = page.locator("div.artdeco-inline-feedback--error")
            if error_msg.count() > 0 and error_msg.first.is_visible():
                print(f"   [Form] Step {step+1}: Validation error. Cannot proceed.")
                break
            
            print(f"   [Form] Step {step+1}: Clicking Next...")
            next_btn.first.click()
            random_sleep(1, 2)

        elif review_btn.count() > 0 and review_btn.first.is_visible():
            # Check for validation errors before clicking Review
            error_msg = page.locator("div.artdeco-inline-feedback--error")
            if error_msg.count() > 0 and error_msg.first.is_visible():
                print(f"   [Form] Step {step+1}: Validation error. Cannot proceed.")
                break
                
            print(f"   [Form] Step {step+1}: Clicking Review...")
            review_btn.first.click()
            random_sleep(1, 2)
        else:
            print(f"   [Form] Step {step+1}: No navigation button found.")
            break

    # Dismiss modal
    print("   [Form] Dismissing application...")
    dismiss_btn = page.locator("button[aria-label='Dismiss']")
    if dismiss_btn.count() > 0 and dismiss_btn.first.is_visible():
        dismiss_btn.first.click()
        random_sleep(1, 2)

        discard_confirm = page.locator("button[data-control-name='discard_application_confirm_btn']")
        if discard_confirm.count() > 0 and discard_confirm.first.is_visible():
            discard_confirm.first.click()

    return False


def go_to_next_page(page):
    """Navigate to the next page of results. Returns True if successful."""
    try:
        # Find current page number
        current_page = page.locator("button[aria-current='true']")
        if current_page.count() == 0:
            return False
        
        current_num = int(current_page.first.inner_text().strip())
        next_num = current_num + 1
        
        # Click next page button
        next_page_btn = page.locator(f"button[aria-label='Page {next_num}']")
        if next_page_btn.count() > 0:
            next_page_btn.first.click()
            random_sleep(3, 5)
            return True
        
        return False
    except:
        return False


def process_jobs_on_page(page, form_filler, stats):
    """Process all jobs on current page. Returns updated stats."""
    card_selector = "div.job-card-container"
    
    # Scroll to load jobs
    job_list = page.locator("div.job-card-list")
    if job_list.count() > 0:
        job_list.first.hover()
    
    for _ in range(3):
        page.mouse.wheel(0, 1500)
        random_sleep(1, 2)

    count = page.locator(card_selector).count()
    print(f"[ApplyPilot] Found {count} job cards on this page.")

    for idx in range(count):
        # Check limits
        if stats["applied"] >= MAX_APPLICATIONS_PER_RUN:
            print(f"\n[ApplyPilot] Reached max applications ({MAX_APPLICATIONS_PER_RUN}). Stopping.")
            return stats, True
        
        if stats["processed"] >= MAX_JOBS_TO_PROCESS:
            print(f"\n[ApplyPilot] Reached max jobs to process ({MAX_JOBS_TO_PROCESS}). Stopping.")
            return stats, True

        stats["processed"] += 1
        print(f"\n[ApplyPilot] Processing Job #{stats['processed']}...")

        current_job = page.locator(card_selector).nth(idx)

        try:
            current_job.scroll_into_view_if_needed()
            random_sleep(0.5, 1)
        except:
            pass

        current_job.click()
        random_sleep(2, 3)

        # Extract job info
        job_title = ""
        company = ""
        try:
            title_el = page.locator("h1.t-24, h2.t-24")
            if title_el.count() > 0:
                job_title = title_el.first.inner_text().strip()
            company_el = page.locator("div.job-details-jobs-unified-top-card__company-name a")
            if company_el.count() > 0:
                company = company_el.first.inner_text().strip()
        except:
            pass

        print(f"   [Job] {job_title} at {company}" if job_title else "   [Job] Unknown position")

        # Check if already applied
        if check_already_applied(page):
            print("   [Skip] Already applied to this job.")
            stats["already_applied"] += 1
            continue

        # Select appropriate resume
        resume_type = form_filler.set_job_context(job_title)
        resume_dropdown_name = form_filler.get_resume_dropdown_name()
        print(f"   [Resume] Type: {resume_type} | Dropdown: {resume_dropdown_name}")

        # Look for Easy Apply button
        apply_btn = page.locator("button.jobs-apply-button")

        if apply_btn.count() > 0:
            btn_text = apply_btn.first.inner_text().strip().lower()

            if "easy apply" in btn_text:
                print("   [Apply] 'Easy Apply' button found. Clicking...")
                apply_btn.first.click()
                random_sleep(2, 3)

                success = handle_application_modal(page, form_filler, job_title, company)
                if success:
                    print("   [Apply] SUCCESS: Application submitted.")
                    stats["applied"] += 1
                    log_application(job_title, company, "submitted", resume_type)
                else:
                    print("   [Apply] SKIPPED: Could not complete form.")
                    stats["skipped"] += 1
                    log_application(job_title, company, "skipped", resume_type)
            else:
                print("   [Skip] External application.")
                stats["external"] += 1
        else:
            print("   [Skip] No apply button found.")
            stats["no_button"] += 1

    return stats, False


def main():
    parser = argparse.ArgumentParser(description="ApplyPilot Agent - LinkedIn Easy Apply Automation")
    parser.add_argument("--keywords", type=str, help="Search keywords (e.g., 'frontend engineer')")
    parser.add_argument("--limit", type=int, help="Max applications to submit")
    args = parser.parse_args()

    # Build search URL
    search_url = build_search_url(keywords=args.keywords)
    max_apps = args.limit or MAX_APPLICATIONS_PER_RUN

    # Initialize components
    browser = BrowserManager()
    form_filler = FormFiller()

    page = browser.launch()
    print("[ApplyPilot] Browser launched. Please ensure you are logged in.")

    page.goto(search_url, timeout=60000)
    print(f"[ApplyPilot] Search loaded: {args.keywords or 'default keywords'}")

    stats = {
        "processed": 0,
        "applied": 0,
        "skipped": 0,
        "already_applied": 0,
        "external": 0,
        "no_button": 0
    }

    try:
        card_selector = "div.job-card-container"
        page.wait_for_selector(card_selector, timeout=20000)
        print("[ApplyPilot] Job cards detected.")

        current_page = 1
        should_stop = False

        while not should_stop and current_page <= MAX_PAGES:
            print(f"\n{'='*50}")
            print(f"[ApplyPilot] Processing Page {current_page}")
            print(f"{'='*50}")

            stats, should_stop = process_jobs_on_page(page, form_filler, stats)

            if not should_stop and ENABLE_PAGINATION and current_page < MAX_PAGES:
                if go_to_next_page(page):
                    current_page += 1
                    random_sleep(2, 3)
                else:
                    print("[ApplyPilot] No more pages available.")
                    break
            else:
                break

    except TimeoutError:
        print("[ApplyPilot] Timeout waiting for elements.")
    except Exception as e:
        print(f"[ApplyPilot] Error: {e}")

    # Summary
    print(f"\n{'='*50}")
    print("[ApplyPilot] Session Complete")
    print(f"{'='*50}")
    print(f"   Jobs Processed:   {stats['processed']}")
    print(f"   Applied:          {stats['applied']}")
    print(f"   Skipped (fields): {stats['skipped']}")
    print(f"   Already Applied:  {stats['already_applied']}")
    print(f"   External Links:   {stats['external']}")
    print(f"   No Button:        {stats['no_button']}")

    unknowns = form_filler.get_unknown_fields()
    if unknowns:
        print(f"\n[ApplyPilot] {len(unknowns)} unknown fields logged.")
        print("   Run 'python learn_fields.py' to fill them in.")

    browser.close()


if __name__ == "__main__":
    main()