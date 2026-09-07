from __future__ import annotations

import json
import urllib.parse
from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class DeallsScraper(BaseScraper):
    """ Dealls jobs via their public API.
    
    Dealls is an Indonesian career platform offering job search and career guidance.
    They have a public GraphQL API at https://api.dealls.com/graphql.
    
    API Reference: https://docs.dealls.com/api
    """
    
    platform = "dealls"
    BASE = "https://api.dealls.com"
    GRAPHQL_ENDPOINT = "https://api.dealls.com/graphql"
    
    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Origin": "https://www.dealls.com",
            "Referer": "https://www.dealls.com/"
        })
    
    def _get_auth_token(self) -> Optional[str]:
        """Get authentication token from config if available."""
        return getattr(self.config, 'dealls_token', None) or self.config._data.get("credentials", {}).get("dealls", {}).get("token", "")
    
    def search(self, keyword: str, location: str) -> List[Job]:
        """ Dealls jobs using GraphQL API.
        
        Args:
            keyword: Job title or keyword to search
            location: City or region
        
        Returns:
            List of Job objects
        """
        # GraphQL query for job search
        query = """
        query Job($input: JobInput!) {
            job(input: $input) {
                totalCount
                nodes {
                    id
                    title
                    slug
                    description
                    employmentType
                    salaryMin
                    salaryMax
                    currency
                    company {
                        name
                        slug
                        logo
                    }
                    location {
                        city
                        province
                        country
                    }
                    postedAt
                    url
                }
            }
        }
        """
        
        variables = {
            "input": {
                "keyword": keyword,
                "location": location,
                "limit": self.max_results,
                "offset": 0,
                "sortBy": "recent",
                "status": "active"
            }
        }
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        # Try with auth token if available
        token = self._get_auth_token()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        
        try:
            resp = self.session.post(self.GRAPHQL_ENDPOINT, json=payload, timeout=30)
            if resp.status_code != 200:
                # Fallback: try REST API endpoint
                return self.__rest(keyword, location)
            
            data = resp.json()
            if "errors" in data:
                # GraphQL had errors, fallback to REST
                return self.__rest(keyword, location)
            
            result = data.get("data", {}).get("job", {})
            nodes = result.get("nodes", [])
            
            jobs: List[Job] = []
            for item in nodes:
                jid = str(item.get("id", ""))
                if not jid:
                    continue
                
                company = item.get("company", {})
                company_name = company.get("name", "") if isinstance(company, dict) else str(company)
                
                location_data = item.get("location", {})
                loc_parts = []
                if isinstance(location_data, dict):
                    city = location_data.get("city", "")
                    province = location_data.get("province", "")
                    country = location_data.get("country", "")
                    if city:
                        loc_parts.append(city)
                    if province:
                        loc_parts.append(province)
                    if country:
                        loc_parts.append(country)
                loc_str = ", ".join(loc_parts) if loc_parts else location
                
                # Build salary string
                min_sal = item.get("salaryMin")
                max_sal = item.get("salaryMax")
                currency = item.get("currency", "IDR")
                salary_str = ""
                if min_sal and max_sal:
                    salary_str = f"{currency} {min_sal} - {max_sal}"
                elif min_sal:
                    salary_str = f"{currency} {min_sal}+"
                
                job_slug = item.get("slug") or item.get("title", "").lower().replace(" ", "-")
                job_url = item.get("url") or f"https://www.dealls.com/jobs/{job_slug}"
                
                jobs.append(
                    Job(
                        platform=self.platform,
                        job_id=jid,
                        title=item.get("title", ""),
                        company=company_name,
                        location=loc_str,
                        salary=salary_str,
                        url=job_url,
                        description=item.get("description", "")[:4000],
                        employment_type=item.get("employmentType", ""),
                        published=str(item.get("postedAt", "")),
                        raw=item
                    )
                )
                
                if len(jobs) >= self.max_results:
                    break
            
            return jobs
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Dealls API returned invalid JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Dealls search failed: {e}")
    
    def __rest(self, keyword: str, location: str) -> List[Job]:
        """Fallback REST API search method.
        
        Some Dealls endpoints use REST instead of GraphQL.
        """
        params = {
            "q": keyword,
            "location": location,
            "limit": self.max_results,
            "offset": 0,
            "sort": "recent"
        }
        
        url = f"{self.BASE}/api/v1/jobs?{urllib.parse.urlencode(params)}"
        
        resp = self.session.get(url, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Dealls REST search failed: HTTP {resp.status_code} {resp.text[:300]}")
        
        data = resp.json()
        jobs_data = data.get("data", [])
        
        jobs: List[Job] = []
        for item in jobs_data:
            jid = str(item.get("id", ""))
            if not jid:
                continue
            
            company = item.get("company", {})
            company_name = company.get("name", "") if isinstance(company, dict) else str(company)
            
            # Build location
            loc_parts = []
            for key in ["city", "province", "country"]:
                if item.get(key):
                    loc_parts.append(str(item[key]))
            loc_str = ", ".join(loc_parts) if loc_parts else location
            
            jobs.append(
                Job(
                    platform=self.platform,
                    job_id=jid,
                    title=item.get("title", ""),
                    company=company_name,
                    location=loc_str,
                    salary=item.get("salary", ""),
                    url=item.get("url", f"https://www.dealls.com/jobs/{item.get('slug', '')}"),
                    description=item.get("description", "")[:4000],
                    employment_type=item.get("employment_type", ""),
                    published=str(item.get("posted_at", "")),
                    raw=item
                )
            )
            
            if len(jobs) >= self.max_results:
                break
        
        return jobs
