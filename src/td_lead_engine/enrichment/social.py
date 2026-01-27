"""Social media profile enrichment."""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class SocialProfile:
    """Enriched social media profile data."""

    # Platform info
    platform: str  # instagram, facebook, linkedin, twitter
    username: str
    profile_url: str = ""

    # Basic info
    full_name: str = ""
    bio: str = ""
    location: str = ""
    website: str = ""

    # Metrics
    followers: int = 0
    following: int = 0
    posts: int = 0
    engagement_rate: float = 0.0

    # Inferred data
    is_business_account: bool = False
    industry: str = ""
    company: str = ""
    job_title: str = ""

    # Real estate signals
    real_estate_interest_score: int = 0
    detected_signals: List[str] = field(default_factory=list)

    # Contact
    email: str = ""
    phone: str = ""

    # Activity
    last_post_date: Optional[datetime] = None
    posting_frequency: str = ""  # "daily", "weekly", "monthly", "inactive"

    # Metadata
    enriched_at: datetime = field(default_factory=datetime.now)
    data_source: str = ""


class SocialEnrichment:
    """Enrich lead data from social media profiles."""

    def __init__(self):
        """Initialize social enrichment."""
        # API keys for various services
        self.clearbit_api_key = os.environ.get("CLEARBIT_API_KEY")
        self.hunter_api_key = os.environ.get("HUNTER_API_KEY")
        self.peopledatalabs_key = os.environ.get("PEOPLEDATALABS_API_KEY")

        # Real estate interest signals
        self.interest_signals = {
            "buyer": [
                "house hunting", "looking for a home", "home search",
                "need a realtor", "first time buyer", "relocating to",
                "moving to columbus", "moving to ohio", "apartment hunting",
                "preapproved", "pre-approved", "mortgage approved",
                "looking for homes", "searching for houses"
            ],
            "seller": [
                "selling our home", "listing our house", "moving out",
                "downsizing", "upgrading homes", "need to sell",
                "relocating from", "leaving columbus", "selling soon"
            ],
            "investor": [
                "real estate investor", "rental property", "investment property",
                "passive income", "cash flow", "fix and flip", "wholesale",
                "brrrr", "multifamily", "landlord"
            ],
            "industry": [
                "realtor", "real estate agent", "mortgage", "lender",
                "title company", "home inspector", "appraiser",
                "real estate broker", "realty"
            ],
            "life_events": [
                "just married", "newlywed", "expecting", "pregnant",
                "new job", "promotion", "retiring", "retired",
                "empty nester", "divorce", "engaged"
            ],
            "local": [
                "columbus ohio", "central ohio", "614", "cbus",
                "dublin ohio", "powell ohio", "westerville", "osu",
                "ohio state", "buckeye"
            ]
        }

    def enrich_by_email(self, email: str) -> Optional[SocialProfile]:
        """Enrich profile data using email address."""
        profile = SocialProfile(platform="email", username=email)

        # Try Clearbit if available
        if self.clearbit_api_key:
            clearbit_data = self._fetch_clearbit(email)
            if clearbit_data:
                profile = self._merge_clearbit_data(profile, clearbit_data)

        # Try Hunter.io for company info
        if self.hunter_api_key:
            hunter_data = self._fetch_hunter(email)
            if hunter_data:
                profile = self._merge_hunter_data(profile, hunter_data)

        # Extract domain-based info
        domain_info = self._analyze_email_domain(email)
        if domain_info:
            if not profile.company:
                profile.company = domain_info.get("company", "")
            if not profile.industry:
                profile.industry = domain_info.get("industry", "")

        return profile if profile.full_name or profile.company else None

    def enrich_instagram(self, username: str, bio: str = "", followers: int = 0) -> SocialProfile:
        """Enrich Instagram profile with available data."""
        profile = SocialProfile(
            platform="instagram",
            username=username,
            profile_url=f"https://instagram.com/{username}",
            bio=bio,
            followers=followers
        )

        # Analyze bio for signals
        if bio:
            signals = self._detect_signals(bio)
            profile.detected_signals = signals["all_signals"]
            profile.real_estate_interest_score = signals["score"]

            # Extract location from bio
            location = self._extract_location(bio)
            if location:
                profile.location = location

            # Check if business account indicators
            if any(word in bio.lower() for word in ["dm for", "book now", "link in bio", "shop now", "@"]):
                profile.is_business_account = True

            # Extract job/company from bio
            job_info = self._extract_job_info(bio)
            if job_info:
                profile.job_title = job_info.get("title", "")
                profile.company = job_info.get("company", "")

        # Engagement estimation based on followers
        if followers > 0:
            if followers < 1000:
                profile.engagement_rate = 8.0  # High engagement typical for small accounts
            elif followers < 10000:
                profile.engagement_rate = 4.0
            elif followers < 100000:
                profile.engagement_rate = 2.0
            else:
                profile.engagement_rate = 1.0

        return profile

    def enrich_facebook(self, profile_url: str = "", name: str = "", about: str = "") -> SocialProfile:
        """Enrich Facebook profile with available data."""
        profile = SocialProfile(
            platform="facebook",
            username=name,
            profile_url=profile_url,
            full_name=name,
            bio=about
        )

        if about:
            signals = self._detect_signals(about)
            profile.detected_signals = signals["all_signals"]
            profile.real_estate_interest_score = signals["score"]

            location = self._extract_location(about)
            if location:
                profile.location = location

        return profile

    def enrich_linkedin(self, profile_url: str = "", name: str = "",
                       headline: str = "", company: str = "") -> SocialProfile:
        """Enrich LinkedIn profile with available data."""
        profile = SocialProfile(
            platform="linkedin",
            username=name,
            profile_url=profile_url,
            full_name=name,
            job_title=headline,
            company=company
        )

        # LinkedIn headline often contains job title
        if headline:
            signals = self._detect_signals(headline)
            profile.detected_signals = signals["all_signals"]
            profile.real_estate_interest_score = signals["score"]

            # Check for industry signals
            if any(word in headline.lower() for word in self.interest_signals["industry"]):
                profile.industry = "real_estate"

        return profile

    def _detect_signals(self, text: str) -> Dict[str, Any]:
        """Detect real estate interest signals in text."""
        text_lower = text.lower()
        score = 0
        all_signals = []
        categories = {}

        for category, signals in self.interest_signals.items():
            category_matches = []
            for signal in signals:
                if signal in text_lower:
                    category_matches.append(signal)
                    all_signals.append(signal)

                    # Score by category
                    if category == "buyer":
                        score += 15
                    elif category == "seller":
                        score += 15
                    elif category == "investor":
                        score += 10
                    elif category == "life_events":
                        score += 8
                    elif category == "local":
                        score += 5
                    elif category == "industry":
                        score -= 10  # Likely competitor

            if category_matches:
                categories[category] = category_matches

        return {
            "score": min(score, 100),
            "all_signals": all_signals,
            "by_category": categories,
            "is_competitor": "industry" in categories and len(categories) == 1
        }

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        # Common patterns
        patterns = [
            r"(?:based in|located in|living in|from)\s+([A-Za-z\s]+,?\s*(?:OH|Ohio)?)",
            r"([A-Za-z]+)\s*,\s*(?:OH|Ohio)",
            r"(Columbus|Dublin|Powell|Westerville|New Albany|Upper Arlington|Grandview|Hilliard|Grove City|Gahanna|Worthington|Bexley|Pickerington)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_job_info(self, text: str) -> Optional[Dict[str, str]]:
        """Extract job title and company from text."""
        # Common bio patterns
        patterns = [
            r"(?:^|\|)\s*([^|@]+?)\s+(?:at|@)\s+([^|]+?)(?:\s*\||$)",
            r"([A-Za-z\s]+)\s*@\s*([A-Za-z\s&]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    "title": match.group(1).strip(),
                    "company": match.group(2).strip()
                }

        return None

    def _analyze_email_domain(self, email: str) -> Optional[Dict[str, str]]:
        """Analyze email domain for company info."""
        try:
            domain = email.split("@")[1].lower()

            # Skip personal email domains
            personal_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                              "icloud.com", "aol.com", "protonmail.com", "me.com"]
            if domain in personal_domains:
                return None

            # Known tech companies
            tech_companies = {
                "google.com": {"company": "Google", "industry": "Technology"},
                "amazon.com": {"company": "Amazon", "industry": "Technology"},
                "microsoft.com": {"company": "Microsoft", "industry": "Technology"},
                "apple.com": {"company": "Apple", "industry": "Technology"},
                "meta.com": {"company": "Meta", "industry": "Technology"},
                "facebook.com": {"company": "Meta", "industry": "Technology"},
                "salesforce.com": {"company": "Salesforce", "industry": "Technology"},
                "jpmorgan.com": {"company": "JPMorgan Chase", "industry": "Finance"},
                "chase.com": {"company": "JPMorgan Chase", "industry": "Finance"},
                "nationwide.com": {"company": "Nationwide", "industry": "Insurance"},
            }

            if domain in tech_companies:
                return tech_companies[domain]

            # Ohio specific
            if "osu.edu" in domain or "ohio-state.edu" in domain:
                return {"company": "Ohio State University", "industry": "Education"}
            if ".edu" in domain:
                return {"company": domain.split(".")[0].title(), "industry": "Education"}

            # Extract company name from domain
            company_name = domain.split(".")[0].replace("-", " ").title()
            return {"company": company_name, "industry": "Unknown"}

        except Exception:
            return None

    def _fetch_clearbit(self, email: str) -> Optional[Dict]:
        """Fetch data from Clearbit Enrichment API."""
        try:
            url = f"https://person.clearbit.com/v2/people/find?email={email}"
            headers = {"Authorization": f"Bearer {self.clearbit_api_key}"}

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Clearbit error: {e}")

        return None

    def _fetch_hunter(self, email: str) -> Optional[Dict]:
        """Fetch data from Hunter.io API."""
        try:
            url = f"https://api.hunter.io/v2/email-verifier"
            params = {"email": email, "api_key": self.hunter_api_key}

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Hunter.io error: {e}")

        return None

    def _merge_clearbit_data(self, profile: SocialProfile, data: Dict) -> SocialProfile:
        """Merge Clearbit data into profile."""
        try:
            profile.full_name = data.get("name", {}).get("fullName", "")
            profile.location = data.get("location", "")
            profile.job_title = data.get("employment", {}).get("title", "")
            profile.company = data.get("employment", {}).get("name", "")

            # Social profiles
            if data.get("linkedin", {}).get("handle"):
                profile.profile_url = f"https://linkedin.com/in/{data['linkedin']['handle']}"

            profile.data_source = "clearbit"
        except Exception as e:
            logger.error(f"Error merging Clearbit data: {e}")

        return profile

    def _merge_hunter_data(self, profile: SocialProfile, data: Dict) -> SocialProfile:
        """Merge Hunter.io data into profile."""
        try:
            result = data.get("data", {})
            if result.get("first_name"):
                profile.full_name = f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
            if result.get("company"):
                profile.company = result["company"]
            if result.get("position"):
                profile.job_title = result["position"]

            profile.data_source = profile.data_source or "hunter"
        except Exception as e:
            logger.error(f"Error merging Hunter data: {e}")

        return profile

    def batch_enrich(self, leads: List[Dict[str, Any]]) -> Dict[str, SocialProfile]:
        """Batch enrich multiple leads."""
        results = {}

        for lead in leads:
            lead_id = lead.get("id", str(id(lead)))

            # Try email enrichment first
            if lead.get("email"):
                profile = self.enrich_by_email(lead["email"])
                if profile:
                    results[lead_id] = profile
                    continue

            # Try Instagram
            if lead.get("instagram_username") or lead.get("source") == "instagram":
                username = lead.get("instagram_username") or lead.get("username", "")
                profile = self.enrich_instagram(
                    username=username,
                    bio=lead.get("bio", ""),
                    followers=lead.get("followers", 0)
                )
                results[lead_id] = profile
                continue

            # Try LinkedIn
            if lead.get("linkedin_url"):
                profile = self.enrich_linkedin(
                    profile_url=lead["linkedin_url"],
                    name=lead.get("name", ""),
                    headline=lead.get("headline", ""),
                    company=lead.get("company", "")
                )
                results[lead_id] = profile

        return results
