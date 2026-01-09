"""Parser for Avito classifieds (services section)."""

import re
from typing import AsyncGenerator, Optional
from urllib.parse import urlencode, quote

from app.parsers.base import BaseParser, ParsedLead


class AvitoParser(BaseParser):
    """Parser for Avito.ru classifieds."""

    BASE_URL = "https://www.avito.ru"

    # Search queries for website-related services
    DEFAULT_QUERIES = [
        "создание сайта",
        "разработка сайта",
        "интернет магазин",
        "веб разработка",
        "лендинг",
    ]

    def __init__(
        self,
        queries: Optional[list[str]] = None,
        location: str = "rossiya",
        keywords: Optional[list[str]] = None
    ):
        """Initialize Avito parser."""
        super().__init__(keywords)
        self.queries = queries or self.DEFAULT_QUERIES
        self.location = location

    def get_source_name(self) -> str:
        return "Avito"

    def get_source_type(self) -> str:
        return "classified_ads"

    def build_search_url(self, query: str, page: int = 1) -> str:
        """Build search URL for Avito."""
        # Avito services section: /uslugi
        params = {
            "q": query,
            "p": page,
        }
        return f"{self.BASE_URL}/{self.location}/uslugi?{urlencode(params)}"

    async def parse_search_results(self, query: str, page: int = 1) -> list[dict]:
        """Parse Avito search results page."""
        url = self.build_search_url(query, page)
        html = await self.fetch_page(url)

        if not html:
            return []

        soup = self.parse_html(html)
        results = []

        # Find listing items
        items = soup.find_all("div", {"data-marker": "item"})

        for item in items:
            try:
                # Get title
                title_tag = item.find("a", {"data-marker": "item-title"})
                if not title_tag:
                    continue

                title = title_tag.get("title", "") or title_tag.get_text(strip=True)
                item_url = self.BASE_URL + title_tag.get("href", "")

                # Get price
                price_tag = item.find("meta", {"itemprop": "price"})
                price = price_tag.get("content") if price_tag else None

                # Get description preview
                desc_tag = item.find("div", {"class": re.compile(r"item-description")})
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                # Get location
                location_tag = item.find("div", {"class": re.compile(r"geo-address")})
                location = location_tag.get_text(strip=True) if location_tag else ""

                # Get seller info
                seller_tag = item.find("div", {"data-marker": "item-line"})
                seller = seller_tag.get_text(strip=True) if seller_tag else ""

                # Check if this is a "looking for" post (not selling)
                full_text = f"{title} {description}".lower()
                is_looking = any(word in full_text for word in [
                    "ищу", "нужен", "требуется", "закажу", "куплю"
                ])

                if is_looking and self.contains_keyword(full_text):
                    results.append({
                        "title": title,
                        "url": item_url,
                        "price": price,
                        "description": description,
                        "location": location,
                        "seller": seller,
                        "query": query,
                    })

            except Exception as e:
                print(f"Error parsing Avito item: {e}")
                continue

        return results

    def create_lead_from_item(self, item: dict) -> ParsedLead:
        """Create a ParsedLead from an Avito item."""
        text = f"{item['title']} {item['description']}"
        contacts = self.extract_contacts(text)

        # Try to extract name from seller info or text
        name = item.get("seller", "").split()[0] if item.get("seller") else "Avito User"

        return ParsedLead(
            name=name,
            source_url=item["url"],
            original_request=item["title"],
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            telegram=contacts.get("telegram"),
            website=contacts.get("website"),
            business_description=item.get("description", ""),
            needs_description=item["title"],
            budget_mentioned=item.get("price"),
            urgency=self.estimate_urgency(text),
            raw_data=item,
        )

    async def search(self, max_results: int = 50) -> AsyncGenerator[ParsedLead, None]:
        """Search for leads on Avito."""
        results_count = 0

        for query in self.queries:
            if results_count >= max_results:
                break

            try:
                # Parse first 2 pages per query
                for page in range(1, 3):
                    if results_count >= max_results:
                        break

                    items = await self.parse_search_results(query, page)

                    for item in items:
                        if results_count >= max_results:
                            break

                        lead = self.create_lead_from_item(item)
                        yield lead
                        results_count += 1

            except Exception as e:
                print(f"Error searching Avito for '{query}': {e}")
                continue

        await self.close()
