"""Parsers for different lead sources."""

from app.parsers.base import BaseParser, ParsedLead
from app.parsers.telegram_parser import TelegramParser
from app.parsers.avito_parser import AvitoParser
from app.parsers.freelance_parser import FreelanceParser
from app.parsers.forum_parser import ForumParser

__all__ = [
    "BaseParser",
    "ParsedLead",
    "TelegramParser",
    "AvitoParser",
    "FreelanceParser",
    "ForumParser",
]
