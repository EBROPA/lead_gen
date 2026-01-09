"""Parser for freelance platforms (FL.ru, Kwork, etc.)."""

import re
from typing import AsyncGenerator, Optional
from datetime import datetime

from app.parsers.base import BaseParser, ParsedLead


class FreelanceParser(BaseParser):
    """Parser for Russian freelance platforms."""

    # Freelance platform configurations
    PLATFORMS = {
        "fl.ru": {
            "base_url": "https://www.fl.ru",
            "search_path": "/projects/?kind=5&category=37",  # Web development category
            "item_selector": "div.b-post",
            "title_selector": "a.b-post__link",
            "desc_selector": "div.b-post__body",
            "price_selector": "div.b-post__price",
        },
        "kwork": {
            "base_url": "https://kwork.ru",
            "search_path": "/projects?c=41",  # Sites and landing pages
            "item_selector": "div.wants-card",
            "title_selector": "a.wants-card__header-title",
            "desc_selector": "div.wants-card__description",
            "price_selector": "div.wants-card__header-price",
        },
        "habr_freelance": {
            "base_url": "https://freelance.habr.com",
            "search_path": "/tasks?categories=development_all_inclusive,development_sites",
            "item_selector": "article.task",
            "title_selector": "a.task__title",
            "desc_selector": "div.task__description",
            "price_selector": "span.task__price",
        },
    }

    def __init__(
        self,
        platforms: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None
    ):
        """Initialize freelance parser."""
        super().__init__(keywords)
        self.platforms = platforms or list(self.PLATFORMS.keys())

    def get_source_name(self) -> str:
        return "Freelance Platforms"

    def get_source_type(self) -> str:
        return "freelance_platform"

    async def parse_platform(self, platform_name: str) -> list[dict]:
        """Parse a freelance platform's project listing."""
        if platform_name not in self.PLATFORMS:
            return []

        config = self.PLATFORMS[platform_name]
        url = config["base_url"] + config["search_path"]
        html = await self.fetch_page(url)

        if not html:
            return []

        soup = self.parse_html(html)
        results = []

        items = soup.select(config["item_selector"])

        for item in items[:30]:  # Limit to 30 items per platform
            try:
                # Get title
                title_el = item.select_one(config["title_selector"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                item_url = title_el.get("href", "")
                if not item_url.startswith("http"):
                    item_url = config["base_url"] + item_url

                # Get description
                desc_el = item.select_one(config["desc_selector"])
                description = desc_el.get_text(strip=True) if desc_el else ""

                # Get price/budget
                price_el = item.select_one(config["price_selector"])
                price = price_el.get_text(strip=True) if price_el else None

                # Check for relevant keywords
                full_text = f"{title} {description}"
                if not self.contains_keyword(full_text):
                    continue

                results.append({
                    "title": title,
                    "url": item_url,
                    "description": description,
                    "price": price,
                    "platform": platform_name,
                })

            except Exception as e:
                print(f"Error parsing {platform_name} item: {e}")
                continue

        return results

    def create_lead_from_project(self, project: dict) -> ParsedLead:
        """Create a ParsedLead from a freelance project."""
        text = f"{project['title']} {project['description']}"
        contacts = self.extract_contacts(text)

        return ParsedLead(
            name=f"Client from {project['platform']}",
            source_url=project["url"],
            original_request=project["title"],
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            telegram=contacts.get("telegram"),
            website=contacts.get("website"),
            needs_description=project["description"][:500] if project["description"] else project["title"],
            budget_mentioned=project.get("price"),
            urgency=self.estimate_urgency(text),
            raw_data=project,
        )

    async def search(self, max_results: int = 50) -> AsyncGenerator[ParsedLead, None]:
        """Search for leads on freelance platforms."""
        results_count = 0

        for platform in self.platforms:
            if results_count >= max_results:
                break

            try:
                projects = await self.parse_platform(platform)

                for project in projects:
                    if results_count >= max_results:
                        break

                    lead = self.create_lead_from_project(project)
                    yield lead
                    results_count += 1

            except Exception as e:
                print(f"Error searching {platform}: {e}")
                continue

        await self.close()


class KworkParser(FreelanceParser):
    """Specialized parser for Kwork.ru."""

    def __init__(self, keywords: Optional[list[str]] = None):
        super().__init__(platforms=["kwork"], keywords=keywords)

    def get_source_name(self) -> str:
        return "Kwork.ru"


class FLParser(FreelanceParser):
    """Specialized parser for FL.ru."""

    def __init__(self, keywords: Optional[list[str]] = None):
        super().__init__(platforms=["fl.ru"], keywords=keywords)

    def get_source_name(self) -> str:
        return "FL.ru"


class HabrFreelanceParser(FreelanceParser):
    """Specialized parser for Habr Freelance."""

    def __init__(self, keywords: Optional[list[str]] = None):
        super().__init__(platforms=["habr_freelance"], keywords=keywords)

    def get_source_name(self) -> str:
        return "Habr Freelance"
