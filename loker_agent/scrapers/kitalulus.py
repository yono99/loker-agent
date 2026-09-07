from __future__ import annotations

import json
import urllib.parse
from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class KitaLulusScraper(BaseScraper):
    """ KitaLulus jobs via their public API.
    
    KitaLulus is an Indonesian job platform focused on fresh graduates and entry-level positions.
    Their public API returns JSON data suitable for programmatic access.
    
    API Endpoint: https://api.kitalulus.com/api/v1/jobs
    """
    
    platform = "kitalulus"
    BASE = "https://api.kitalulus.com/api/v1"
    
    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Origin": "https://www.kitalulus.com",
            "Referer": "https://www.kitalulus.com/"
        })
    
    def search(self, keyword: str, location: str) -> List[Job]:
        """ KitaLulus jobs.
        
        Args:
            keyword: Job title or keyword to search
            location: City or region (will be mapped to Indonesia provinces/cities)
        
        Returns:
            List of Job objects
        """
        # KitaLulus API expects location as city ID or name
        # We'll pass the location string and let the API handle it
        params = {
            "q": keyword,
            "location": location,
            "limit": self.max_results,
            "offset": 0,
            "sort_by": "recent",
            "status": "active"
        }
        
        url = f"{self.BASE}/jobs?{urllib.parse.urlencode(params)}"
        
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"KitaLulus search failed: HTTP {resp.status_code} {resp.text[:300]}")
            
            data = resp.json()
            jobs_data = data.get("data", [])
            
            if not jobs_data:
                # Try alternative API structure
                jobs_data = data.get("jobs", [])
            
            jobs: List[Job] = []
            for item in jobs_data:
                jid = str(item.get("id") or item.get("job_id") or "")
                if not jid:
                    continue
                
                # Extract company info
                company = item.get("company", {})
                company_name = company.get("name", "") if isinstance(company, dict) else str(company)
                
                # Extract location
                loc_data = item.get("location", {})
                loc_parts = []
                if isinstance(loc_data, dict):
                    city = loc_data.get("city", "")
                    province = loc_data.get("province", "")
                    if city:
                        loc_parts.append(city)
                    if province:
                        loc_parts.append(province)
                else:
                    loc_parts.append(str(loc_data))
                loc_str = ", ".join(loc_parts) if loc_parts else location
                
                # Build URL
                job_slug = item.get("slug") or item.get("title", "").lower().replace(" ", "-")
                job_url = f"https://www.kitalulus.com/jobs/{jid}-{job_slug}"
                
                # Employment type
                emp_type = item.get("employment_type", "")
                if not emp_type:
                    emp_type = item.get("job_type", "")
                
                # Description
                desc = item.get("description", "")
                if isinstance(desc, dict):
                    desc = desc.get("text", "") or desc.get("content", "")
                desc = str(desc)[:4000]
                
                # Salary
                salary = item.get("salary", "")
                if isinstance(salary, dict):
                    min_sal = salary.get("min", "")
                    max_sal = salary.get("max", "")
                    currency = salary.get("currency", "IDR")
                    if min_sal and max_sal:
                        salary = f"{currency} {min_sal} - {max_sal}"
                    elif min_sal:
                        salary = f"{currency} {min_sal}+"
                    else:
                        salary = ""
                elif salary:
                    salary = str(salary)
                
                jobs.append(
                    Job(
                        platform=self.platform,
                        job_id=jid,
                        title=item.get("title", ""),
                        company=company_name,
                        location=loc_str,
                        salary=salary,
                        url=job_url,
                        description=desc,
                        employment_type=emp_type,
                        published=str(item.get("published_at") or item.get("created_at") or ""),
                        raw=item
                    )
                )
                
                if len(jobs) >= self.max_results:
                    break
            
            return jobs
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"KitaLulus API returned invalid JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"KitaLulus search failed: {e}")
