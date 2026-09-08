import re
import json
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path


class WorkType(Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class ExperienceLevel(Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class EducationLevel(Enum):
    SMA = "SMA"
    D3 = "D3"
    S1 = "S1"
    S2 = "S2"


class CompanySize(Enum):
    STARTUP = "startup"
    SME = "sme"
    ENTERPRISE = "enterprise"


@dataclass
class FilterCriteria:
    """Kriteria untuk memfilter lowongan kerja"""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    company_size: Optional[List[CompanySize]] = None
    work_type: Optional[List[WorkType]] = None
    experience_level: Optional[List[ExperienceLevel]] = None
    education_level: Optional[List[EducationLevel]] = None
    industries: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konversi ke dictionary untuk penyimpanan"""
        return {
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "company_size": [cs.value for cs in self.company_size] if self.company_size else None,
            "work_type": [wt.value for wt in self.work_type] if self.work_type else None,
            "experience_level": [el.value for el in self.experience_level] if self.experience_level else None,
            "education_level": [el.value for el in self.education_level] if self.education_level else None,
            "industries": self.industries,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterCriteria':
        """Buat FilterCriteria dari dictionary"""
        return cls(
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            company_size=[CompanySize(v) for v in data.get("company_size", [])] if data.get("company_size") else None,
            work_type=[WorkType(v) for v in data.get("work_type", [])] if data.get("work_type") else None,
            experience_level=[ExperienceLevel(v) for v in data.get("experience_level", [])] if data.get("experience_level") else None,
            education_level=[EducationLevel(v) for v in data.get("education_level", [])] if data.get("education_level") else None,
            industries=data.get("industries"),
            keywords=data.get("keywords")
        )


class SmartFilter:
    """Filter cerdas untuk lowongan pekerjaan"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inisialisasi SmartFilter
        
        Args:
            config_path: Path ke file konfigurasi (opsional)
        """
        self.config_path = config_path or "filter_preferences.json"
        self.preferences: Optional[FilterCriteria] = None
        self._load_preferences()
    
    def _load_preferences(self) -> None:
        """Muat preferensi filter dari file konfigurasi"""
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.preferences = FilterCriteria.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading preferences: {e}")
                self.preferences = None
        else:
            self.preferences = None
    
    def save_preferences(self, criteria: Optional[FilterCriteria] = None) -> None:
        """
        Simpan preferensi filter ke file konfigurasi
        
        Args:
            criteria: Kriteria filter yang akan disimpan. Jika None, gunakan self.preferences
        """
        if criteria is not None:
            self.preferences = criteria
        
        if self.preferences is None:
            return
        
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.preferences.to_dict(), f, indent=2, ensure_ascii=False)
    
    def set_preferences(self, criteria: FilterCriteria) -> None:
        """
        Set preferensi filter dan simpan
        
        Args:
            criteria: Kriteria filter
        """
        self.preferences = criteria
        self.save_preferences()
    
    def parse_job_info(self, job_description: str) -> Dict[str, Any]:
        """
        Parse informasi dari job description secara otomatis
        
        Args:
            job_description: Teks deskripsi pekerjaan
            
        Returns:
            Dictionary berisi informasi yang diekstrak
        """
        parsed = {
            "salary_min": None,
            "salary_max": None,
            "work_type": None,
            "experience_level": None,
            "education_level": None,
            "keywords": []
        }
        
        # Extract salary information
        salary_patterns = [
            r'(?:Rp|IDR|Rp\.?)\s*(\d+(?:\.\d+)?)\s*-\s*(?:Rp|IDR|Rp\.?)\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:juta|jt|juta?)',
            r'gaji\s*(?:Rp|IDR|Rp\.?)\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:juta|jt)\s*(?:-|s\.d\.?|to)\s*(\d+(?:\.\d+)?)\s*(?:juta|jt)',
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    try:
                        parsed["salary_min"] = int(float(groups[0].replace('.', '')))
                        parsed["salary_max"] = int(float(groups[1].replace('.', '')))
                    except ValueError:
                        pass
                elif len(groups) == 1:
                    try:
                        parsed["salary_min"] = int(float(groups[0].replace('.', '')))
                        parsed["salary_max"] = parsed["salary_min"]
                    except ValueError:
                        pass
                break
        
        # Extract work type
        work_type_patterns = {
            WorkType.REMOTE: r'\b(remote|work from home|wfh|jarak jauh)\b',
            WorkType.HYBRID: r'\b(hybrid|mixed|flexible|work from anywhere)\b',
            WorkType.ONSITE: r'\b(onsite|on-site|office|kantor|full time in office)\b',
        }
        
        for wt, pattern in work_type_patterns.items():
            if re.search(pattern, job_description, re.IGNORECASE):
                parsed["work_type"] = wt.value
                break
        
        # Extract experience level
        exp_patterns = {
            ExperienceLevel.ENTRY: r'\b(entry|junior|fresh graduate|0-?\s*\d+\s*years?)\b',
            ExperienceLevel.MID: r'\b(mid|intermediate|\d+-\d+\s*years?)\b',
            ExperienceLevel.SENIOR: r'\b(senior|lead|senior\s+level)\b',
            ExperienceLevel.LEAD: r'\b(lead|manager|principal|architect|head of)\b',
        }
        
        for el, pattern in exp_patterns.items():
            if re.search(pattern, job_description, re.IGNORECASE):
                parsed["experience_level"] = el.value
                break
        
        # Extract education level
        edu_patterns = {
            EducationLevel.SMA: r'\b(SMA|SMK|MA|sederajat)\b',
            EducationLevel.D3: r'\b(D3|diploma|associate)\b',
            EducationLevel.S1: r'\b(S1|strata 1|sarjana|bachelor|undergraduate)\b',
            EducationLevel.S2: r'\b(S2|strata 2|magister|master|graduate|postgraduate)\b',
        }
        
        for el, pattern in edu_patterns.items():
            if re.search(pattern, job_description, re.IGNORECASE):
                parsed["education_level"] = el.value
                break
        
        # Extract keywords (technical terms, skills)
        skill_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|Go|Rust|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(React|Angular|Vue|Node\.js|Django|Flask|Spring|Laravel)\b',
            r'\b(Docker|Kubernetes|AWS|GCP|Azure|DevOps|CI/CD)\b',
            r'\b(SQL|NoSQL|MongoDB|PostgreSQL|MySQL|Redis)\b',
            r'\b(machine learning|AI|data science|analytics|big data)\b',
            r'\b(agile|scrum|kanban|leadership|team management)\b',
        ]
        
        keywords_found = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    keywords_found.update(match)
                else:
                    keywords_found.add(match)
        
        parsed["keywords"] = list(keywords_found)
        
        return parsed
    
    def filter_jobs(self, jobs: List[Dict[str, Any]], criteria: Optional[FilterCriteria] = None) -> List[Dict[str, Any]]:
        """
        Filter lowongan berdasarkan kriteria
        
        Args:
            jobs: List dictionary lowongan pekerjaan
            criteria: Kriteria filter. Jika None, gunakan preferensi yang disimpan
            
        Returns:
            List lowongan yang sesuai kriteria
        """
        if criteria is None:
            criteria = self.preferences
        
        if criteria is None:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            # Parse job info if description provided
            if "description" in job and job["description"]:
                parsed = self.parse_job_info(job["description"])
                # Merge parsed info into job
                for key, value in parsed.items():
                    if key not in job or job[key] is None:
                        job[key] = value
            
            if self._matches_criteria(job, criteria):
                filtered_jobs.append(job)
        
        return filtered_jobs
    
    def _matches_criteria(self, job: Dict[str, Any], criteria: FilterCriteria) -> bool:
        """Cek apakah lowongan sesuai dengan kriteria"""
        
        # Salary range check
        if criteria.salary_min is not None:
            salary = job.get("salary_min") or job.get("salary")
            if salary is not None and salary < criteria.salary_min:
                return False
        
        if criteria.salary_max is not None:
            salary = job.get("salary_max") or job.get("salary")
            if salary is not None and salary > criteria.salary_max:
                return False
        
        # Company size check
        if criteria.company_size:
            company_size = job.get("company_size")
            if company_size:
                if isinstance(company_size, str):
                    try:
                        company_size = CompanySize(company_size.lower())
                    except ValueError:
                        pass
                if company_size not in criteria.company_size:
                    return False
        
        # Work type check
        if criteria.work_type:
            work_type = job.get("work_type")
            if work_type:
                if isinstance(work_type, str):
                    try:
                        work_type = WorkType(work_type.lower())
                    except ValueError:
                        pass
                if work_type not in criteria.work_type:
                    return False
        
        # Experience level check
        if criteria.experience_level:
            exp_level = job.get("experience_level")
            if exp_level:
                if isinstance(exp_level, str):
                    try:
                        exp_level = ExperienceLevel(exp_level.lower())
                    except ValueError:
                        pass
                if exp_level not in criteria.experience_level:
                    return False
        
        # Education level check
        if criteria.education_level:
            edu_level = job.get("education_level")
            if edu_level:
                if isinstance(edu_level, str):
                    try:
                        edu_level = EducationLevel(edu_level.upper())
                    except ValueError:
                        pass
                if edu_level not in criteria.education_level:
                    return False
        
        # Industry check
        if criteria.industries:
            industry = job.get("industry")
            if industry and industry not in criteria.industries:
                return False
        
        # Keywords check
        if criteria.keywords:
            job_text = " ".join([
                str(job.get(key, "")) for key in ["title", "description", "company", "requirements"]
            ]).lower()
            
            keyword_matches = sum(
                1 for keyword in criteria.keywords 
                if keyword.lower() in job_text
            )
            
            if keyword_matches == 0:
                return False
        
        return True
    
    def rank_jobs(self, jobs: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None) -> List[Tuple[Dict[str, Any], float]]:
        """
        Beri ranking pada lowongan berdasarkan preferensi
        
        Args:
            jobs: List dictionary lowongan pekerjaan
            weights: Bobot untuk setiap kriteria. Default: {"salary": 0.3, "work_type": 0.2, 
                    "experience": 0.2, "education": 0.15, "keywords": 0.15}
            
        Returns:
            List tuple (job, score) yang sudah di-ranking
        """
        if weights is None:
            weights = {
                "salary": 0.3,
                "work_type": 0.2,
                "experience": 0.2,
                "education": 0.15,
                "keywords": 0.15
            }
        
        scored_jobs = []
        
        for job in jobs:
            score = 0.0
            
            # Parse job info if needed
            if "description" in job and job["description"]:
                parsed = self.parse_job_info(job["description"])
                for key, value in parsed.items():
                    if key not in job or job[key] is None:
                        job[key] = value
            
            # Salary score (higher is better, capped)
            if weights.get("salary", 0) > 0:
                salary = job.get("salary_max") or job.get("salary_min") or job.get("salary")
                if salary:
                    # Normalize salary (assuming max 50 juta)
                    salary_score = min(salary / 50000000, 1.0)
                    score += weights["salary"] * salary_score
            
            # Work type score (match with preferences)
            if weights.get("work_type", 0) > 0 and self.preferences and self.preferences.work_type:
                work_type = job.get("work_type")
                if work_type:
                    if isinstance(work_type, str):
                        try:
                            work_type = WorkType(work_type.lower())
                        except ValueError:
                            pass
                    if work_type in self.preferences.work_type:
                        score += weights["work_type"]
            
            # Experience level score
            if weights.get("experience", 0) > 0 and self.preferences and self.preferences.experience_level:
                exp_level = job.get("experience_level")
                if exp_level:
                    if isinstance(exp_level, str):
                        try:
                            exp_level = ExperienceLevel(exp_level.lower())
                        except ValueError:
                            pass
                    if exp_level in self.preferences.experience_level:
                        score += weights["experience"]
            
            # Education level score
            if weights.get("education", 0) > 0 and self.preferences and self.preferences.education_level:
                edu_level = job.get("education_level")
                if edu_level:
                    if isinstance(edu_level, str):
                        try:
                            edu_level = EducationLevel(edu_level.upper())
                        except ValueError:
                            pass
                    if edu_level in self.preferences.education_level:
                        score += weights["education"]
            
            # Keywords score
            if weights.get("keywords", 0) > 0 and self.preferences and self.preferences.keywords:
                job_text = " ".join([
                    str(job.get(key, "")) for key in ["title", "description", "company", "requirements"]
                ]).lower()
                
                keyword_matches = sum(
                    1 for keyword in self.preferences.keywords 
                    if keyword.lower() in job_text
                )
                
                if self.preferences.keywords:
                    keyword_score = keyword_matches / len(self.preferences.keywords)
                    score += weights["keywords"] * keyword_score
            
            scored_jobs.append((job, score))
        
        # Sort by score descending
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_jobs
    
    def get_top_matches(self, jobs: List[Dict[str, Any]], limit: int = 10, 
                       weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Get top N lowongan terbaik berdasarkan ranking
        
        Args:
            jobs: List dictionary lowongan pekerjaan
            limit: Jumlah lowongan yang dikembalikan
            weights: Bobot untuk ranking
            
        Returns:
            List top N lowongan yang sudah di-ranking
        """
        if self.preferences is None:
            return jobs[:limit]
        
        # Filter jobs first
        filtered_jobs = self.filter_jobs(jobs)
        
        # Rank filtered jobs
        ranked_jobs = self.rank_jobs(filtered_jobs, weights)
        
        # Return top N
        top_jobs = [job for job, score in ranked_jobs[:limit]]
        
        return top_jobs
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """
        Get summary of current filter preferences
        
        Returns:
            Dictionary berisi ringkasan preferensi
        """
        if self.preferences is None:
            return {"message": "No preferences set"}
        
        return {
            "salary_range": f"{self.preferences.salary_min or 'N/A'} - {self.preferences.salary_max or 'N/A'}" if (self.preferences.salary_min or self.preferences.salary_max) else "No limit",
            "company_sizes": [cs.value for cs in self.preferences.company_size] if self.preferences.company_size else "Any",
            "work_types": [wt.value for wt in self.preferences.work_type] if self.preferences.work_type else "Any",
            "experience_levels": [el.value for el in self.preferences.experience_level] if self.preferences.experience_level else "Any",
            "education_levels": [el.value for el in self.preferences.education_level] if self.preferences.education_level else "Any",
            "industries": self.preferences.industries or "Any",
            "keywords": self.preferences.keywords or "None"
        }
