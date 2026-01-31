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
    APPLICATION_LOG_PATH, PREFERRED_EMAIL
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
    applied_badge = page.locator("span.artdeco-inline-feedback__message:has-text('Applied')")
    applied_badge2 = page.locator("li-icon[type='success-pebble-icon']")
    applied_text = page.locator(".jobs-s-apply__application-link")
    
    if applied_badge.count() > 0 or applied_badge2.count() > 0 or applied_text.count() > 0:
        return True
    
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
    except Exception as e:
        print(f"   [Form] Follow checkbox error: {e}")
    
    return False


def select_resume_in_dropdown(page, resume_dropdown_name):
    """
    Select the correct resume from LinkedIn's resume list.
    Clicks the card/row to properly trigger LinkedIn's form validation.
    """
    try:
        print(f"   [Resume] Looking for: {resume_dropdown_name}")
        
        # FIRST: Expand the resume list if collapsed
        expand_btn = page.locator("button:has-text('more resumes')")
        if expand_btn.count() > 0 and expand_btn.first.is_visible():
            expand_btn.first.click()
            print("   [Resume] Expanded resume list")
            random_sleep(1, 2)
        
        # Find all download buttons - they contain the actual filename in aria-label
        download_btns = page.locator("button[aria-label*='Download resume']")
        btn_count = download_btns.count()
        print(f"   [Resume] Found {btn_count} resume download buttons")
        
        if btn_count == 0:
            print("   [Resume] No resume buttons found")
            return False
        
        # Also get radio buttons
        radios = page.locator("input[type='radio'][id^='jobsDocumentCardToggle']:visible")
        
        # First, print ALL resumes found for debugging
        target_index = -1
        for i in range(btn_count):
            btn = download_btns.nth(i)
            aria_label = btn.get_attribute("aria-label") or ""
            print(f"   [Resume] [{i}] {aria_label}")
            if resume_dropdown_name.lower() in aria_label.lower():
                target_index = i
        
        if target_index == -1:
            print(f"   [Resume] ✗ Could not find: {resume_dropdown_name}")
            return False
        
        print(f"   [Resume] Target found at index {target_index}")
        
        # Check if already selected
        if target_index < radios.count():
            radio = radios.nth(target_index)
            if radio.is_checked():
                print(f"   [Resume] ✓ Already selected: {resume_dropdown_name}")
                return True
        
        # METHOD 1: Try clicking the radio button directly with JS
        if target_index < radios.count():
            radio = radios.nth(target_index)
            try:
                radio.evaluate("""el => {
                    el.click();
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }""")
                random_sleep(0.5, 1)
                
                # Verify selection
                if radio.is_checked():
                    print(f"   [Resume] ✓ Selected via radio click: {resume_dropdown_name}")
                    return True
                else:
                    print(f"   [Resume] Radio click didn't work, trying card click...")
            except Exception as e:
                print(f"   [Resume] Radio click error: {e}")
        
        # METHOD 2: Find and click the parent card/row
        btn = download_btns.nth(target_index)
        card = btn.locator("xpath=ancestor::div[contains(@class, 'jobs-document-upload')]").first
        
        if card and card.is_visible():
            card.click()
            random_sleep(0.5, 1)
            print(f"   [Resume] ✓ Clicked card for: {resume_dropdown_name}")
            return True
        
        # METHOD 3: Click the label/text area
        try:
            resume_text = page.locator(f"text='{resume_dropdown_name}'").first
            if resume_text and resume_text.is_visible():
                resume_text.click()
                random_sleep(0.5, 1)
                print(f"   [Resume] ✓ Clicked text for: {resume_dropdown_name}")
                return True
        except:
            pass
        
        print(f"   [Resume] ✗ All methods failed for: {resume_dropdown_name}")
        return False
        
    except Exception as e:
        print(f"   [Resume] Error: {e}")
        return False


