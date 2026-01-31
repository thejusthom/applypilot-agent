# ApplyPilot Agent

ApplyPilot Agent is a private, on-demand AI-assisted automation agent that helps discover relevant job postings, automatically selects the appropriate resume based on job type, and assists with submitting LinkedIn Easy Apply applications using browser automation and intelligent form filling.

> ⚠️ This project is designed strictly for personal use.

---

## Motivation

Manually applying to jobs is repetitive, time-consuming, and error-prone. ApplyPilot Agent was built to streamline this process while maintaining application quality, platform safety, and human oversight.

---

## Features

### Core Automation
- **LinkedIn Easy Apply Automation** - Automatically navigates and submits Easy Apply applications
- **Persistent Browser Sessions** - Maintains login state across runs using Playwright
- **Multi-page Processing** - Processes jobs across multiple search result pages
- **Already Applied Detection** - Skips jobs you've already applied to

### Smart Resume Selection
- **Multiple Resume Support** - Maintains different resumes for different job types (frontend, backend, SRE, fullstack)
- **Automatic Resume Matching** - Selects the appropriate resume based on job title keywords
- **LinkedIn Resume Dropdown Handling** - Automatically selects the correct resume from LinkedIn's saved resumes

### Intelligent Form Filling
- **Structured Resume Memory** - Uses `resume.json` for consistent form data (name, email, phone, work authorization, etc.)
- **Field Memory System** - Learns and remembers answers to application questions
- **Dropdown & Radio Support** - Handles select dropdowns and radio button questions
- **Unknown Field Logging** - Captures new questions for later review and training

### Human-in-the-Loop
- **Interactive Field Trainer** - CLI tool to review and answer unknown questions
- **Option Selection** - Shows dropdown/radio options and allows numeric selection (1, 2, 3...)
- **Skip & Delete Controls** - Skip questions or remove irrelevant ones from the queue

### Safety & Rate Limiting
- **Configurable Limits** - Set max applications per run to avoid LinkedIn rate limits
- **Random Delays** - Human-like delays between actions
- **Follow Checkbox Handling** - Automatically unchecks "Follow company" checkboxes
- **Application Logging** - Tracks all applications with timestamps and status

---

## Tech Stack

- **Python 3.10+**
- **Playwright** - Browser automation
- **JSON** - Data storage (resumes, field memory, application logs)

---

## Project Structure

```
applypilot-agent/
├── agent.py              # Main agent controller and execution flow
├── browser.py            # Playwright browser manager with persistent sessions
├── form_filler.py        # Form field detection, filling, and memory management
├── resume_selector.py    # Resume type selection based on job keywords
├── learn_fields.py       # Interactive CLI to train unknown fields
├── config.py             # Configuration settings (loads from .env)
├── debug_selectors.py    # Debug tool for testing LinkedIn selectors
├── .env.example          # Template for environment variables
├── .env                  # Your personal config (not committed to git)
├── .gitignore            # Ensures .env and personal data not committed
├── field_memory.json     # Learned question-answer pairs
├── application_log.json  # History of all applications
├── browser_profile/      # Playwright session storage (auto-created)
└── README.md
```

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/applypilot-agent.git
cd applypilot-agent
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install playwright python-dotenv
playwright install chromium
```

### 4. Configure your environment

Copy the example environment file and fill in your personal information:
```bash
cp .env.example .env
```

Edit `.env` with your details:
```bash
# Personal Information
FIRST_NAME=John
LAST_NAME=Doe
EMAIL=johndoe@gmail.com
PHONE=1234567890

# Resume Filenames (must match EXACTLY what's in LinkedIn)
RESUME_FRONTEND=JohnDoe_Frontend.pdf
RESUME_BACKEND=JohnDoe_Backend.pdf
RESUME_SRE=JohnDoe_SRE.pdf
RESUME_FULLSTACK=JohnDoe_FullStack.pdf
```

> ⚠️ **Important:** Never commit your `.env` file. It's already in `.gitignore`.

### 5. First run - Login to LinkedIn
```bash
python agent.py
```
On first run, manually log in to LinkedIn in the browser window. Your session will be saved for future runs.

---

## Usage

### Basic Usage
```bash
python agent.py
```

### Custom Search Keywords
```bash
python agent.py --keywords "frontend react developer"
```

### With Application Limit
```bash
python agent.py --keywords "software engineer" --limit 10
```

### Train Unknown Fields
After running the agent, review and answer unknown questions:
```bash
python learn_fields.py
```

Example interaction:
```
[1/5] Are you authorized to work in the United States?
    Type: radio
    From: Software Engineer at Google

    Options:
      [1] Yes
      [2] No

    Enter number (1-2): 1
    → Saved: Yes
```

---

## Configuration

Edit `config.py` to customize behavior:

```python
# Search settings
SEARCH_KEYWORDS = "software engineer new grad"
EASY_APPLY_ONLY = True
TIME_FILTER = "r86400"  # r86400 = past 24h, r604800 = past week

# Agent limits (keep under 30/day to avoid rate limits)
MAX_APPLICATIONS_PER_RUN = 25
MAX_JOBS_TO_PROCESS = 75
MAX_PAGES = 5

# Delays (longer = safer)
MIN_DELAY_SECONDS = 3
MAX_DELAY_SECONDS = 7

# Resume keyword mappings
RESUME_KEYWORDS = {
    "frontend": ["react", "vue", "angular", "frontend"],
    "backend": ["java", "python", "backend", "api"],
    "sre": ["devops", "sre", "infrastructure", "kubernetes"],
    "fullstack": ["fullstack", "software engineer", "sde"]
}
```

---

## How It Works

### Resume Selection Flow
```
Job Title: "React Frontend Developer"
         ↓
Keyword Match: "react" → frontend
         ↓
Select Resume: YourName_Frontend.pdf
         ↓
Fill Forms: Uses resume.json data
```

### Form Filling Flow
```
1. Detect field (text, dropdown, radio, textarea)
2. Check field_memory.json for known answer
3. Check resume.json for profile data
4. If unknown → log to field_memory.json for training
5. Fill or skip based on configuration
```

---

## Rate Limiting & Safety

LinkedIn limits daily Easy Apply submissions. To avoid getting blocked:

- **Keep applications under 25-30 per day**
- **Run 2-3 sessions spaced throughout the day**
- **Use longer delays** (3-7 seconds between actions)
- **Don't run continuously for hours**

If you see "We limit daily submissions..." message, wait 24 hours before applying again.

---

## Debugging

### Test Resume Selection
```bash
python debug_selectors.py
```
Follow prompts to verify resume picker is working.

### Check Application Log
```bash
cat application_log.json
```

### View Unknown Fields
```bash
cat field_memory.json | python -m json.tool
```

---

## Roadmap

- [ ] Resume-to-job relevance scoring
- [ ] AI-generated answers for custom questions
- [ ] Support for other job platforms (Indeed, Glassdoor)
- [ ] Dashboard for tracking application status
- [ ] Cover letter generation

---

## Design Principles

- **Assistive automation over full autonomy** - Human oversight for critical decisions
- **Safety-first execution** - Rate limiting and delays to respect platform rules
- **Learning system** - Improves with use through field memory
- **Local-first** - No external servers, all data stays on your machine

---

## Disclaimer

This tool is for personal use only. Use responsibly and in accordance with LinkedIn's Terms of Service. The author is not responsible for any account restrictions resulting from misuse.

---

## License

MIT License - See LICENSE file for details.