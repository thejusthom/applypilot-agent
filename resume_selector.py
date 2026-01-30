import json
from pathlib import Path
from config import RESUME_DROPDOWN_NAMES, RESUME_KEYWORDS

class ResumeSelector:
    """
    Selects the appropriate resume based on job title keywords.
    Returns both the JSON profile data and the LinkedIn dropdown name.
    """

    def __init__(self, resumes_dir="resumes"):
        self.resumes_dir = Path(resumes_dir)
        self.dropdown_names = RESUME_DROPDOWN_NAMES
        self.keywords = RESUME_KEYWORDS
        self.default_type = "fullstack"
        self._cache = {}

    def _load_resume(self, resume_type):
        """Load and cache a resume JSON file."""
        if resume_type in self._cache:
            return self._cache[resume_type]
        
        path = self.resumes_dir / f"{resume_type}.json"
        if path.exists():
            with open(path, "r") as f:
                self._cache[resume_type] = json.load(f)
                return self._cache[resume_type]
        return None

    def get_resume_type(self, job_title, job_description=""):
        """
        Determine which resume type to use based on job title/description.
        Returns: 'frontend', 'backend', 'sre', or 'fullstack'
        """
        search_text = f"{job_title} {job_description}".lower()

        # Check each type's keywords (order: frontend, backend, sre, then fullstack)
        for resume_type in ["frontend", "backend", "sre", "fullstack"]:
            keywords = self.keywords.get(resume_type, [])
            for keyword in keywords:
                if keyword in search_text:
                    return resume_type

        return self.default_type

    def select(self, job_title, job_description=""):
        """
        Select the best resume for a given job.
        Returns (resume_data, resume_type)
        """
        resume_type = self.get_resume_type(job_title, job_description)
        resume_data = self._load_resume(resume_type)
        
        if not resume_data:
            # Fallback to fullstack if specific type not found
            resume_data = self._load_resume(self.default_type)
            resume_type = self.default_type
        
        return resume_data, resume_type

    def get_dropdown_name(self, job_title, job_description=""):
        """
        Get the EXACT name that appears in LinkedIn's resume dropdown.
        This must match what you've uploaded to LinkedIn.
        """
        resume_type = self.get_resume_type(job_title, job_description)
        return self.dropdown_names.get(resume_type, self.dropdown_names[self.default_type])

    def get_all_dropdown_names(self):
        """Return all configured dropdown names for debugging."""
        return self.dropdown_names