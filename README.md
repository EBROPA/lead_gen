# Lead Generation System

Автоматическая система поиска и квалификации лидов для веб-студий и фрилансеров.

## Возможности

- **Автоматический поиск лидов** из множества источников:
  - Telegram-каналы (freelance, web development)
  - Фриланс-биржи (FL.ru, Kwork, Habr Freelance)
  - Доски объявлений (Avito)
  - Форумы

- **Квалификация лидов** с использованием AI и правил:
  - Оценка бюджета
  - Определение срочности
  - Выявление отрасли бизнеса
  - Фильтрация спама и неподходящих запросов

- **Анализ сайтов** потенциальных клиентов:
  - Проверка SSL
  - Оценка скорости загрузки
  - Адаптивность под мобильные устройства
  - SEO-анализ
  - Выявление проблем и рекомендации

- **Генерация персонализированных предложений**:
  - Адаптация под канал коммуникации (email, Telegram)
  - Учёт анализа сайта
  - Релевантные примеры из портфолио

- **Веб-интерфейс** для управления:
  - Dashboard со статистикой
  - Управление лидами
  - Настройка источников
  - Генерация предложений

## Архитектура

```
lead_gen/
├── app/
│   ├── api/              # REST API endpoints
│   ├── models/           # SQLAlchemy models
│   ├── parsers/          # Parsers for different sources
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── templates/        # HTML templates
├── tests/                # Unit and integration tests
├── static/               # Static files
└── requirements.txt
```

### Компоненты

1. **LeadFinder** - поиск лидов из различных источников
2. **WebsiteAnalyzer** - анализ сайтов клиентов
3. **LeadQualifier** - квалификация и скоринг лидов
4. **ProposalGenerator** - генерация персонализированных предложений
5. **AIService** - унифицированный сервис для работы с бесплатными AI провайдерами (Gemini, Groq, OpenRouter, Ollama)
6. **REST API** - FastAPI endpoints
7. **Web UI** - интерфейс управления

## Быстрый старт

### Требования

- Python 3.11+
- pip

### Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd lead_gen

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Копирование конфигурации
cp .env.example .env

# Редактирование конфигурации (опционально)
# nano .env
```

### Запуск

```bash
# Запуск приложения
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Docker

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

## Конфигурация

Основные переменные окружения (`.env`):

```env
# База данных
DATABASE_URL=sqlite+aiosqlite:///./lead_gen.db

# ========== AI ПРОВАЙДЕРЫ (бесплатные) ==========
# Выберите один или несколько. Система автоматически использует доступный.

# Google Gemini (РЕКОМЕНДУЕТСЯ - 60 запросов/мин бесплатно)
# Получить ключ: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash

# Groq (ОЧЕНЬ БЫСТРЫЙ - щедрый бесплатный tier)
# Получить ключ: https://console.groq.com/keys
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant

# OpenRouter (МНОГО МОДЕЛЕЙ - $5 бесплатно при регистрации)
# Получить ключ: https://openrouter.ai/keys
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free

# Ollama (ЛОКАЛЬНО - полностью бесплатно)
# Установка: https://ollama.ai
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Настройки поиска
SEARCH_INTERVAL_MINUTES=60
MAX_LEADS_PER_SEARCH=50
```

### Получение бесплатных API ключей

| Провайдер | Лимиты | Как получить |
|-----------|--------|--------------|
| **Google Gemini** | 60 req/min | [aistudio.google.com](https://aistudio.google.com/app/apikey) - войти через Google |
| **Groq** | 30 req/min | [console.groq.com](https://console.groq.com/keys) - регистрация |
| **OpenRouter** | $5 кредит | [openrouter.ai](https://openrouter.ai/keys) - регистрация |
| **Ollama** | Безлимит | [ollama.ai](https://ollama.ai) - установить локально |

## API

### Leads

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/leads` | Список лидов с фильтрацией |
| GET | `/api/leads/hot` | Горячие лиды |
| GET | `/api/leads/stats` | Статистика |
| GET | `/api/leads/{id}` | Получить лид |
| POST | `/api/leads` | Создать лид |
| PATCH | `/api/leads/{id}` | Обновить лид |
| DELETE | `/api/leads/{id}` | Удалить лид |
| POST | `/api/leads/{id}/qualify` | Квалифицировать лид |
| POST | `/api/leads/{id}/analyze-website` | Анализ сайта |

### Sources

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/sources` | Список источников |
| POST | `/api/sources` | Создать источник |
| PATCH | `/api/sources/{id}` | Обновить источник |
| POST | `/api/sources/{id}/toggle` | Вкл/выкл источник |

### Proposals

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/proposals` | Список предложений |
| POST | `/api/proposals/generate` | Генерация предложения |
| POST | `/api/proposals/{id}/mark-sent` | Отметить как отправленное |

### Search

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/search/run` | Запустить поиск |
| GET | `/api/search/stats` | Статистика поиска |

## Добавление нового источника

1. Создайте парсер в `app/parsers/`:

```python
from app.parsers.base import BaseParser, ParsedLead

class MyParser(BaseParser):
    def get_source_name(self) -> str:
        return "My Source"

    def get_source_type(self) -> str:
        return "custom"

    async def search(self, max_results: int = 50):
        # Логика поиска
        for item in items:
            yield ParsedLead(
                name=item.name,
                source_url=item.url,
                original_request=item.text,
                email=self.extract_email(item.text),
                telegram=self.extract_telegram(item.text),
            )
```

2. Зарегистрируйте парсер в `app/services/lead_finder.py`:

```python
PARSER_REGISTRY = {
    ...
    SourceType.CUSTOM: MyParser,
}
```

## Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Конкретный файл
pytest tests/test_qualifier.py -v
```

## Структура базы данных

### Lead (Лид)

- `id` - идентификатор
- `name` - имя контакта
- `company_name` - название компании
- `email`, `phone`, `telegram` - контакты
- `website` - сайт
- `original_request` - исходный запрос
- `needs_description` - описание потребностей
- `budget_mentioned` - упомянутый бюджет
- `urgency` - срочность
- `qualification_score` - общий скор (0-100)
- `status` - статус в воронке

### Source (Источник)

- `id` - идентификатор
- `name` - название
- `source_type` - тип источника
- `is_active` - активен ли
- `search_keywords` - ключевые слова для поиска

### Proposal (Предложение)

- `id` - идентификатор
- `lead_id` - связь с лидом
- `subject` - тема (для email)
- `content` - текст предложения
- `channel` - канал (email, telegram)
- `status` - статус (draft, ready, sent)

### WebsiteAnalysis (Анализ сайта)

- `id` - идентификатор
- `lead_id` - связь с лидом
- `overall_score` - общая оценка
- `issues` - найденные проблемы
- `improvement_suggestions` - рекомендации

## Лицензия

MIT

## Контакты

При возникновении вопросов создайте issue в репозитории.
