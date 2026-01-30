import json
from pathlib import Path
from difflib import SequenceMatcher
from resume_selector import ResumeSelector

class FormFiller:
    """
    Handles form field detection, filling, and memory management.
    Learns from unknown fields and stores answers for reuse.
    """

    def __init__(self, resume_path="resume.json", memory_path="field_memory.json"):
        self.resume_path = Path(resume_path)
        self.memory_path = Path(memory_path)
        self.resume = self._load_json(self.resume_path, {})
        self.memory = self._load_json(self.memory_path, {
            "known_fields": {},
            "unknown_fields": [],
            "field_log": []
        })
        self.resume_selector = ResumeSelector()
        self.current_resume_type = "fullstack"
        
        # Validate resume loaded
        if not self.resume:
            print("[Warning] resume.json not found or empty. Form filling may fail.")

    def _load_json(self, path, default):
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return default

    def _save_memory(self):
        with open(self.memory_path, "w") as f:
            json.dump(self.memory, f, indent=2)

    def _similarity(self, a, b):
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_best_match(self, question, threshold=0.7):
        """
        Find the best matching known field for a question.
        Returns (answer, confidence) or (None, 0) if no match.
        """
        best_match = None
        best_score = 0

        for known_q, answer in self.memory["known_fields"].items():
            score = self._similarity(question, known_q)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = answer

        return best_match, best_score

    def get_answer(self, question, field_type="text"):
        """
        Get answer for a form field question.
        Returns (answer, source) where source is 'memory', 'resume', or 'unknown'
        """
        # 1. Check exact match in memory
        if question in self.memory["known_fields"]:
            return self.memory["known_fields"][question], "memory"

        # 2. Check fuzzy match in memory
        fuzzy_answer, score = self.find_best_match(question)
        if fuzzy_answer:
            return fuzzy_answer, "memory_fuzzy"

        # 3. Try to infer from resume based on keywords
        q_lower = question.lower()

        # Personal info
        if any(kw in q_lower for kw in ["first name"]):
            return self.resume.get("personal", {}).get("first_name"), "resume"
        if any(kw in q_lower for kw in ["last name"]):
            return self.resume.get("personal", {}).get("last_name"), "resume"
        if any(kw in q_lower for kw in ["email", "e-mail"]):
            return self.resume.get("personal", {}).get("email"), "resume"
        if any(kw in q_lower for kw in ["phone", "mobile", "contact number"]):
            return self.resume.get("personal", {}).get("phone"), "resume"
        if any(kw in q_lower for kw in ["linkedin"]):
            return self.resume.get("personal", {}).get("linkedin"), "resume"
        if any(kw in q_lower for kw in ["github"]):
            return self.resume.get("personal", {}).get("github"), "resume"
        if any(kw in q_lower for kw in ["portfolio", "website"]):
            return self.resume.get("personal", {}).get("portfolio"), "resume"
        if any(kw in q_lower for kw in ["city"]):
            return self.resume.get("personal", {}).get("location", {}).get("city"), "resume"
        if any(kw in q_lower for kw in ["state"]):
            return self.resume.get("personal", {}).get("location", {}).get("state"), "resume"
        if any(kw in q_lower for kw in ["zip", "postal"]):
            return self.resume.get("personal", {}).get("location", {}).get("zip"), "resume"

        # Work authorization
        if any(kw in q_lower for kw in ["authorized to work", "legally authorized", "work authorization"]):
            return "Yes" if self.resume.get("work_authorization", {}).get("authorized_us") else "No", "resume"
        if any(kw in q_lower for kw in ["sponsorship", "visa sponsorship"]):
            return "Yes" if self.resume.get("work_authorization", {}).get("sponsorship_required") else "No", "resume"

        # Experience
        if "years" in q_lower and "experience" in q_lower:
            return self.resume.get("experience", {}).get("years_of_experience"), "resume"

        # Common questions
        if any(kw in q_lower for kw in ["relocate", "relocation"]):
            return self.resume.get("common_answers", {}).get("willing_to_relocate"), "resume"
        if any(kw in q_lower for kw in ["start date", "when can you start", "earliest start"]):
            return self.resume.get("common_answers", {}).get("start_date"), "resume"
        if any(kw in q_lower for kw in ["salary", "compensation", "pay"]):
            return self.resume.get("common_answers", {}).get("salary_expectation"), "resume"
        if any(kw in q_lower for kw in ["how did you hear", "how did you find", "where did you hear"]):
            return self.resume.get("common_answers", {}).get("how_did_you_hear"), "resume"

        # No match found
        return None, "unknown"

    def log_unknown_field(self, question, field_type, job_title="", company="", options=None):
        """Log an unknown field for later review."""
        entry = {
            "question": question,
            "field_type": field_type,
            "job_title": job_title,
            "company": company,
            "options": options or [],  # Store dropdown/radio options
            "answer": None
        }

        # Avoid duplicates
        existing_questions = [f["question"] for f in self.memory["unknown_fields"]]
        if question not in existing_questions:
            self.memory["unknown_fields"].append(entry)
            self._save_memory()
            print(f"   [Memory] Logged unknown field: '{question[:50]}...'")

    def remove_unknown_field(self, question):
        """Remove a field from unknown list."""
        self.memory["unknown_fields"] = [
            f for f in self.memory["unknown_fields"] 
            if f["question"] != question
        ]
        self._save_memory()

    def learn_field(self, question, answer):
        """Add a new question-answer pair to memory."""
        self.memory["known_fields"][question] = answer
        
        # Remove from unknown if it was there
        self.memory["unknown_fields"] = [
            f for f in self.memory["unknown_fields"] 
            if f["question"] != question
        ]
        
        self._save_memory()
        print(f"   [Memory] Learned: '{question[:40]}...' -> '{answer[:20]}...'")

    def get_unknown_fields(self):
        """Return list of unknown fields that need answers."""
        return self.memory["unknown_fields"]

    def set_job_context(self, job_title, job_description=""):
        """Set the current job context to determine which resume PDF to use."""
        self.current_resume_type = self.resume_selector.get_resume_type(job_title, job_description)
        
        # Try to load type-specific resume, fall back to main resume.json
        resume_data, _ = self.resume_selector.select(job_title, job_description)
        if resume_data:
            self.resume = resume_data
        # If no type-specific resume found, keep using the main resume.json
        
        return self.current_resume_type

    def get_resume_dropdown_name(self):
        """Get the LinkedIn dropdown name for the current resume type."""
        return self.resume_selector.dropdown_names.get(
            self.current_resume_type, 
            self.resume_selector.dropdown_names["fullstack"]
        )

    def fill_unknown_fields_interactive(self):
        """Interactive CLI to fill in unknown fields."""
        unknowns = self.memory["unknown_fields"]
        
        if not unknowns:
            print("No unknown fields to fill!")
            return

        print(f"\n{'='*60}")
        print(f"Found {len(unknowns)} unknown fields. Let's fill them in.")
        print(f"{'='*60}\n")

        for i, field in enumerate(unknowns[:], 1):
            print(f"[{i}/{len(unknowns)}] {field['question']}")
            if field.get('job_title'):
                print(f"    (From: {field['job_title']} at {field.get('company', 'Unknown')})")
            
            answer = input("    Your answer (or 'skip'): ").strip()
            
            if answer.lower() != 'skip' and answer:
                self.learn_field(field['question'], answer)

        print("\nDone! Memory updated.")