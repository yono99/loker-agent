from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class LinkedInScraper(BaseScraper):
    """ LinkedIn jobs via the official LinkedIn API (OAuth 2.0).
    
    Requires OAuth 2.0 credentials from LinkedIn Developer Portal.
    Set up:
    1. Create app at https://www.linkedin.com/developers/
    2. Get Client ID and Client Secret
    3. Set redirect URI to http://localhost:8000/callback
    4. Add credentials to config.json under credentials.linkedin
    
    API Reference: https://learn.microsoft.com/en-us/linkedin/shared/references/
    """
    
    platform = "linkedin"
    BASE = "https://api.linkedin.com/v2"
    AUTH_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    
    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[int] = None
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with OAuth token."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "x-li-format": "json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def _ensure_auth(self) -> None:
        """Ensure valid OAuth token."""
        if self.access_token and self.token_expiry and self.token_expiry > int(time.time()) + 60:
            return
        self._refresh_token()
    
    def _refresh_token(self) -> None:
        """Exchange refresh token for access token."""
        client_id = self.config.linkedin_client_id
        client_secret = self.config.linkedin_client_secret
        refresh_token = self.config.linkedin_refresh_token
        
        if not all([client_id, client_secret, refresh_token]):
            raise RuntimeError(
                "LinkedIn OAuth credentials required. "
                "Set linkedin_client_id, linkedin_client_secret, and linkedin_refresh_token in config."
            )
        
        auth_str = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        resp = self.session.post(
            self.AUTH_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            },
            headers={
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        if resp.status_code != 200:
            raise RuntimeError(f"LinkedIn token refresh failed: HTTP {resp.status_code} {resp.text[:300]}")
        
        data = resp.json()
        self.access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        self.token_expiry = int(time.time()) + expires_in
    
    def search(self, keyword: str, location: str) -> List[Job]:
        """ LinkedIn jobs using the Jobs API."""
        self._ensure_auth()
        
        # LinkedIn API uses place ID for location
        # For simplicity, we'll use the location string directly and let the API resolve it
        params = {
            "q": "job",
            "count": min(self.max_results, 50),  # LinkedIn max is 50 per page
            "start": 0,
            "title": keyword,
            "location": location,
            "sort": "R",  # Recent
            "jobActive": "true"
        }
        
        url = f"{self.BASE}/jobs?{urllib.parse.urlencode(params)}"
        resp = self.session.get(url, headers=self._get_auth_headers())
        
        if resp.status_code != 200:
            raise RuntimeError(f"LinkedIn search failed: HTTP {resp.status_code} {resp.text[:300]}")
        
        data = resp.json()
        elements = data.get("elements", [])
        
        jobs: List[Job] = []
        for item in elements:
            jid = str(item.get("id", ""))
            if not jid:
                continue
                
            # Extract company info
            company_data = item.get("companyDetails", {})
            company_name = ""
            if company_data:
                company_name = company_data.get("company", {}).get("localizedName", "")
            
            # Extract location
            location_data = item.get("primaryLocation", {})
            loc_parts = []
            if isinstance(location_data, dict):
                country = location_data.get("country", {}).get("code", "")
                city = location_data.get("city", {}).get("localizedName", "")
                if city:
                    loc_parts.append(city)
                if country:
                    loc_parts.append(country)
            loc_str = ", ".join(loc_parts) if loc_parts else location
            
            # Extract salary
            salary_data = item.get("salary", {})
            salary_str = ""
            if salary_data:
                sal = salary_data.get("salaryRange", {})
                currency = salary_data.get("currency", "")
                min_val = sal.get("min", {}).get("value", "")
                max_val = sal.get("max", {}).get("value", "")
                if min_val and max_val:
                    salary_str = f"{currency} {min_val} - {max_val}"
                elif min_val:
                    salary_str = f"{currency} {min_val}+"
            
            # Build URL
            job_url = f"https://www.linkedin.com/jobs/view/{jid}/"
            
            jobs.append(
                Job(
                    platform=self.platform,
                    job_id=jid,
                    title=item.get("title", {}).get("localizedName", ""),
                    company=company_name,
                    location=loc_str,
                    salary=salary_str,
                    url=job_url,
                    description=item.get("description", {}).get("localizedText", "")[:4000],
                    employment_type=item.get("employmentType", ""),
                    published=str(item.get("listedAt", "")),
                    raw=item
                )
            )
            
            if len(jobs) >= self.max_results:
                break
        
        return jobs
