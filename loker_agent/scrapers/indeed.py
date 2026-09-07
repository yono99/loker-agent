from __future__ import annotations

import json
import urllib.parse
from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class IndeedScraper(BaseScraper):
    """ Indeed jobs via their public API and RSS feeds.
    
    Indeed offers several access methods:
    1. Official API (requires publisher account)
    2. RSS feeds (public, no authentication)
    3. Public search endpoint
    
    This scraper uses the RSS feed method which requires no authentication and
    provides reliable job listings. For higher volume, consider the Publisher API.
    
    RSS Feed: https://www.indeed.com/rss?q=keyword&l=location
    """
    
    platform = "indeed"
    RSS_BASE = "https://www.indeed.com/rss"
    
    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/rss+xml, application/xml, application/json",
            "Accept-Language": "en-US,en;q=0.9"
        })
    
    def search(self, keyword: str, location: str) -> List[Job]:
        """ Indeed jobs using RSS feeds.
        
        Args:
            keyword: Job title or keyword
            location: City, state, or country
        
        Returns:
            List of Job objects
        """
        # Build RSS query
        params = {
            "q": keyword,
            "l": location,
            "limit": min(self.max_results, 50)  # RSS limit
        }
        
        rss_url = f"{self.RSS_BASE}?{urllib.parse.urlencode(params)}"
        
        try:
            resp = self.session.get(rss_url, timeout=30)
            if resp.status_code != 200:
                # Try fallback: search endpoint
                return self.__api(keyword, location)
            
            # Parse RSS XML
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(resp.text)
            # RSS namespace
            ns = {'': 'http://purl.org/rss/1.0/'}
            
            jobs: List[Job] = []
            items = root.findall('.//item')
            
            for item in items[:self.max_results]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                # Parse title format: "Job Title - Company Name"
                title_parts = title.split(' - ')
                job_title = title_parts[0] if title_parts else title
                company_name = title_parts[1] if len(title_parts) > 1 else ""
                
                # Extract job ID from link
                job_id = self._extract_job_id(link)
                if not job_id:
                    continue
                
                # Extract location from description or link
                loc = self._extract_location(description, location)
                
                # Clean description
                desc_clean = self._clean_html(description)[:4000]
                
                jobs.append(
                    Job(
                        platform=self.platform,
                        job_id=job_id,
                        title=job_title,
                        company=company_name,
                        location=loc,
                        salary="",  # RSS doesn't provide salary
                        url=link,
                        description=desc_clean,
                        employment_type="",
                        published=pub_date,
                        raw={"rss_item": self._element_to_dict(item)}
                    )
                )
                
                if len(jobs) >= self.max_results:
                    break
            
            return jobs
            
        except ET.ParseError:
            # RSS parsing failed, try API
            return self.__api(keyword, location)
        except Exception as e:
            raise RuntimeError(f"Indeed search failed: {e}")
    
    def __api(self, keyword: str, location: str) -> List[Job]:
        """Fallback: search using Indeed's unofficial JSON API.
        
        Note: This endpoint is not officially documented and may change.
        """
        params = {
            "q": keyword,
            "l": location,
            "start": 0,
            "limit": min(self.max_results, 50)
        }
        
        url = f"https://indeed.com/jobs/api/v1/search?{urllib.parse.urlencode(params)}"
        
        resp = self.session.get(url, timeout=30)
        if resp.status_code != 200:
            # Final fallback: use indeed.com/jobs endpoint
            return self.__html(keyword, location)
        
        data = resp.json()
        jobs_data = data.get("jobs", [])
        
        jobs: List[Job] = []
        for item in jobs_data[:self.max_results]:
            jid = str(item.get("id", ""))
            if not jid:
                continue
            
            job = Job(
                platform=self.platform,
                job_id=jid,
                title=item.get("title", ""),
                company=item.get("company", {}).get("name", ""),
                location=item.get("location", ""),
                salary=item.get("salary", ""),
                url=item.get("url", f"https://www.indeed.com/viewjob?jk={jid}"),
                description=item.get("description", "")[:4000],
                employment_type=item.get("employment_type", ""),
                published=str(item.get("posted_at", "")),
                raw=item
            )
            jobs.append(job)
        
        return jobs
    
    def __html(self, keyword: str, location: str) -> List[Job]:
        """Last resort: attempt HTML parsing.
        
        This is unreliable and should only be used if other methods fail.
        """
        params = {
            "q": keyword,
            "l": location,
            "limit": min(self.max_results, 30)
        }
        
        url = f"https://www.indeed.com/jobs?{urllib.parse.urlencode(params)}"
        
        resp = self.session.get(url, timeout=30, headers={
            **self.session.headers,
            "Accept": "text/html,application/xhtml+xml"
        })
        
        if resp.status_code != 200:
            raise RuntimeError(f"Indeed HTML search failed: HTTP {resp.status_code}")
        
        # Simple HTML parsing
        import re
        html = resp.text
        
        # Extract job cards (simplified)
        job_pattern = r'id="job_([^"]+)"'
        job_ids = re.findall(job_pattern, html)[:self.max_results]
        
        jobs: List[Job] = []
        for jid in job_ids:
            # Extract details from job card (simplified)
            pattern = f'id="job_{jid}".*?<a[^>]*>(.*?)</a>'
            title_match = re.search(pattern, html, re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Unknown"
            
            # Company
            company_pattern = f'id="job_{jid}".*?class="companyName".*?>(.*?)</span>'
            company_match = re.search(company_pattern, html, re.DOTALL)
            company = company_match.group(1).strip() if company_match else ""
            
            jobs.append(
                Job(
                    platform=self.platform,
                    job_id=jid,
                    title=title,
                    company=company,
                    location=location,
                    salary="",
                    url=f"https://www.indeed.com/viewjob?jk={jid}",
                    description="",
                    employment_type="",
                    published="",
                    raw={"html_fallback": True}
                )
            )
        
        return jobs
    
    @staticmethod
    def _extract_job_id(link: str) -> str:
        """Extract job ID from Indeed link."""
        import re
        match = re.search(r'jk=([^&]+)', link)
        if match:
            return match.group(1)
        
        match = re.search(r'/viewjob\?jk=([^&]+)', link)
        if match:
            return match.group(1)
        
        match = re.search(r'/(\d+)/', link)
        if match:
            return match.group(1)
        
        return link.split('/')[-1].split('?')[0]
    
    @staticmethod
    def _extract_location(description: str, default: str) -> str:
        """Extract location from description text."""
        import re
        
        # Look for location patterns in description
        loc_patterns = [
            r'Location:\s*([^\n]+)',
            r'Lokasi:\s*([^\n]+)',
            r'Job Location:\s*([^\n]+)',
            r'at\s+([A-Z][a-z]+,\s*[A-Z]{2})'
        ]
        
        for pattern in loc_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return default
    
    @staticmethod
    def _clean_html(text: str) -> str:
        """Remove HTML tags from text."""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', ' ', text)
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', clean)
        # Remove CDATA
        clean = clean.replace('<![CDATA[', '').replace(']]>', '')
        return clean.strip()
    
    @staticmethod
    def _element_to_dict(element) -> Dict:
        """Convert XML element to dict."""
        result = {}
        for child in element:
            if child.text:
                result[child.tag] = child.text
            else:
                result[child.tag] = 'sub_elements'
        return result
