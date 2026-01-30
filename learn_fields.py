#!/usr/bin/env python
"""
Interactive CLI tool to review and fill unknown form fields.
Run this after the agent encounters fields it doesn't know.
"""

from form_filler import FormFiller

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
    print("  - Type your answer to save it")
    print("  - 'skip' to skip this field")
    print("  - 'quit' to exit\n")

    filled = 0
    for i, field in enumerate(unknowns[:], 1):
        print(f"[{i}/{len(unknowns)}] Question:")
        print(f"    \"{field['question']}\"")
        print(f"    Type: {field['field_type']}")
        if field.get('job_title'):
            print(f"    From: {field['job_title']} at {field.get('company', 'Unknown')}")

        answer = input("\n    Your answer: ").strip()

        if answer.lower() == 'quit':
            print("\nExiting. Progress saved.")
            break
        elif answer.lower() == 'skip' or not answer:
            print("    Skipped.\n")
        else:
            filler.learn_field(field['question'], answer)
            filled += 1
            print(f"    Saved!\n")

    print(f"\n{'='*60}")
    print(f"  Done! Filled {filled} field(s).")
    print(f"  Remaining unknown: {len(filler.get_unknown_fields())}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()