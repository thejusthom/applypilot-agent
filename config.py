"""
ApplyPilot Agent Configuration
Loads personal info from .env file
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# RESUME MAPPING - Loaded from .env
# =============================================================================
RESUME_DROPDOWN_NAMES = {
    "frontend": os.getenv("RESUME_FRONTEND", "Resume_Frontend.pdf"),
    "backend": os.getenv("RESUME_BACKEND", "Resume_Backend.pdf"), 
    "sre": os.getenv("RESUME_SRE", "Resume_SRE.pdf"),
    "fullstack": os.getenv("RESUME_FULLSTACK", "Resume_FullStack.pdf")
}

# Keywords that trigger each resume type (checked against job title)
RESUME_KEYWORDS = {
    "frontend": ["frontend", "front-end", "front end", "react", "vue", "angular", "ui engineer", "ui developer", "javascript developer"],
    "backend": ["backend", "back-end", "back end", "java developer", "python developer", "api engineer", "server", "spring", "node.js"],
    "sre": ["sre", "site reliability", "devops", "platform engineer", "infrastructure", "cloud engineer", "kubernetes", "aws engineer"],
    "fullstack": ["fullstack", "full-stack", "full stack", "software engineer", "software developer", "sde", "new grad", "associate"]
}

# LinkedIn search settings
SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "software engineer new grad")
SEARCH_LOCATION_ID = os.getenv("SEARCH_LOCATION_ID", "103644278")  # United States
EASY_APPLY_ONLY = True
DISTANCE_MILES = 25
TIME_FILTER = "r8640"  # r86400 = past 24h, r604800 = past week, r2592000 = past month

# Agent behavior
MAX_APPLICATIONS_PER_RUN = 25      # Keep under 30 to avoid LinkedIn rate limits
MAX_JOBS_TO_PROCESS = 75           # Max jobs to look at (including skips)
ENABLE_PAGINATION = True           # Go to next page when current page is done
MAX_PAGES = 5                      # Max pages to process if pagination enabled

# Safety settings - longer delays to appear more human
MIN_DELAY_SECONDS = 3
MAX_DELAY_SECONDS = 7
SKIP_IF_UNKNOWN_FIELDS = False     # Skip application if there are unfillable fields

# Paths
RESUMES_DIR = "resumes"
FIELD_MEMORY_PATH = "field_memory.json"
APPLICATION_LOG_PATH = "application_log.json"

# Preferred email for dropdown selection
PREFERRED_EMAIL = os.getenv("EMAIL", "")


def build_search_url(keywords=None, location_id=None):
    """Build LinkedIn job search URL from config."""
    kw = keywords or SEARCH_KEYWORDS
    loc = location_id or SEARCH_LOCATION_ID
    
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={kw.replace(' ', '%20')}"
        f"&geoId={loc}"
        f"&distance={DISTANCE_MILES}"
        f"&f_TPR={TIME_FILTER}"
    )
    
    if EASY_APPLY_ONLY:
        url += "&f_AL=true"
    
    return url


def get_resume_data():
    """Build resume data dict from environment variables."""
    return {
        "personal": {
            "first_name": os.getenv("FIRST_NAME", ""),
            "last_name": os.getenv("LAST_NAME", ""),
            "full_name": f"{os.getenv('FIRST_NAME', '')} {os.getenv('LAST_NAME', '')}",
            "email": os.getenv("EMAIL", ""),
            "phone": os.getenv("PHONE", ""),
            "linkedin": os.getenv("LINKEDIN_URL", ""),
            "github": os.getenv("GITHUB_URL", ""),
            "portfolio": os.getenv("PORTFOLIO_URL", ""),
            "location": {
                "city": os.getenv("CITY", ""),
                "state": os.getenv("STATE", ""),
                "country": os.getenv("COUNTRY", ""),
                "zip": os.getenv("ZIP_CODE", "")
            }
        },
        "work_authorization": {
            "authorized_us": os.getenv("AUTHORIZED_TO_WORK", "true").lower() == "true",
            "sponsorship_required": os.getenv("REQUIRES_SPONSORSHIP", "false").lower() == "true",
            "visa_status": os.getenv("VISA_STATUS", ""),
            "work_authorization_text": "Yes" if os.getenv("AUTHORIZED_TO_WORK", "true").lower() == "true" else "No"
        },
        "education": {
            "degree": os.getenv("DEGREE", ""),
            "field": os.getenv("FIELD_OF_STUDY", ""),
            "university": os.getenv("UNIVERSITY", ""),
            "graduation_date": os.getenv("GRADUATION_DATE", ""),
            "gpa": os.getenv("GPA", "")
        },
        "experience": {
            "years_of_experience": os.getenv("YEARS_OF_EXPERIENCE", ""),
            "most_recent_title": os.getenv("CURRENT_TITLE", ""),
            "most_recent_company": os.getenv("CURRENT_COMPANY", "")
        },
        "common_answers": {
            "willing_to_relocate": os.getenv("WILLING_TO_RELOCATE", "Yes"),
            "start_date": os.getenv("START_DATE", "Immediately"),
            "salary_expectation": os.getenv("SALARY_EXPECTATION", "Open to discussion"),
            "how_did_you_hear": os.getenv("HOW_DID_YOU_HEAR", "LinkedIn"),
            "gender": os.getenv("GENDER", ""),
            "hispanic_latino": os.getenv("HISPANIC_LATINO", ""),
            "veteran_status": os.getenv("VETERAN_STATUS", ""),
            "disability_status": os.getenv("DISABILITY_STATUS", "")
        }
    }