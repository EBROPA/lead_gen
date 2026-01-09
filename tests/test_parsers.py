"""Tests for parsers."""

import pytest
from app.parsers.base import BaseParser, ParsedLead


class TestBaseParser:
    """Tests for BaseParser utility methods."""

    def test_extract_email(self):
        """Test email extraction."""
        class ConcreteParser(BaseParser):
            async def search(self, max_results=50):
                yield ParsedLead(name="test", source_url="test", original_request="test")
            def get_source_name(self): return "test"
            def get_source_type(self): return "test"

        parser = ConcreteParser()

        # Test valid emails
        assert parser.extract_email("contact me at test@example.com") == "test@example.com"
        assert parser.extract_email("email: user.name@domain.co.uk please") == "user.name@domain.co.uk"

        # Test no email
        assert parser.extract_email("no email here") is None

    def test_extract_phone(self):
        """Test phone extraction."""
        class ConcreteParser(BaseParser):
            async def search(self, max_results=50):
                yield ParsedLead(name="test", source_url="test", original_request="test")
            def get_source_name(self): return "test"
            def get_source_type(self): return "test"

        parser = ConcreteParser()

        # Test valid phones
        assert parser.extract_phone("+7 999 123-45-67") is not None
        assert parser.extract_phone("call 8-800-555-35-35") is not None

        # Test no phone
        assert parser.extract_phone("no phone here") is None

    def test_extract_telegram(self):
        """Test Telegram username extraction."""
        class ConcreteParser(BaseParser):
            async def search(self, max_results=50):
                yield ParsedLead(name="test", source_url="test", original_request="test")
            def get_source_name(self): return "test"
            def get_source_type(self): return "test"

        parser = ConcreteParser()

        # Test valid usernames
        assert parser.extract_telegram("write me @username") == "username"
        assert parser.extract_telegram("t.me/myusername link") == "myusername"

        # Test no telegram
        assert parser.extract_telegram("no telegram here") is None

    def test_extract_budget(self):
        """Test budget extraction."""
        class ConcreteParser(BaseParser):
            async def search(self, max_results=50):
                yield ParsedLead(name="test", source_url="test", original_request="test")
            def get_source_name(self): return "test"
            def get_source_type(self): return "test"

        parser = ConcreteParser()

        # Test budget mentions
        assert parser.extract_budget("бюджет: 100 тыс руб") is not None
        assert parser.extract_budget("50k budget") is not None

    def test_contains_keyword(self):
        """Test keyword detection."""
        class ConcreteParser(BaseParser):
            async def search(self, max_results=50):
                yield ParsedLead(name="test", source_url="test", original_request="test")
            def get_source_name(self): return "test"
            def get_source_type(self): return "test"

        parser = ConcreteParser()

        # Test keyword detection
        assert parser.contains_keyword("Нужен сайт для магазина")
        assert parser.contains_keyword("Ищу веб-разработчика")
        assert parser.contains_keyword("создать интернет-магазин")
        assert not parser.contains_keyword("просто какой-то текст")

    def test_estimate_urgency(self):
        """Test urgency estimation."""
        class ConcreteParser(BaseParser):
            async def search(self, max_results=50):
                yield ParsedLead(name="test", source_url="test", original_request="test")
            def get_source_name(self): return "test"
            def get_source_type(self): return "test"

        parser = ConcreteParser()

        assert parser.estimate_urgency("срочно нужен сайт") == "urgent"
        assert parser.estimate_urgency("быстро сделать") == "urgent"
        assert parser.estimate_urgency("в ближайшее время") == "high"
        assert parser.estimate_urgency("нужен сайт") == "medium"


class TestParsedLead:
    """Tests for ParsedLead dataclass."""

    def test_parsed_lead_creation(self):
        """Test creating a ParsedLead."""
        lead = ParsedLead(
            name="Test User",
            source_url="https://example.com/post/1",
            original_request="Нужен сайт для магазина",
            email="test@example.com",
            telegram="@testuser",
        )

        assert lead.name == "Test User"
        assert lead.source_url == "https://example.com/post/1"
        assert lead.email == "test@example.com"
        assert lead.telegram == "@testuser"
        assert lead.found_at is not None
