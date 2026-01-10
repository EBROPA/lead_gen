"""Proposal generator service - generates personalized proposals for leads."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, Proposal, ProposalStatus, ProposalChannel, WebsiteAnalysis
from app.services.ai_provider import ai_service


class ProposalGeneratorService:
    """Service for generating personalized proposals for leads."""

    # Templates for different channels
    EMAIL_TEMPLATE = """Здравствуйте{name_greeting}!

{intro}

{website_analysis}

{value_proposition}

{portfolio}

{call_to_action}

С уважением,
{sender_name}
{sender_company}
{sender_contacts}
"""

    TELEGRAM_TEMPLATE = """Здравствуйте{name_greeting}!

{intro}

{website_analysis}

{value_proposition}

{call_to_action}
"""

    # Portfolio examples by industry
    PORTFOLIO_EXAMPLES = {
        "e-commerce": [
            {"name": "Интернет-магазин одежды", "result": "Увеличение конверсии на 35%"},
            {"name": "Маркетплейс товаров для дома", "result": "Рост продаж в 2 раза за 3 месяца"},
        ],
        "services": [
            {"name": "Сайт юридической компании", "result": "Увеличение заявок на 50%"},
            {"name": "Корпоративный сайт IT-компании", "result": "Снижение bounce rate на 40%"},
        ],
        "restaurant": [
            {"name": "Сайт ресторана с онлайн-бронированием", "result": "Рост бронирований на 60%"},
            {"name": "Сервис доставки еды", "result": "Снижение времени оформления заказа в 2 раза"},
        ],
        "real_estate": [
            {"name": "Каталог недвижимости", "result": "Увеличение заявок на просмотры на 45%"},
            {"name": "Сайт агентства недвижимости", "result": "Рост органического трафика на 80%"},
        ],
        "default": [
            {"name": "Корпоративный сайт", "result": "Улучшение пользовательского опыта"},
            {"name": "Лендинг для услуги", "result": "Высокая конверсия"},
        ],
    }

    # Intro templates based on source
    INTRO_TEMPLATES = {
        "telegram": "Увидел ваш запрос в Telegram-канале и хотел бы предложить свои услуги.",
        "freelance": "Заметил ваш проект на фриланс-бирже и уверен, что могу помочь.",
        "forum": "Прочитал вашу публикацию на форуме и готов предложить решение.",
        "avito": "Увидел ваше объявление и хочу предложить сотрудничество.",
        "default": "Обратил внимание на ваш запрос и хотел бы предложить свои услуги.",
    }

    # Value propositions based on needs
    VALUE_PROPOSITIONS = {
        "new_website": """
Я специализируюсь на создании современных, быстрых и конверсионных сайтов.

Что вы получите:
- Уникальный дизайн, адаптированный под вашу целевую аудиторию
- Мобильная версия и адаптивный дизайн
- SEO-оптимизация для продвижения в поисковиках
- Высокая скорость загрузки
- Удобная админ-панель для управления контентом
""",
        "redesign": """
Я помогу обновить ваш сайт и сделать его более современным и эффективным.

Что я предлагаю:
- Современный дизайн с учётом последних трендов
- Улучшение пользовательского опыта (UX)
- Оптимизация скорости загрузки
- Адаптация под мобильные устройства
- Сохранение существующего контента и SEO-позиций
""",
        "ecommerce": """
Я создаю интернет-магазины, которые продают.

Что входит в разработку:
- Каталог товаров с фильтрами и поиском
- Корзина и оформление заказа
- Интеграция с платёжными системами
- Личный кабинет покупателя
- Интеграция с CRM и системами учёта
- SEO-оптимизация карточек товаров
""",
        "landing": """
Создаю лендинги с высокой конверсией.

