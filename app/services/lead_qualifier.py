"""Lead qualifier service - qualifies and scores leads using AI and rules."""

import json
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, LeadStatus, WebsiteAnalysis
from app.services.ai_provider import ai_service


class LeadQualifierService:
    """Service for qualifying and scoring leads."""

    # Industry keywords for classification
    INDUSTRY_KEYWORDS = {
        "e-commerce": ["магазин", "shop", "товар", "продаж", "интернет-магазин", "e-commerce", "marketplace"],
        "services": ["услуг", "сервис", "service", "консалтинг", "юрист", "врач", "клиника"],
        "restaurant": ["ресторан", "кафе", "еда", "доставка еды", "restaurant", "food"],
        "real_estate": ["недвижимость", "квартир", "дом", "аренд", "real estate", "property"],
        "education": ["обучение", "курс", "школа", "education", "training", "course"],
        "beauty": ["салон", "красот", "косметик", "beauty", "spa", "wellness"],
        "auto": ["авто", "машин", "car", "auto", "transport"],
        "fitness": ["фитнес", "спорт", "gym", "fitness", "sport"],
        "tech": ["IT", "технолог", "software", "приложение", "app", "tech"],
        "manufacturing": ["производств", "завод", "фабрик", "manufacturing", "factory"],
    }

    # Budget indicators
    BUDGET_INDICATORS = {
        "high": [
            r"\d{3,}\s*(?:тыс|k|К)",  # 100k+
            r"(?:от|from)\s*\d{2,}\s*(?:тыс|k|К)",
            r"бюджет\s*(?:не\s*)?ограничен",
            r"budget\s*(?:is\s*)?(?:not\s*)?limited",
        ],
        "medium": [
            r"(?:30|40|50|60|70|80|90)\s*(?:тыс|k|К)",
            r"(?:от|from)\s*(?:30|40|50)\s*(?:тыс|k|К)",
        ],
        "low": [
            r"(?:5|10|15|20|25)\s*(?:тыс|k|К)",
            r"(?:до|up\s*to)\s*(?:20|30)\s*(?:тыс|k|К)",
            r"минимальн|cheap|дешев",
        ],
    }

    # Urgency indicators
    URGENCY_INDICATORS = {
        "urgent": [
            r"срочно",
            r"asap",
            r"urgent",
            r"как\s*можно\s*скорее",
            r"сегодня",
            r"завтра",
        ],
        "high": [
            r"быстро",
            r"скоро",
            r"на\s*этой\s*неделе",
            r"в\s*ближайшее\s*время",
            r"this\s*week",
        ],
        "medium": [
            r"в\s*течение\s*месяца",
            r"на\s*следующей\s*неделе",
            r"next\s*week",
        ],
    }

    # Disqualification patterns (spam, not relevant)
    DISQUALIFY_PATTERNS = [
        r"бесплатно",
        r"free",
        r"(?:без|no)\s*(?:оплаты|payment)",
        r"(?:очень\s*)?(?:маленький|small)\s*бюджет",
        r"тестов(?:ое|ый)\s*задани",
        r"test\s*(?:task|assignment)",
        r"(?:крипт|crypto)",
        r"(?:казино|casino|betting|ставк)",
        r"(?:адалт|adult|porn|xxx)",
    ]

    def __init__(self, db: AsyncSession):
        """Initialize the qualifier service."""
        self.db = db

    def detect_industry(self, text: str) -> Optional[str]:
        """Detect industry from text."""
        text_lower = text.lower()

        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return industry

        return None

    def estimate_budget_level(self, text: str) -> tuple[str, float]:
        """Estimate budget level and score from text."""
        text_lower = text.lower()

        for level, patterns in self.BUDGET_INDICATORS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if level == "high":
                        return level, 85.0
                    elif level == "medium":
                        return level, 60.0
                    else:
                        return level, 35.0

        # Default: unknown budget
        return "unknown", 50.0

    def estimate_urgency_level(self, text: str) -> tuple[str, float]:
        """Estimate urgency level and score from text."""
        text_lower = text.lower()

        for level, patterns in self.URGENCY_INDICATORS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if level == "urgent":
                        return level, 95.0
                    elif level == "high":
                        return level, 75.0
                    else:
                        return level, 55.0

        # Default: normal urgency
        return "normal", 40.0

    def check_disqualification(self, text: str) -> tuple[bool, Optional[str]]:
        """Check if lead should be disqualified."""
        text_lower = text.lower()

        for pattern in self.DISQUALIFY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True, f"Matched disqualification pattern: {pattern}"

        return False, None

    def calculate_fit_score(
        self,
        has_contact: bool,
        has_website: bool,
        website_score: Optional[float],
        budget_level: str,
        urgency_level: str,
        industry: Optional[str]
    ) -> float:
        """Calculate overall fit score."""
        score = 50.0  # Base score

        # Contact availability (+20 max)
        if has_contact:
            score += 20.0

        # Website situation
        if has_website:
            if website_score is not None:
                if website_score < 50:
                    score += 15.0  # Poor website = good opportunity
                elif website_score < 70:
                    score += 10.0
        else:
            score += 10.0  # No website = needs one

        # Budget adjustment
        if budget_level == "high":
            score += 15.0
        elif budget_level == "medium":
            score += 10.0
        elif budget_level == "low":
            score -= 10.0

        # Urgency adjustment
        if urgency_level == "urgent":
            score += 10.0
        elif urgency_level == "high":
            score += 7.0

        # Known industry bonus
        if industry:
            score += 5.0

        return min(100.0, max(0.0, score))

    async def qualify_lead(self, lead_id: int) -> Lead:
        """Qualify a single lead and update its scores."""
        # Get lead with website analysis
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Combine all text for analysis
        full_text = " ".join(filter(None, [
            lead.original_request or "",
            lead.needs_description or "",
            lead.business_description or "",
        ]))

        # Check for disqualification
        should_disqualify, reason = self.check_disqualification(full_text)
        if should_disqualify:
            lead.status = LeadStatus.DISQUALIFIED
            lead.qualification_notes = reason
            lead.qualification_score = 0
            await self.db.commit()
            return lead

        # Detect industry
        industry = self.detect_industry(full_text)
        if industry and not lead.industry:
            lead.industry = industry

        # Estimate budget
        budget_level, budget_score = self.estimate_budget_level(full_text)
        lead.budget_score = budget_score

        # Estimate urgency
        urgency_level, urgency_score = self.estimate_urgency_level(full_text)
        lead.urgency_score = urgency_score
        if not lead.urgency:
            lead.urgency = urgency_level

        # Get website analysis if available
        website_score = None
        if lead.website:
            wa_result = await self.db.execute(
                select(WebsiteAnalysis).where(WebsiteAnalysis.lead_id == lead_id)
            )
            website_analysis = wa_result.scalar_one_or_none()
            if website_analysis:
                website_score = website_analysis.overall_score

        # Calculate fit score
        fit_score = self.calculate_fit_score(
            has_contact=lead.contact_available,
            has_website=bool(lead.website),
            website_score=website_score,
            budget_level=budget_level,
            urgency_level=urgency_level,
            industry=industry,
        )
        lead.fit_score = fit_score

        # Calculate overall qualification score
        scores = [s for s in [budget_score, urgency_score, fit_score] if s is not None]
        lead.qualification_score = sum(scores) / len(scores) if scores else 50.0

        # Update status based on score
        if lead.qualification_score >= 70:
            lead.status = LeadStatus.QUALIFIED
            lead.priority = 2
        elif lead.qualification_score >= 50:
            lead.status = LeadStatus.QUALIFIED
            lead.priority = 1
        else:
            lead.status = LeadStatus.NEW
            lead.priority = 0

        # Generate qualification notes
        notes = []
        notes.append(f"Отрасль: {industry or 'не определена'}")
        notes.append(f"Бюджет: {budget_level} (оценка: {budget_score:.0f})")
        notes.append(f"Срочность: {urgency_level} (оценка: {urgency_score:.0f})")
        notes.append(f"Соответствие: {fit_score:.0f}")
        if website_score is not None:
            notes.append(f"Качество сайта: {website_score:.0f}")
        lead.qualification_notes = "\n".join(notes)

        await self.db.commit()
        await self.db.refresh(lead)

        return lead

    async def qualify_lead_with_ai(self, lead_id: int) -> Lead:
        """Qualify lead using AI for more nuanced analysis."""
        # Check if any AI provider is available
        if not ai_service.is_available():
            # Fallback to rule-based qualification
            return await self.qualify_lead(lead_id)

        # Get lead
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Prepare context for AI
        context = {
            "name": lead.name,
            "company": lead.company_name,
            "request": lead.original_request,
            "needs": lead.needs_description,
            "business": lead.business_description,
            "budget_mentioned": lead.budget_mentioned,
            "urgency": lead.urgency,
            "has_email": bool(lead.email),
            "has_phone": bool(lead.phone),
            "has_telegram": bool(lead.telegram),
            "has_website": bool(lead.website),
        }

        prompt = f"""Проанализируй потенциального клиента для веб-студии и оцени его по следующим критериям.

Данные о лиде:
{json.dumps(context, ensure_ascii=False, indent=2)}

Ответь ТОЛЬКО валидным JSON (без markdown, без ```):
{{
    "industry": "отрасль бизнеса",
    "budget_score": число от 0 до 100,
    "urgency_score": число от 0 до 100,
    "fit_score": число от 0 до 100,
    "is_spam": true или false,
    "spam_reason": "причина если спам или null",
    "project_type": "тип проекта (лендинг, корпоративный сайт, интернет-магазин, etc)",
    "estimated_budget_range": "примерный диапазон бюджета",
    "key_needs": ["потребность1", "потребность2"],
    "notes": "краткие заметки о лиде"
}}

Оценивай строго:
- budget_score: 0-30 для маленьких бюджетов, 30-60 для средних, 60-100 для больших
- urgency_score: выше если есть срочность
- fit_score: насколько этот лид подходит как клиент для веб-студии"""

        system_prompt = "Ты - эксперт по квалификации лидов для веб-студии. Отвечай ТОЛЬКО валидным JSON без каких-либо дополнительных символов или текста."

        try:
            ai_result = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                fallback_value=None,
            )

            if not ai_result:
                # AI failed, fallback to rule-based
                return await self.qualify_lead(lead_id)

            # Check for spam
            if ai_result.get("is_spam"):
                lead.status = LeadStatus.SPAM
                lead.qualification_notes = ai_result.get("spam_reason", "AI detected as spam")
                lead.qualification_score = 0
                await self.db.commit()
                return lead

            # Update lead with AI analysis
            lead.industry = ai_result.get("industry")
            lead.budget_score = float(ai_result.get("budget_score", 50))
            lead.urgency_score = float(ai_result.get("urgency_score", 50))
            lead.fit_score = float(ai_result.get("fit_score", 50))

            # Calculate overall score
            lead.qualification_score = (
                lead.budget_score * 0.3 +
                lead.urgency_score * 0.2 +
                lead.fit_score * 0.5
            )

            # Update status and priority
            if lead.qualification_score >= 70:
                lead.status = LeadStatus.QUALIFIED
                lead.priority = 2
            elif lead.qualification_score >= 50:
                lead.status = LeadStatus.QUALIFIED
                lead.priority = 1
            else:
                lead.status = LeadStatus.NEW
                lead.priority = 0

            # Store AI analysis
            lead.ai_analysis = ai_result
            lead.qualification_notes = ai_result.get("notes", "")

            await self.db.commit()
            await self.db.refresh(lead)

        except Exception as e:
            print(f"AI qualification failed: {e}")
            # Fallback to rule-based
            return await self.qualify_lead(lead_id)

        return lead

    async def qualify_all_new_leads(self, use_ai: bool = False) -> dict:
        """Qualify all leads with NEW status."""
        result = await self.db.execute(
            select(Lead).where(Lead.status == LeadStatus.NEW)
        )
        leads = result.scalars().all()

        results = {
            "qualified": 0,
            "disqualified": 0,
            "spam": 0,
            "errors": [],
        }

        for lead in leads:
            try:
                if use_ai:
                    qualified_lead = await self.qualify_lead_with_ai(lead.id)
                else:
                    qualified_lead = await self.qualify_lead(lead.id)

                if qualified_lead.status == LeadStatus.QUALIFIED:
                    results["qualified"] += 1
                elif qualified_lead.status == LeadStatus.DISQUALIFIED:
                    results["disqualified"] += 1
                elif qualified_lead.status == LeadStatus.SPAM:
                    results["spam"] += 1

            except Exception as e:
                results["errors"].append(f"Lead {lead.id}: {str(e)}")

        return results

    async def get_hot_leads(self, limit: int = 20) -> list[Lead]:
        """Get top qualified leads."""
        result = await self.db.execute(
            select(Lead)
            .where(
                Lead.status == LeadStatus.QUALIFIED,
                Lead.qualification_score >= 60
            )
            .order_by(Lead.qualification_score.desc(), Lead.priority.desc())
            .limit(limit)
        )
        return result.scalars().all()
