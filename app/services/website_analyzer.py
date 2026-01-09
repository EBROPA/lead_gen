"""Website analyzer service - analyzes websites for quality and issues."""

import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, WebsiteAnalysis
from app.config import settings


class WebsiteAnalyzerService:
    """Service for analyzing websites and finding improvement opportunities."""

    # Common issues to check
    ISSUE_CHECKS = {
        "no_ssl": {
            "severity": "critical",
            "description": "Сайт не использует HTTPS",
            "suggestion": "Установить SSL сертификат для защиты данных пользователей",
        },
        "slow_loading": {
            "severity": "high",
            "description": "Медленная загрузка страницы",
            "suggestion": "Оптимизировать изображения, включить кэширование, использовать CDN",
        },
        "no_mobile": {
            "severity": "high",
            "description": "Сайт не адаптирован для мобильных устройств",
            "suggestion": "Внедрить адаптивный дизайн или мобильную версию",
        },
        "no_meta": {
            "severity": "medium",
            "description": "Отсутствуют мета-теги для SEO",
            "suggestion": "Добавить title, description и Open Graph теги",
        },
        "broken_links": {
            "severity": "medium",
            "description": "Обнаружены битые ссылки",
            "suggestion": "Исправить или удалить неработающие ссылки",
        },
        "no_favicon": {
            "severity": "low",
            "description": "Отсутствует favicon",
            "suggestion": "Добавить иконку сайта для лучшего брендинга",
        },
        "outdated_design": {
            "severity": "medium",
            "description": "Устаревший дизайн",
            "suggestion": "Обновить дизайн в соответствии с современными трендами",
        },
        "no_contact_form": {
            "severity": "medium",
            "description": "Отсутствует форма обратной связи",
            "suggestion": "Добавить форму для удобной связи с клиентами",
        },
        "no_social": {
            "severity": "low",
            "description": "Нет ссылок на социальные сети",
            "suggestion": "Добавить ссылки на социальные сети для увеличения доверия",
        },
    }

    # Technology detection patterns
    TECH_PATTERNS = {
        "WordPress": [r"wp-content", r"wp-includes", r"wordpress"],
        "Joomla": [r"com_content", r"joomla"],
        "Drupal": [r"drupal", r"sites/default"],
        "1C-Bitrix": [r"bitrix", r"/bitrix/"],
        "Tilda": [r"tilda", r"tildacdn"],
        "Wix": [r"wixsite", r"wix.com"],
        "Shopify": [r"shopify", r"cdn.shopify"],
        "OpenCart": [r"opencart", r"route=common"],
        "ModX": [r"modx"],
        "React": [r"react", r"_next", r"__NEXT_DATA__"],
        "Vue.js": [r"vue", r"__VUE__"],
        "Angular": [r"ng-version", r"angular"],
        "Bootstrap": [r"bootstrap"],
        "jQuery": [r"jquery"],
    }

    def __init__(self, db: AsyncSession):
        """Initialize the website analyzer service."""
        self.db = db
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def normalize_url(self, url: str) -> str:
        """Normalize URL to include protocol."""
        if not url:
            return ""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    async def fetch_website(self, url: str) -> dict:
        """Fetch website and return response details."""
        url = self.normalize_url(url)
        result = {
            "url": url,
            "is_accessible": False,
            "status_code": None,
            "load_time_ms": None,
            "html": None,
            "final_url": None,
            "error": None,
        }

        try:
            session = await self.get_session()
            start_time = time.time()

            async with session.get(url, allow_redirects=True) as response:
                load_time = int((time.time() - start_time) * 1000)

                result["is_accessible"] = response.status == 200
                result["status_code"] = response.status
                result["load_time_ms"] = load_time
                result["final_url"] = str(response.url)

                if response.status == 200:
                    result["html"] = await response.text()

        except aiohttp.ClientError as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)

        return result

    def detect_technologies(self, html: str) -> list[str]:
        """Detect technologies used on the website."""
        technologies = []
        html_lower = html.lower()

        for tech, patterns in self.TECH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html_lower, re.IGNORECASE):
                    technologies.append(tech)
                    break

        return list(set(technologies))

    def detect_cms(self, html: str, technologies: list[str]) -> Optional[str]:
        """Detect the CMS used."""
        cms_list = ["WordPress", "Joomla", "Drupal", "1C-Bitrix", "Tilda", "Wix", "Shopify", "OpenCart", "ModX"]
        for cms in cms_list:
            if cms in technologies:
                return cms
        return None

    def check_ssl(self, url: str) -> bool:
        """Check if website uses SSL."""
        return url.startswith("https://")

    def check_mobile_friendly(self, html: str) -> bool:
        """Check if website appears to be mobile-friendly."""
        soup = BeautifulSoup(html, "lxml")

        # Check for viewport meta tag
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport:
            return True

        # Check for responsive classes
        responsive_patterns = [
            r"responsive",
            r"mobile",
            r"col-\d+",
            r"col-sm-",
            r"col-md-",
            r"col-lg-",
        ]

        for pattern in responsive_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                return True

        return False

    def extract_meta_info(self, html: str) -> dict:
        """Extract meta information from HTML."""
        soup = BeautifulSoup(html, "lxml")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else None

        return {
            "title": title,
            "description": description,
            "has_title": bool(title),
            "has_description": bool(description),
        }

    def check_contact_form(self, html: str) -> bool:
        """Check if website has a contact form."""
        soup = BeautifulSoup(html, "lxml")

        # Look for form tags
        forms = soup.find_all("form")
        for form in forms:
            form_text = str(form).lower()
            if any(word in form_text for word in ["contact", "feedback", "message", "email", "phone", "обратн", "связ", "контакт"]):
                return True

        return False

    def check_social_links(self, html: str) -> bool:
        """Check if website has social media links."""
        social_patterns = [
            r"facebook\.com",
            r"vk\.com",
            r"instagram\.com",
            r"twitter\.com",
            r"linkedin\.com",
            r"youtube\.com",
            r"t\.me",
            r"telegram\.me",
        ]

        for pattern in social_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                return True

        return False

    def calculate_performance_score(self, load_time_ms: int) -> float:
        """Calculate performance score based on load time."""
        # Ideal load time: < 1000ms = 100 points
        # Each additional second reduces score by 15 points
        if load_time_ms < 1000:
            return 100.0
        elif load_time_ms < 2000:
            return 85.0
        elif load_time_ms < 3000:
            return 70.0
        elif load_time_ms < 5000:
            return 55.0
        elif load_time_ms < 10000:
            return 40.0
        else:
            return 25.0

    def calculate_seo_score(self, meta_info: dict, has_ssl: bool) -> float:
        """Calculate basic SEO score."""
        score = 0.0

        if meta_info.get("has_title"):
            score += 35
        if meta_info.get("has_description"):
            score += 35
        if has_ssl:
            score += 30

        return score

    def find_issues(self, analysis_data: dict) -> list[dict]:
        """Find issues based on analysis data."""
        issues = []

        if not analysis_data.get("has_ssl"):
            issues.append({
                "code": "no_ssl",
                **self.ISSUE_CHECKS["no_ssl"],
            })

        if analysis_data.get("load_time_ms", 0) > 3000:
            issues.append({
                "code": "slow_loading",
                **self.ISSUE_CHECKS["slow_loading"],
            })

        if not analysis_data.get("is_mobile_friendly"):
            issues.append({
                "code": "no_mobile",
                **self.ISSUE_CHECKS["no_mobile"],
            })

        if not analysis_data.get("has_title") or not analysis_data.get("has_description"):
            issues.append({
                "code": "no_meta",
                **self.ISSUE_CHECKS["no_meta"],
            })

        if not analysis_data.get("has_contact_form"):
            issues.append({
                "code": "no_contact_form",
                **self.ISSUE_CHECKS["no_contact_form"],
            })

        if not analysis_data.get("has_social_links"):
            issues.append({
                "code": "no_social",
                **self.ISSUE_CHECKS["no_social"],
            })

        return issues

    def generate_suggestions(self, issues: list[dict]) -> list[str]:
        """Generate improvement suggestions based on issues."""
        suggestions = []

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x["severity"], 4))

        for issue in sorted_issues:
            suggestions.append(issue["suggestion"])

        return suggestions

    async def analyze_website(self, url: str) -> dict:
        """Perform full website analysis."""
        # Fetch the website
        fetch_result = await self.fetch_website(url)

        if not fetch_result["is_accessible"]:
            return {
                "url": url,
                "is_accessible": False,
                "status_code": fetch_result.get("status_code"),
                "error": fetch_result.get("error"),
                "overall_score": 0,
            }

        html = fetch_result["html"]

        # Analyze various aspects
        has_ssl = self.check_ssl(fetch_result["final_url"])
        is_mobile_friendly = self.check_mobile_friendly(html)
        meta_info = self.extract_meta_info(html)
        has_contact_form = self.check_contact_form(html)
        has_social_links = self.check_social_links(html)
        technologies = self.detect_technologies(html)
        cms = self.detect_cms(html, technologies)

        # Calculate scores
        performance_score = self.calculate_performance_score(fetch_result["load_time_ms"])
        seo_score = self.calculate_seo_score(meta_info, has_ssl)

        # Design score is harder to calculate without visual analysis
        # We'll use a heuristic based on modern tech detection
        design_score = 50.0
        if "Bootstrap" in technologies or "React" in technologies or "Vue.js" in technologies:
            design_score = 70.0
        if is_mobile_friendly:
            design_score += 15

        # Overall score
        overall_score = (performance_score * 0.3 + seo_score * 0.3 + design_score * 0.4)

        # Compile analysis data
        analysis_data = {
            "has_ssl": has_ssl,
            "is_mobile_friendly": is_mobile_friendly,
            "has_title": meta_info.get("has_title"),
            "has_description": meta_info.get("has_description"),
            "has_contact_form": has_contact_form,
            "has_social_links": has_social_links,
            "load_time_ms": fetch_result["load_time_ms"],
        }

        # Find issues and suggestions
        issues = self.find_issues(analysis_data)
        suggestions = self.generate_suggestions(issues)

        return {
            "url": url,
            "final_url": fetch_result["final_url"],
            "is_accessible": True,
            "status_code": fetch_result["status_code"],
            "load_time_ms": fetch_result["load_time_ms"],
            "has_ssl": has_ssl,
            "is_mobile_friendly": is_mobile_friendly,
            "has_responsive_design": is_mobile_friendly,
            "performance_score": performance_score,
            "seo_score": seo_score,
            "design_score": design_score,
            "overall_score": overall_score,
            "title": meta_info.get("title"),
            "meta_description": meta_info.get("description"),
            "has_contact_form": has_contact_form,
            "has_social_links": has_social_links,
            "technologies": technologies,
            "cms_detected": cms,
            "issues": issues,
            "improvement_suggestions": suggestions,
        }

    async def analyze_lead_website(self, lead_id: int) -> Optional[WebsiteAnalysis]:
        """Analyze website for a specific lead and save results."""
        # Get lead
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead or not lead.website:
            return None

        # Check if analysis already exists
        result = await self.db.execute(
            select(WebsiteAnalysis).where(WebsiteAnalysis.lead_id == lead_id)
        )
        existing = result.scalar_one_or_none()

        # Perform analysis
        analysis_result = await self.analyze_website(lead.website)

        if existing:
            # Update existing analysis
            for key, value in analysis_result.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.analyzed_at = datetime.utcnow()
            analysis = existing
        else:
            # Create new analysis
            analysis = WebsiteAnalysis(
                lead_id=lead_id,
                url=lead.website,
                is_accessible=analysis_result.get("is_accessible", False),
                status_code=analysis_result.get("status_code"),
                load_time_ms=analysis_result.get("load_time_ms"),
                has_ssl=analysis_result.get("has_ssl"),
                is_mobile_friendly=analysis_result.get("is_mobile_friendly"),
                has_responsive_design=analysis_result.get("has_responsive_design"),
                performance_score=analysis_result.get("performance_score"),
                seo_score=analysis_result.get("seo_score"),
                design_score=analysis_result.get("design_score"),
                overall_score=analysis_result.get("overall_score"),
                title=analysis_result.get("title"),
                meta_description=analysis_result.get("meta_description"),
                has_contact_form=analysis_result.get("has_contact_form"),
                has_social_links=analysis_result.get("has_social_links"),
                technologies=analysis_result.get("technologies"),
                cms_detected=analysis_result.get("cms_detected"),
                issues=analysis_result.get("issues"),
                improvement_suggestions=analysis_result.get("improvement_suggestions"),
                raw_analysis=analysis_result,
            )
            self.db.add(analysis)

        await self.db.commit()
        await self.db.refresh(analysis)

        return analysis

    async def analyze_all_leads_websites(self, limit: int = 50) -> dict:
        """Analyze websites for all leads that have websites but no analysis."""
        # Get leads with websites but no analysis
        result = await self.db.execute(
            select(Lead)
            .outerjoin(WebsiteAnalysis)
            .where(
                Lead.website.isnot(None),
                Lead.website != "",
                WebsiteAnalysis.id.is_(None)
            )
            .limit(limit)
        )
        leads = result.scalars().all()

        results = {
            "analyzed": 0,
            "failed": 0,
            "errors": [],
        }

        for lead in leads:
            try:
                analysis = await self.analyze_lead_website(lead.id)
                if analysis:
                    results["analyzed"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Lead {lead.id}: {str(e)}")

        return results
