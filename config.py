"""
ApplyPilot Agent Configuration
"""

# =============================================================================
# RESUME MAPPING - Update these to match EXACTLY what LinkedIn shows
# =============================================================================
RESUME_DROPDOWN_NAMES = {
    "frontend": "ThejusThomson_Resume.pdf",
    "backend": "ThejusThomson-resume.pdf", 
    "sre": "ThejusThomsonResume.pdf",
    "fullstack": "Thejus_Thomson_Resume.pdf"  # default
}

# Keywords that trigger each resume type (checked against job title)
RESUME_KEYWORDS = {
    "frontend": ["frontend", "front-end", "front end", "react", "vue", "angular", "ui engineer", "ui developer", "javascript developer"],
    "backend": ["backend", "back-end", "back end", "java developer", "python developer", "api engineer", "server", "spring", "node.js"],
    "sre": ["sre", "site reliability", "devops", "platform engineer", "infrastructure", "cloud engineer", "kubernetes", "aws engineer"],
    "fullstack": ["fullstack", "full-stack", "full stack", "software engineer", "software developer", "sde", "new grad", "associate"]
}

# LinkedIn search settings
SEARCH_KEYWORDS = "software engineer new grad"
SEARCH_LOCATION_ID = "103644278"  # United States
EASY_APPLY_ONLY = True
DISTANCE_MILES = 25
TIME_FILTER = "r8640"  # r86400 = past 24h, r604800 = past week, r2592000 = past month

# Agent behavior
MAX_APPLICATIONS_PER_RUN = 100      # Stop after this many applications
MAX_JOBS_TO_PROCESS = 50          # Max jobs to look at (including skips)
ENABLE_PAGINATION = True          # Go to next page when current page is done
MAX_PAGES = 3                     # Max pages to process if pagination enabled

# Safety settings
MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5
SKIP_IF_UNKNOWN_FIELDS = True     # Skip application if there are unfillable fields

# Paths
RESUMES_DIR = "resumes"
FIELD_MEMORY_PATH = "field_memory.json"
APPLICATION_LOG_PATH = "application_log.json"


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