Преимущества работы со мной:
- Продающий дизайн и копирайтинг
- A/B тестирование
- Интеграция с CRM и аналитикой
- Быстрая загрузка страницы
- Адаптация под мобильные устройства
""",
    }

    def __init__(self, db: AsyncSession):
        """Initialize the proposal generator service."""
        self.db = db
        self.sender_name = "Ваш веб-разработчик"
        self.sender_company = ""
        self.sender_contacts = ""

    def configure_sender(
        self,
        name: str,
        company: str = "",
        contacts: str = ""
    ):
        """Configure sender information for proposals."""
        self.sender_name = name
        self.sender_company = company
        self.sender_contacts = contacts

    def detect_project_type(self, lead: Lead) -> str:
        """Detect what type of project the lead needs."""
        text = " ".join(filter(None, [
            lead.original_request or "",
            lead.needs_description or "",
        ])).lower()

        if any(word in text for word in ["магазин", "shop", "ecommerce", "товар", "корзин"]):
            return "ecommerce"
        if any(word in text for word in ["лендинг", "landing", "одностранич"]):
            return "landing"
        if any(word in text for word in ["редизайн", "обновить", "переделать", "улучшить"]):
            return "redesign"
        return "new_website"

    def get_source_type(self, lead: Lead) -> str:
        """Determine source type from lead data."""
        source_url = (lead.source_url or "").lower()

        if "t.me" in source_url or "telegram" in source_url:
            return "telegram"
        if any(platform in source_url for platform in ["fl.ru", "kwork", "freelance"]):
            return "freelance"
        if "avito" in source_url:
            return "avito"
        if any(word in source_url for word in ["forum", "searchengines"]):
            return "forum"
        return "default"

    def format_website_analysis(self, analysis: Optional[WebsiteAnalysis]) -> str:
        """Format website analysis for inclusion in proposal."""
        if not analysis:
            return ""

        if not analysis.is_accessible:
            return "Заметил, что ваш текущий сайт недоступен. Это серьёзная проблема, которую нужно решить как можно скорее.\n"

        parts = ["Проанализировал ваш текущий сайт и нашёл несколько моментов для улучшения:\n"]

        issues = analysis.issues or []
        suggestions = analysis.improvement_suggestions or []

        # Add top 3 issues
        for issue in issues[:3]:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(issue.get("severity", "medium"), "🟡")

            parts.append(f"{severity_emoji} {issue.get('description', '')}")

        if analysis.overall_score is not None and analysis.overall_score < 60:
            parts.append(f"\nОбщая оценка сайта: {analysis.overall_score:.0f}/100 — есть значительный потенциал для улучшения.")

        return "\n".join(parts) + "\n"

    def get_portfolio_section(self, industry: Optional[str], include: bool = True) -> str:
        """Generate portfolio section."""
        if not include:
            return ""

        examples = self.PORTFOLIO_EXAMPLES.get(industry, self.PORTFOLIO_EXAMPLES["default"])

        parts = ["\nНесколько примеров моих работ:\n"]
        for example in examples[:2]:
            parts.append(f"• {example['name']} — {example['result']}")

        return "\n".join(parts) + "\n"

    def get_call_to_action(self, channel: ProposalChannel) -> str:
        """Generate call to action based on channel."""
        if channel == ProposalChannel.EMAIL:
            return """
Буду рад обсудить ваш проект подробнее. Напишите мне, и мы договоримся об удобном времени для звонка или встречи.

Также можете ответить на несколько вопросов:
1. Какой у вас примерный бюджет на проект?
2. К какому сроку нужен готовый результат?
3. Есть ли референсы сайтов, которые вам нравятся?
"""
        elif channel == ProposalChannel.TELEGRAM:
            return """
Напишите, если интересно обсудить проект подробнее.

