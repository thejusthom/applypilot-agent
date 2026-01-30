#!/usr/bin/env python
"""
Interactive CLI tool to review and fill unknown form fields.
Run this after the agent encounters fields it doesn't know.
"""

from form_filler import FormFiller


def clean_question(question):
    """Remove duplicate lines from question text."""
    lines = question.split('\n')
    seen = []
    for line in lines:
        line = line.strip()
        if line and line not in seen and line.lower() != 'required':
            seen.append(line)
    return ' '.join(seen)


def main():
    filler = FormFiller()
    unknowns = filler.get_unknown_fields()

    if not unknowns:
        print("No unknown fields to fill! You're all caught up.")
        return

    print(f"\n{'='*60}")
    print(f"  ApplyPilot Field Trainer")
    print(f"  {len(unknowns)} unknown field(s) to review")
    print(f"{'='*60}\n")

    print("Commands:")
    print("  - For options: type the number (1, 2, 3...)")
    print("  - For text fields: type your answer")
    print("  - 'skip' to skip this field")
    print("  - 'delete' to remove from list")
    print("  - 'quit' to exit\n")

    filled = 0
    for i, field in enumerate(unknowns[:], 1):
        question = field['question']
        field_type = field['field_type']
        options = field.get('options') or []
        
        # Clean up question display
        clean_q = clean_question(question)
        
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(unknowns)}] {clean_q}")
        print(f"    Type: {field_type}")
        if field.get('job_title'):
            print(f"    From: {field['job_title']} at {field.get('company', 'Unknown')}")
        
        # Show options if available
        if options and len(options) > 0:
            print(f"\n    Options:")
            for idx, opt in enumerate(options, 1):
                print(f"      [{idx}] {opt}")
            print(f"\n    Enter number (1-{len(options)}): ", end="")
        else:
            # For fields without options, show common choices for radio/select
            if field_type in ['radio', 'select']:
                print(f"\n    No options captured. Common answers:")
                print(f"      [1] Yes")
                print(f"      [2] No")
                print(f"    Enter 1, 2, or type custom: ", end="")
            else:
                print(f"\n    Your answer: ", end="")
        
        answer = input().strip()

        if answer.lower() == 'quit':
            print("\nExiting. Progress saved.")
            break
        elif answer.lower() == 'skip' or answer == '':
            print("    → Skipped.")
            continue
        elif answer.lower() == 'delete':
            filler.remove_unknown_field(field['question'])
            print("    → Deleted from list.")
            continue
        
        # Handle numeric selection
        if answer.isdigit():
            idx = int(answer) - 1
            if options and 0 <= idx < len(options):
                answer = options[idx]
            elif field_type in ['radio', 'select'] and not options:
                # Default Yes/No mapping
                if answer == '1':
                    answer = 'Yes'
                elif answer == '2':
                    answer = 'No'
        
        # Save the answer
        filler.learn_field(field['question'], answer)
        filled += 1
        print(f"    → Saved: {answer}")

    print(f"\n{'='*60}")
    print(f"  Done! Filled {filled} field(s).")
    print(f"  Remaining unknown: {len(filler.get_unknown_fields())}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()