def detect_and_fill_fields(page, form_filler, job_title="", company=""):
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

    # Uncheck "Follow company" if present
    uncheck_follow_company(page)
    
    # Handle email dropdowns specifically (LinkedIn shows saved emails as dropdown)
    email_selects = page.locator("select:visible")
    for i in range(email_selects.count()):
        try:
            field = email_selects.nth(i)
            field_id = field.get_attribute("id") or ""
            label = page.locator(f"label[for='{field_id}']")
            
            if label.count() > 0:
                label_text = label.first.inner_text().strip().lower()
            else:
                label_text = field.get_attribute("aria-label") or ""
                label_text = label_text.lower()
            
            # Check if this is an email field
            if "email" in label_text and PREFERRED_EMAIL:
                try:
                    field.select_option(label=PREFERRED_EMAIL)
                    print(f"   [Fill] Email dropdown -> '{PREFERRED_EMAIL}'")
                except:
                    try:
                        field.select_option(value=PREFERRED_EMAIL)
                        print(f"   [Fill] Email dropdown -> '{PREFERRED_EMAIL}'")
                    except:
                        pass
        except:
            continue

    # Text inputs
    text_inputs = page.locator("input[type='text']:visible, input:not([type]):visible")
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

    # Radio buttons (Yes/No questions and other radio groups)
    fieldsets = page.locator("fieldset:visible")
    for i in range(fieldsets.count()):
        try:
            fieldset = fieldsets.nth(i)
            if not fieldset.is_visible():
                continue

            legend = fieldset.locator("legend")
            if legend.count() == 0:
                continue

            question = legend.first.inner_text().strip()
            
            # Clean up duplicate text in question
            lines = question.split('\n')
            if len(lines) > 1 and lines[0].strip() == lines[1].strip():
                question = lines[0].strip()
            
            # Skip ignored fields
            if any(ignored in question.lower() for ignored in IGNORED_FIELDS):
                continue
            
            # Check if already answered
            checked = fieldset.locator("input[type='radio']:checked")
            if checked.count() > 0:
                continue

            answer, source = form_filler.get_answer(question, "radio")

            # Capture all radio options - try multiple methods
            options = []
            
            # Method 1: Labels inside fieldset
            radio_labels = fieldset.locator("label")
            for j in range(radio_labels.count()):
                opt_text = radio_labels.nth(j).inner_text().strip()
                if opt_text and opt_text.lower() not in ['required', '']:
                    options.append(opt_text)
            
            # Method 2: If no labels found, try getting text near radio inputs
            if not options:
                radio_inputs = fieldset.locator("input[type='radio']")
                for j in range(radio_inputs.count()):
                    try:
                        radio = radio_inputs.nth(j)
                        parent = radio.locator("xpath=parent::*")
                        if parent.count() > 0:
                            text = parent.first.inner_text().strip()
                            if text and text.lower() not in ['required', '']:
                                options.append(text)
                    except:
                        pass
            
            # Method 3: Common Yes/No pattern
            if not options:
                fieldset_text = fieldset.inner_text().lower()
                if 'yes' in fieldset_text and 'no' in fieldset_text:
                    options = ['Yes', 'No']

            if answer:
                # Find the radio button with matching label
                matched = False
                for j in range(radio_labels.count()):
                    label_text = radio_labels.nth(j).inner_text().strip().lower()
                    if answer.lower() in label_text or label_text in answer.lower():
                        radio_labels.nth(j).click()
                        print(f"   [Fill] '{question[:30]}...' -> '{answer}' ({source})")
                        matched = True
                        break
                if not matched:
                    form_filler.log_unknown_field(question, "radio", job_title, company, options)
                    all_filled = False
                    unknown_count += 1
            else:
                form_filler.log_unknown_field(question, "radio", job_title, company, options)
                all_filled = False
                unknown_count += 1

        except Exception as e:
            continue

    # Textareas (essay questions)
    textareas = page.locator("textarea:visible")
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
    resume_selected = False

    for step in range(max_steps):
        random_sleep(1, 2)

        # Try to select resume on first 3 steps if not already done
        if step < 3 and resume_dropdown_name and not resume_selected:
            # Check for resume section - look for resume radio buttons directly
            resume_radios = page.locator("input[type='radio'][id^='jobsDocumentCardToggle']:visible")
            resume_header = page.locator("h3:has-text('Resume'):visible")
            upload_btn = page.locator("button:has-text('Upload resume'):visible")
            
            radio_count = resume_radios.count()
            header_count = resume_header.count()
            upload_count = upload_btn.count()
            
            print(f"   [Debug] Step {step+1} resume check: radios={radio_count}, header={header_count}, upload={upload_count}")
            
            if radio_count > 0 or header_count > 0 or upload_count > 0:
                print(f"   [Resume] Resume section detected on step {step + 1}")
                resume_selected = select_resume_in_dropdown(page, resume_dropdown_name)

        # Fill fields on current step
        detect_and_fill_fields(page, form_filler, job_title, company)

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
        current_page = page.locator("button[aria-current='true']")
        if current_page.count() == 0:
            return False
        
        current_num = int(current_page.first.inner_text().strip())
        next_num = current_num + 1
        
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

        # Select appropriate resume based on job title
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

                success = handle_application_modal(
                    page, form_filler, job_title, company, resume_dropdown_name
                )
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