Буду рад ответить на ваши вопросы и подготовить предложение с точной стоимостью и сроками.
"""
        else:
            return "\nБуду рад обсудить ваш проект. Свяжитесь со мной удобным способом.\n"

    def generate_subject(self, lead: Lead, project_type: str) -> str:
        """Generate email subject line."""
        subjects = {
            "new_website": f"Создание сайта для {lead.company_name or 'вашего бизнеса'}",
            "redesign": f"Редизайн и улучшение вашего сайта",
            "ecommerce": f"Разработка интернет-магазина",
            "landing": f"Создание конверсионного лендинга",
        }
        return subjects.get(project_type, "Предложение по разработке сайта")

    async def generate_proposal(
        self,
        lead_id: int,
        channel: ProposalChannel = ProposalChannel.EMAIL,
        tone: str = "professional",
        include_portfolio: bool = True,
        include_website_analysis: bool = True,
        custom_notes: Optional[str] = None,
    ) -> Proposal:
        """Generate a personalized proposal for a lead."""
        # Get lead with website analysis
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Get website analysis if available
        website_analysis = None
        if include_website_analysis and lead.website:
            wa_result = await self.db.execute(
                select(WebsiteAnalysis).where(WebsiteAnalysis.lead_id == lead_id)
            )
            website_analysis = wa_result.scalar_one_or_none()

        # Detect project type and source
        project_type = self.detect_project_type(lead)
        source_type = self.get_source_type(lead)

        # Build proposal components
        name_greeting = f", {lead.name}" if lead.name and lead.name != "Unknown" else ""
        intro = self.INTRO_TEMPLATES.get(source_type, self.INTRO_TEMPLATES["default"])
        website_section = self.format_website_analysis(website_analysis) if include_website_analysis else ""
        value_prop = self.VALUE_PROPOSITIONS.get(project_type, self.VALUE_PROPOSITIONS["new_website"])
        portfolio = self.get_portfolio_section(lead.industry, include_portfolio)
        cta = self.get_call_to_action(channel)

        # Choose template based on channel
        if channel == ProposalChannel.TELEGRAM:
            template = self.TELEGRAM_TEMPLATE
        else:
            template = self.EMAIL_TEMPLATE

        # Generate content
        content = template.format(
            name_greeting=name_greeting,
            intro=intro,
            website_analysis=website_section,
            value_proposition=value_prop.strip(),
            portfolio=portfolio,
            call_to_action=cta,
            sender_name=self.sender_name,
            sender_company=self.sender_company,
            sender_contacts=self.sender_contacts,
        )

        # Clean up extra whitespace
        content = "\n".join(line for line in content.split("\n") if line.strip() or line == "")
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

        # Add custom notes if provided
        if custom_notes:
            content = content.replace("{custom_notes}", custom_notes)

        # Generate subject for email
        subject = self.generate_subject(lead, project_type) if channel == ProposalChannel.EMAIL else None

        # Collect personalization data
        personalization_data = {
            "project_type": project_type,
            "source_type": source_type,
            "lead_industry": lead.industry,
            "tone": tone,
        }

        # Collect issues mentioned
        website_issues = []
        if website_analysis and website_analysis.issues:
            website_issues = [issue.get("description") for issue in website_analysis.issues[:3]]

        # Suggested solutions
        suggested_solutions = []
        if website_analysis and website_analysis.improvement_suggestions:
            suggested_solutions = website_analysis.improvement_suggestions[:3]

        # Portfolio examples used
        portfolio_examples = self.PORTFOLIO_EXAMPLES.get(
            lead.industry,
            self.PORTFOLIO_EXAMPLES["default"]
        ) if include_portfolio else []

        # Create proposal record
        proposal = Proposal(
            lead_id=lead_id,
            subject=subject,
            content=content,
            channel=channel,
            status=ProposalStatus.READY,
            personalization_data=personalization_data,
            website_issues=website_issues,
            suggested_solutions=suggested_solutions,
            portfolio_examples=portfolio_examples,
        )

        self.db.add(proposal)
        await self.db.commit()
        await self.db.refresh(proposal)

        return proposal

    async def generate_proposal_with_ai(
        self,
        lead_id: int,
        channel: ProposalChannel = ProposalChannel.EMAIL,
        tone: str = "professional",
        custom_instructions: Optional[str] = None,
    ) -> Proposal:
        """Generate a proposal using AI for more personalized content."""
        # Check if any AI provider is available
        if not ai_service.is_available():
            # Fallback to template-based generation
            return await self.generate_proposal(lead_id, channel, tone)

        # Get lead with website analysis
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Get website analysis
        website_analysis = None
        if lead.website:
            wa_result = await self.db.execute(
                select(WebsiteAnalysis).where(WebsiteAnalysis.lead_id == lead_id)
            )
            website_analysis = wa_result.scalar_one_or_none()

        # Prepare context for AI
        context = {
            "lead_name": lead.name,
            "company": lead.company_name,
            "industry": lead.industry,
            "original_request": lead.original_request,
            "needs": lead.needs_description,
            "budget": lead.budget_mentioned,
            "urgency": lead.urgency,
            "website": lead.website,
            "website_issues": website_analysis.issues if website_analysis else None,
            "website_score": website_analysis.overall_score if website_analysis else None,
        }

        tone_instructions = {
            "professional": "Используй профессиональный, деловой тон.",
            "friendly": "Используй дружелюбный, но профессиональный тон.",
            "casual": "Используй неформальный, разговорный тон.",
        }

        channel_instructions = {
            ProposalChannel.EMAIL: "Это email-письмо. Добавь тему письма. Формат: более формальный, структурированный.",
            ProposalChannel.TELEGRAM: "Это сообщение в Telegram. Короче, без лишних формальностей, с эмодзи если уместно.",
        }

        prompt = f"""Создай персонализированное предложение для потенциального клиента веб-студии.

