# ApplyPilot Agent

ApplyPilot Agent is a private, on-demand AI-assisted automation agent that helps discover relevant job postings, score them against a structured resume profile, and assist with submitting applications using browser automation and human-in-the-loop approvals.

> ⚠️ This project is designed strictly for personal use.

---

## Motivation
Manually applying to jobs is repetitive, time-consuming, and error-prone. ApplyPilot Agent was built to streamline this process while maintaining application quality, platform safety, and human oversight.

---

## Features
- On-demand job discovery
- Resume-to-job relevance scoring
- Automated form filling for standardized applications (LinkedIn Easy Apply)
- Human-in-the-loop approval for custom or ambiguous questions
- Local execution (no backend, no SaaS)

---

## Tech Stack
- Python
- Playwright
- OpenAI API
- SQLite / JSON

---

## Project Structure
```txt
applypilot-agent/
├── agent.py            # Agent controller and execution flow
├── browser.py          # Playwright browser automation
├── matcher.py          # Resume ↔ job relevance scoring
├── resume.json         # Structured resume memory
└── README.md
