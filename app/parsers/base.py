"""Base parser class for all lead sources."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, AsyncGenerator

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


@dataclass
class ParsedLead:
    """Data class for parsed lead information."""
    name: str
    source_url: str
    original_request: str

    # Contact information (optional)
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    website: Optional[str] = None

    # Business information (optional)
    company_name: Optional[str] = None
    business_description: Optional[str] = None
    industry: Optional[str] = None

    # Lead details (optional)
    needs_description: Optional[str] = None
    budget_mentioned: Optional[str] = None
    urgency: Optional[str] = None

    # Metadata
    found_at: datetime = field(default_factory=datetime.utcnow)
    social_links: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for all parsers."""

    # Keywords for finding website-related requests (Russian + English)
    DEFAULT_KEYWORDS = [
        # Russian keywords
        "нужен сайт",
        "создать сайт",
        "разработка сайта",
        "сделать сайт",
        "заказать сайт",
        "ищу веб-разработчика",
        "ищу разработчика сайта",
        "нужен интернет-магазин",
        "создать интернет-магазин",
        "разработка интернет-магазина",
        "лендинг",
        "landing page",
        "нужен лендинг",
        "редизайн сайта",
        "обновить сайт",
        "переделать сайт",
        "доработка сайта",
        "веб-студия",
        "верстка сайта",
        "программист сайт",
        "фрилансер сайт",
        # English keywords
        "need website",
        "create website",
        "web developer needed",
        "looking for web developer",
        "website development",
        "e-commerce website",
        "online store",
        "web design",
        "website redesign",
    ]

    # Patterns for extracting contact information
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PHONE_PATTERN = re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,6}[-\s\.]?[0-9]{3,6}')
    TELEGRAM_PATTERN = re.compile(r'@([a-zA-Z][a-zA-Z0-9_]{4,31})|t\.me/([a-zA-Z][a-zA-Z0-9_]{4,31})')
    WEBSITE_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+')
    BUDGET_PATTERN = re.compile(r'бюджет[:\s]*([0-9\s]+(?:тыс|к|руб|₽|usd|\$|euro|€)?)|([0-9]+\s*(?:тыс|к|руб|₽|usd|\$|euro|€))', re.IGNORECASE)

    def __init__(self, keywords: Optional[list[str]] = None):
        """Initialize parser with optional custom keywords."""
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        self.ua = UserAgent()
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": self.ua.random},
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content."""
        try:
            session = await self.get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content."""
        return BeautifulSoup(html, 'lxml')

    def extract_email(self, text: str) -> Optional[str]:
        """Extract first email from text."""
        match = self.EMAIL_PATTERN.search(text)
        return match.group(0) if match else None

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract first phone number from text."""
        match = self.PHONE_PATTERN.search(text)
        return match.group(0) if match else None

    def extract_telegram(self, text: str) -> Optional[str]:
        """Extract first Telegram username from text."""
        match = self.TELEGRAM_PATTERN.search(text)
        if match:
            return match.group(1) or match.group(2)
        return None

    def extract_website(self, text: str) -> Optional[str]:
        """Extract first website URL from text."""
        match = self.WEBSITE_PATTERN.search(text)
        return match.group(0) if match else None

    def extract_budget(self, text: str) -> Optional[str]:
        """Extract budget mention from text."""
        match = self.BUDGET_PATTERN.search(text)
        return match.group(0) if match else None

    def contains_keyword(self, text: str) -> bool:
        """Check if text contains any keyword."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)

    def estimate_urgency(self, text: str) -> str:
        """Estimate urgency based on text content."""
        text_lower = text.lower()
        urgent_markers = ["срочно", "asap", "urgent", "быстро", "сегодня", "завтра", "на этой неделе"]
        high_markers = ["скоро", "в ближайшее время", "на следующей неделе"]

        if any(marker in text_lower for marker in urgent_markers):
            return "urgent"
        if any(marker in text_lower for marker in high_markers):
            return "high"
        return "medium"

    def extract_contacts(self, text: str) -> dict:
        """Extract all contact information from text."""
        return {
            "email": self.extract_email(text),
            "phone": self.extract_phone(text),
            "telegram": self.extract_telegram(text),
            "website": self.extract_website(text),
        }

    @abstractmethod
    async def search(self, max_results: int = 50) -> AsyncGenerator[ParsedLead, None]:
        """
        Search for leads. Must be implemented by subclasses.

        Yields ParsedLead objects.
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this source."""
        pass

    @abstractmethod
    def get_source_type(self) -> str:
        """Return the type of this source (from SourceType enum)."""
        pass