Информация о клиенте:
{json.dumps(context, ensure_ascii=False, indent=2)}

Требования:
- {tone_instructions.get(tone, tone_instructions['professional'])}
- {channel_instructions.get(channel, '')}
- Обращайся на "вы"
- Упомяни конкретные проблемы их сайта если есть
- Предложи конкретное решение
- Добавь призыв к действию
{f'- Дополнительные инструкции: {custom_instructions}' if custom_instructions else ''}

Ответь ТОЛЬКО в формате JSON (без markdown, без ```):
{{
    "subject": "тема письма (только для email)",
    "content": "текст предложения",
    "key_points": ["ключевой момент 1", "ключевой момент 2"],
    "call_to_action": "призыв к действию"
}}
"""

        system_prompt = "Ты - опытный менеджер по продажам веб-студии. Создаёшь персонализированные, убедительные предложения. Отвечай ТОЛЬКО валидным JSON."

        try:
            ai_result = await ai_service.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                fallback_value=None,
            )

            if not ai_result:
                # AI failed, fallback to template
                return await self.generate_proposal(lead_id, channel, tone)

            proposal = Proposal(
                lead_id=lead_id,
                subject=ai_result.get("subject"),
                content=ai_result.get("content"),
                channel=channel,
                status=ProposalStatus.READY,
                personalization_data={
                    "ai_generated": True,
                    "tone": tone,
                    "key_points": ai_result.get("key_points"),
                },
                website_issues=website_analysis.issues[:3] if website_analysis and website_analysis.issues else None,
            )

            self.db.add(proposal)
            await self.db.commit()
            await self.db.refresh(proposal)

            return proposal

        except Exception as e:
            print(f"AI proposal generation failed: {e}")
            # Fallback to template-based
            return await self.generate_proposal(lead_id, channel, tone)

    async def get_proposals_for_lead(self, lead_id: int) -> list[Proposal]:
        """Get all proposals for a lead."""
        result = await self.db.execute(
            select(Proposal)
            .where(Proposal.lead_id == lead_id)
            .order_by(Proposal.created_at.desc())
        )
        return result.scalars().all()

    async def mark_proposal_sent(self, proposal_id: int) -> Proposal:
        """Mark a proposal as sent."""
        result = await self.db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal.status = ProposalStatus.SENT
        proposal.sent_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(proposal)

        return proposal
