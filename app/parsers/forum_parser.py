"""Parser for forums and communities."""

import re
from typing import AsyncGenerator, Optional
from datetime import datetime

from app.parsers.base import BaseParser, ParsedLead


class ForumParser(BaseParser):
    """Parser for various forums and communities."""

    # Forum configurations
    FORUMS = {
        "searchengines": {
            "name": "SearchEngines.guru",
            "base_url": "https://searchengines.guru",
            "search_path": "/forumdisplay.php?f=29",  # Web development forum
            "item_selector": "li.threadbit",
            "title_selector": "a.title",
            "preview_selector": "div.threadbit-preview",
        },
        "maultalk": {
            "name": "MaulTalk",
            "base_url": "https://maultalk.com",
            "search_path": "/forum/50-veb-razrabotka/",
            "item_selector": "li.ipsDataItem",
            "title_selector": "a.ipsDataItem_title",
            "preview_selector": "div.ipsDataItem_meta",
        },
    }

    def __init__(
        self,
        forums: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None
    ):
        """Initialize forum parser."""
        super().__init__(keywords)
        self.forums = forums or list(self.FORUMS.keys())

    def get_source_name(self) -> str:
        return "Forums"

    def get_source_type(self) -> str:
        return "forum"

    async def parse_forum(self, forum_key: str) -> list[dict]:
        """Parse a forum's thread listing."""
        if forum_key not in self.FORUMS:
            return []

        config = self.FORUMS[forum_key]
        url = config["base_url"] + config["search_path"]
        html = await self.fetch_page(url)

        if not html:
            return []

        soup = self.parse_html(html)
        results = []

        items = soup.select(config["item_selector"])

        for item in items[:25]:  # Limit per forum
            try:
                # Get title
                title_el = item.select_one(config["title_selector"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                item_url = title_el.get("href", "")
                if not item_url.startswith("http"):
                    item_url = config["base_url"] + item_url

                # Get preview/description
                preview_el = item.select_one(config["preview_selector"])
                preview = preview_el.get_text(strip=True) if preview_el else ""

                # Look for "looking for" or request-type threads
                full_text = f"{title} {preview}".lower()
                request_markers = [
                    "ищу", "нужен", "требуется", "закажу",
                    "посоветуйте", "подскажите", "помогите",
                    "looking for", "need", "want"
                ]

                is_request = any(marker in full_text for marker in request_markers)

                if is_request and self.contains_keyword(full_text):
                    results.append({
                        "title": title,
                        "url": item_url,
                        "preview": preview,
                        "forum": config["name"],
                        "forum_key": forum_key,
                    })

            except Exception as e:
                print(f"Error parsing {forum_key} item: {e}")
                continue

        return results

    async def parse_thread(self, thread_url: str) -> Optional[dict]:
        """Parse a specific forum thread for more details."""
        html = await self.fetch_page(thread_url)

        if not html:
            return None

        soup = self.parse_html(html)

        # Try to get the first post content
        post_selectors = [
            "div.postcontent",
            "div.post-content",
            "div.message-body",
            "article.message-body",
            "div.cPost_contentWrap",
        ]

        content = ""
        for selector in post_selectors:
            post_el = soup.select_one(selector)
            if post_el:
                content = post_el.get_text(strip=True)
                break

        # Try to get author info
        author_selectors = [
            "a.username",
            "span.author",
            "a.ipsDataItem_author",
            "div.postdetails a",
        ]

        author = ""
        for selector in author_selectors:
            author_el = soup.select_one(selector)
            if author_el:
                author = author_el.get_text(strip=True)
                break

        return {
            "content": content,
            "author": author,
        }

    def create_lead_from_thread(self, thread: dict, details: Optional[dict] = None) -> ParsedLead:
        """Create a ParsedLead from a forum thread."""
        text = thread.get("preview", "") + " " + (details.get("content", "") if details else "")
        contacts = self.extract_contacts(text)

        author = details.get("author", "") if details else ""
        name = author if author else f"User from {thread['forum']}"

        return ParsedLead(
            name=name,
            source_url=thread["url"],
            original_request=thread["title"],
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            telegram=contacts.get("telegram"),
            website=contacts.get("website"),
            needs_description=text[:500] if text else thread["title"],
            budget_mentioned=self.extract_budget(text),
            urgency=self.estimate_urgency(text),
            raw_data={**thread, **(details or {})},
        )

    async def search(self, max_results: int = 50) -> AsyncGenerator[ParsedLead, None]:
        """Search for leads in forums."""
        results_count = 0

        for forum_key in self.forums:
            if results_count >= max_results:
                break

            try:
                threads = await self.parse_forum(forum_key)

                for thread in threads:
                    if results_count >= max_results:
                        break

                    # Optionally get thread details
                    # details = await self.parse_thread(thread["url"])
                    details = None  # Skip for performance

                    lead = self.create_lead_from_thread(thread, details)
                    yield lead
                    results_count += 1

            except Exception as e:
                print(f"Error searching {forum_key}: {e}")
                continue

        await self.close()
