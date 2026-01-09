"""Parser for Telegram channels and chats (via web preview)."""

import re
from typing import AsyncGenerator, Optional
from datetime import datetime

from app.parsers.base import BaseParser, ParsedLead


class TelegramParser(BaseParser):
    """Parser for Telegram channels via t.me web preview."""

    # Public channels for web development requests
    DEFAULT_CHANNELS = [
        "freelancetavern",
        "web_freelance",
        "it_freelance",
        "freelance_ru",
        "devjobs",
    ]

    def __init__(
        self,
        channels: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None
    ):
        """Initialize Telegram parser."""
        super().__init__(keywords)
        self.channels = channels or self.DEFAULT_CHANNELS

    def get_source_name(self) -> str:
        return "Telegram Channels"

    def get_source_type(self) -> str:
        return "telegram_channel"

    async def parse_channel_page(self, channel: str) -> list[dict]:
        """Parse a Telegram channel's web preview."""
        url = f"https://t.me/s/{channel}"
        html = await self.fetch_page(url)

        if not html:
            return []

        soup = self.parse_html(html)
        messages = []

        # Find all message widgets
        message_widgets = soup.find_all("div", class_="tgme_widget_message_wrap")

        for widget in message_widgets:
            try:
                # Get message text
                text_div = widget.find("div", class_="tgme_widget_message_text")
                if not text_div:
                    continue

                text = text_div.get_text(strip=True)

                # Skip if no relevant keywords
                if not self.contains_keyword(text):
                    continue

                # Get message link
                link_tag = widget.find("a", class_="tgme_widget_message_date")
                message_link = link_tag.get("href") if link_tag else url

                # Get post date
                time_tag = widget.find("time")
                post_date = None
                if time_tag and time_tag.get("datetime"):
                    try:
                        post_date = datetime.fromisoformat(
                            time_tag.get("datetime").replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                # Get author info if available
                author_tag = widget.find("a", class_="tgme_widget_message_owner_name")
                author_name = author_tag.get_text(strip=True) if author_tag else channel

                messages.append({
                    "text": text,
                    "url": message_link,
                    "channel": channel,
                    "author": author_name,
                    "date": post_date or datetime.utcnow(),
                })

            except Exception as e:
                print(f"Error parsing message in {channel}: {e}")
                continue

        return messages

    def create_lead_from_message(self, message: dict) -> ParsedLead:
        """Create a ParsedLead from a Telegram message."""
        text = message["text"]
        contacts = self.extract_contacts(text)

        # Try to extract a name from the text
        name = message.get("author", "Unknown")

        # Look for name patterns in Russian
        name_patterns = [
            r"меня зовут\s+([А-Яа-яЁёA-Za-z]+)",
            r"я\s+([А-Яа-яЁёA-Za-z]+)",
            r"обращаться к\s+([А-Яа-яЁёA-Za-z]+)",
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1)
                break

        return ParsedLead(
            name=name,
            source_url=message["url"],
            original_request=text,
            email=contacts.get("email"),
            phone=contacts.get("phone"),
            telegram=contacts.get("telegram") or f"@{message['channel']}",
            website=contacts.get("website"),
            needs_description=text[:500],
            budget_mentioned=self.extract_budget(text),
            urgency=self.estimate_urgency(text),
            found_at=message.get("date", datetime.utcnow()),
            raw_data=message,
        )

    async def search(self, max_results: int = 50) -> AsyncGenerator[ParsedLead, None]:
        """Search for leads in Telegram channels."""
        results_count = 0

        for channel in self.channels:
            if results_count >= max_results:
                break

            try:
                messages = await self.parse_channel_page(channel)

                for message in messages:
                    if results_count >= max_results:
                        break

                    lead = self.create_lead_from_message(message)
                    yield lead
                    results_count += 1

            except Exception as e:
                print(f"Error searching channel {channel}: {e}")
                continue

        await self.close()
