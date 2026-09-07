from __future__ import annotations

import json
import urllib.parse
from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class KarirhubScraper(BaseScraper):
    """ Karirhub Kemnaker jobs via their official API.
    
    Karirhub is the official job portal from the Indonesian Ministry of Manpower.
    It integrates with the SISNAKER (Sistem Informasi Ketenagakerjaan) system.
    
    API Endpoints:
    - https://karirhub.kemnaker.go.id/api/v1/jobs
    - https://karirhub.kemnaker.go.id/api/v1/loker
    
    This is a government API that may require specific headers or tokens.
    """
    
    platform = "karirhub"
    BASE = "https://karirhub.kemnaker.go.id/api/v1"
    
    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Origin": "https://karirhub.kemnaker.go.id",
            "Referer": "https://karirhub.kemnaker.go.id/"
        })
        
        # Get token from config if available
        self.token = None
        creds = config._data.get("credentials", {}).get("karirhub", {})
        if creds:
            self.token = creds.get("token", "")
            if self.token:
                self.session.headers["Authorization"] = f"Bearer {self.token}"
    
    def search(self, keyword: str, location: str) -> List[Job]:
        """ Karirhub jobs.
        
        Args:
            keyword: Job title or keyword (will map to "kata_kunci" parameter)
            location: City or region (will map to "lokasi" parameter)
        
        Returns:
            List of Job objects
        """
        # Karirhub API uses different parameter names
        params = {
            "kata_kunci": keyword,
            "lokasi": location,
            "limit": min(self.max_results, 50),
            "offset": 0,
            "sort": "terbaru"
        }
        
        # Try multiple possible endpoints
        endpoints = [
            f"{self.BASE}/loker?{urllib.parse.urlencode(params)}",
            f"{self.BASE}/jobs?{urllib.parse.urlencode(params)}",
            f"{self.BASE}/lowongan?{urllib.parse.urlencode(params)}"
        ]
        
        for endpoint in endpoints:
            try:
                resp = self.session.get(endpoint, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs_data = self._extract_jobs(data)
                    if jobs_data:
                        return self._parse_jobs(jobs_data, location)
            except Exception:
                continue
        
        # If all endpoints fail, try fallback HTML scraping
        return self.__html(keyword, location)
    
    def _extract_jobs(self, data: Dict) -> List[Dict]:
        """Extract job listings from various API response formats."""
        # Try different possible response structures
        if isinstance(data, dict):
            # Common structure: {"data": [...], "status": "success"}
            if "data" in data and isinstance(data["data"], list):
                return data["data"]
            
            # Structure: {"jobs": [...]}
            if "jobs" in data and isinstance(data["jobs"], list):
                return data["jobs"]
            
            # Structure: {"result": {"data": [...]}}
            if "result" in data and isinstance(data["result"], dict):
                result = data["result"]
                if "data" in result and isinstance(result["data"], list):
                    return result["data"]
            
            # Structure: {"loker": [...]}
            if "loker" in data and isinstance(data["loker"], list):
                return data["loker"]
            
            # Structure: {"items": [...]}
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
        
        return []
    
    def _parse_jobs(self, jobs_data: List[Dict], location: str) -> List[Job]:
        """Parse job listings into Job objects."""
        jobs: List[Job] = []
        
        for item in jobs_data[:self.max_results]:
            jid = str(item.get("id") or item.get("loker_id") or item.get("job_id") or "")
            if not jid:
                continue
            
            # Extract company info
            company = item.get("company", {})
            if isinstance(company, dict):
                company_name = company.get("name") or company.get("nama") or company.get("perusahaan") or ""
            else:
                company_name = str(company) if company else item.get("perusahaan", "")
            
            # Extract location
            loc = item.get("lokasi") or item.get("location") or item.get("kota") or item.get("city") or location
            if isinstance(loc, dict):
                parts = [
                    loc.get("kota") or loc.get("city") or "",
                    loc.get("provinsi") or loc.get("province") or ""
                ]
                loc = ", ".join(p for p in parts if p)
            
            # Extract salary
            min_sal = item.get("gaji_min") or item.get("salary_min") or item.get("min_salary")
            max_sal = item.get("gaji_max") or item.get("salary_max") or item.get("max_salary")
            salary_str = ""
            if min_sal and max_sal:
                salary_str = f"IDR {min_sal} - {max_sal}"
            elif min_sal:
                salary_str = f"IDR {min_sal}+"
            
            # Build URL
            job_slug = item.get("slug") or str(jid)
            job_url = f"https://karirhub.kemnaker.go.id/loker/{job_slug}"
            
            # Employment type
            emp_type = item.get("tipe_pekerjaan") or item.get("employment_type") or item.get("jenis_pekerjaan") or ""
            
            # Description
            desc = item.get("deskripsi") or item.get("description") or item.get("detail") or ""
            if isinstance(desc, dict):
                desc = desc.get("text") or desc.get("content") or ""
            desc = str(desc)[:4000]
            
            jobs.append(
                Job(
                    platform=self.platform,
                    job_id=jid,
                    title=item.get("judul") or item.get("title") or item.get("posisi") or "",
                    company=company_name,
                    location=str(loc),
                    salary=salary_str,
                    url=job_url,
                    description=desc,
                    employment_type=emp_type,
                    published=str(item.get("tanggal_publikasi") or item.get("published_at") or item.get("created_at") or ""),
                    raw=item
                )
            )
            
            if len(jobs) >= self.max_results:
                break
        
        return jobs
    
    def __html(self, keyword: str, location: str) -> List[Job]:
        """Fallback: HTML scraping from the Karirhub website.
        
        This is a fallback when the API is not available.
        """
        params = {
            "q": keyword,
            "lokasi": location
        }
        
        url = f"https://karirhub.kemnaker.go.id/cari?{urllib.parse.urlencode(params)}"
        
        try:
            resp = self.session.get(url, timeout=30, headers={
                **self.session.headers,
                "Accept": "text/html,application/xhtml+xml"
            })
            
            if resp.status_code != 200:
                raise RuntimeError(f"Karirhub HTML search failed: HTTP {resp.status_code}")
            
            import re
            from html.parser import HTMLParser
            
            html = resp.text
            jobs: List[Job] = []
            
            # Simple extraction of job listings from HTML
            # Look for job cards with class names
            job_patterns = [
                r'<div[^>]*class="[^"]*job-item[^"]*"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<div[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*loker-item[^"]*"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>.*?<div[^>]*class="[^"]*perusahaan[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*card[^"]*job[^"]*"[^>]*>.*?<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>.*?<div[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</div>'
            ]
            
            for pattern in job_patterns:
                matches = re.findall(pattern, html, re.DOTALL)
                for match in matches[:self.max_results]:
                    title = re.sub(r'<[^>]+>', '', match[0]).strip()
                    company = re.sub(r'<[^>]+>', '', match[1]).strip() if len(match) > 1 else ""
                    
                    # Generate a unique ID from the title
                    import hashlib
                    jid = hashlib.md5(f"{title}{company}{location}".encode()).hexdigest()[:20]
                    
                    jobs.append(
                        Job(
                            platform=self.platform,
                            job_id=jid,
                            title=title,
                            company=company,
                            location=location,
                            salary="",
                            url=url,
                            description="",
                            employment_type="",
                            published="",
                            raw={"html_fallback": True}
                        )
                    )
                
                if jobs:
                    break
            
            return jobs
            
        except Exception as e:
            raise RuntimeError(f"Karirhub fallback search failed: {e}")
