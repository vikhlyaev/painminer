# Painminer

Локальный Python CLI инструмент, который извлекает повторяющиеся утверждения о "боли пользователей" из выбранных subreddit-ов Reddit, группирует их по намерениям и выводит идеи небольших iOS приложений (1-3 основные функции).

## Возможности

- **Интеграция с Reddit**: Использует официальный API Reddit через PRAW (учетные данные OAuth приложения)
- **Извлечение проблем**: Обнаруживает утверждения о боли/фрустрации с помощью настраиваемого поиска фраз
- **Умная кластеризация**: Группирует похожие утверждения о проблемах, используя TF-IDF + KMeans или простые hash-методы
- **Фильтр основного объема**: Фильтрует идеи для фокуса на простых, локальных iOS приложениях
- **Генерация идей**: Производит действенные идеи приложений с основными функциями, экранами и сложностью MVP
- **Кеширование файлов**: Кеширует данные Reddit, чтобы избежать повторных вызовов API
- **Воспроизводимый вывод**: Детерминированные результаты при одинаковой конфигурации

## Установка

### Требования

- Python 3.11+
- Учетные данные Reddit API (см. ниже)

### Установка зависимостей

```bash
# Клонирование или загрузка репозитория
cd painminer

# Создание виртуального окружения (рекомендуется)
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установка пакета
pip install -e .

# Или установка зависимостей напрямую
pip install praw httpx pyyaml scikit-learn pydantic
```

### Установка для разработки

```bash
pip install -e ".[dev]"
```

## Настройка учетных данных Reddit API

1. Перейдите на https://www.reddit.com/prefs/apps
2. Нажмите "Create App" или "Create Another App"
3. Заполните детали:
   - **name**: painminer (или любое имя)
   - **App type**: Выберите "script"
   - **description**: Инструмент для личных исследований
   - **about url**: (оставьте пустым)
   - **redirect uri**: http://localhost:8080
4. Нажмите "Create app"
5. Запишите:
   - **client_id**: Строка под "personal use script"
   - **client_secret**: Показанный секрет

### Установка переменных окружения

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USERNAME="your_reddit_username"
export REDDIT_PASSWORD="your_reddit_password"
```

Или создайте файл `.env` и подключите его:

```bash
# файл .env
export REDDIT_CLIENT_ID="abc123"
export REDDIT_CLIENT_SECRET="xyz789"
export REDDIT_USERNAME="myusername"
export REDDIT_PASSWORD="mypassword"
```

```bash
source .env
```

## Использование

### Базовое использование

```bash
# Запуск с образцовой конфигурацией по умолчанию, вывод в Markdown
python -m painminer run --config sample_config.yaml --out out.md

# Запуск с выводом в JSON
python -m painminer run --config sample_config.yaml --out report.json

# Запуск без кеша (повторная загрузка всех данных)
python -m painminer run --config config.yaml --out out.md --no-cache

# Подробный вывод
python -m painminer run --config config.yaml --out out.md --verbose
```

### Управление кешем

```bash
# Показать статистику кеша
python -m painminer cache --stats

# Очистить все кешированные данные
python -m painminer cache --clear
```

### Справка

```bash
python -m painminer --help
python -m painminer run --help
```

### Веб-интерфейс

Painminer включает современный веб-интерфейс, построенный с помощью Next.js и Tailwind CSS.

```bash
# Запуск API сервера (из корня проекта)
uvicorn painminer.api:app --reload --host 0.0.0.0 --port 8000

# В другом терминале запуск веб-интерфейса
cd web
npm install
npm run dev
```

Затем откройте [http://localhost:3000](http://localhost:3000) в вашем браузере.

См. [web/README.md](web/README.md) для более подробной информации.

## Конфигурация

Инструмент настраивается через YAML файл. См. `sample_config.yaml` для полного примера.

### Ключевые разделы конфигурации

#### Subreddit-ы

```yaml
subreddits:
  - name: "ADHD"
    period_days: 30      # Просмотреть назад на это количество дней
    min_upvotes: 10      # Минимальный рейтинг поста
    max_posts: 200       # Максимальное количество постов для загрузки
    max_comments_per_post: 50  # Комментариев на пост
```

#### Учетные данные Reddit

```yaml
reddit:
  client_id: "${REDDIT_CLIENT_ID}"
  client_secret: "${REDDIT_CLIENT_SECRET}"
  username: "${REDDIT_USERNAME}"
  password: "${REDDIT_PASSWORD}"
  user_agent: "painminer/0.1 (personal research)"
```

#### Фильтры

```yaml
filters:
  include_phrases:
    - "I struggle"
    - "I keep forgetting"
    - "I wish"
    - "How do you"
    - "Is there an app"
  exclude_phrases:
    - "politics"
    - "rant"
  min_pain_length: 12
```

#### Кластеризация

```yaml
clustering:
  method: "tfidf_kmeans"  # или "simple_hash"
  k_min: 5
  k_max: 20
  random_state: 42        # Для воспроизводимости
```

#### Фильтр основного объема

```yaml
core_filter:
  reject_if:
    requires_social_network: true
    requires_marketplace: true
    requires_realtime_sync: true
    requires_ai_for_value: true
  accept_if:
    solvable_locally: true
    max_screens: 3
    max_user_actions: 3
```

## Примеры вывода

### Markdown отчет

```markdown
# Отчет Painminer

_Создан: 2025-01-20 12:00:00 UTC_

## Сводка конфигурации

### Subreddit-ы
- **r/ADHD**: 30 дней, минимум 10 лайков, максимум 200 постов
- **r/productivity**: 30 дней, минимум 15 лайков, максимум 150 постов

---

## Топ кластеров проблем

### #1: FocusConcentration

- **Количество**: 45 утверждений о проблемах
- **Средний рейтинг**: 32.5
- **Общий рейтинг**: 1462

**Примеры:**
1. _мне сложно сохранять фокус на работе более 20 минут_
2. _концентрироваться на задачах очень сложно, когда есть отвлекающие факторы_
3. _я постоянно теряю фокус и не знаю, как вернуться на правильный путь_

---

## Кандидаты идей iOS приложений

### #1: FocusTimer

**Сложность**: S

**Проблема**: Пользователи сообщают: "мне сложно сохранять фокус на работе..."

**Целевой пользователь**: Люди, интересующиеся темами ADHD, продуктивности, которым нужен функционал таймера

**Основные функции**:
- Запуск/остановка обратного отсчета или секундомера
- Сохранение предустановок таймера для быстрого доступа
- Фоновый таймер с уведомлениями

**Экраны**:
- TimerView
- Presets

**Локальные данные**:
- Предустановки таймера
- История сеансов

**Свидетельства из Reddit**:
- 45 упоминаний
- Средний рейтинг: 32.5
```

### JSON отчет

```json
{
  "generated_at": "2025-01-20T12:00:00",
  "statistics": {
    "total_clusters": 15,
    "feasible_ideas": 8,
    "subreddits_analyzed": 3
  },
  "ideas": [
    {
      "idea_name": "FocusTimer",
      "problem_statement": "Пользователи сообщают: \"мне сложно сохранять фокус...\"",
      "target_user": "Люди, интересующиеся темами ADHD...",
      "core_functions": ["Запуск/остановка обратного отсчета...", "..."],
      "screens": ["TimerView", "Presets"],
      "mvp_complexity": "S",
      "reddit_evidence": {
        "count": 45,
        "avg_score": 32.5
      }
    }
  ]
}
```

## Запуск тестов

```bash
# Установка зависимостей для разработки
pip install -e ".[dev]"

# Запуск всех тестов
pytest

# Запуск с покрытием кода
pytest --cov=painminer

# Запуск конкретного тестового файла
pytest tests/test_extract.py -v
```

## Структура проекта

```
painminer/
├── __init__.py         # Инициализация пакета
├── __main__.py         # Точка входа для python -m
├── cli.py              # Интерфейс командной строки
├── config.py           # Загрузка и валидация конфигурации
├── models.py           # Модели данных (PainItem, Cluster, AppIdea, и т.д.)
├── network.py          # Сетевые утилиты, поддержка прокси, троттлинг
├── cache.py            # Файловое кеширование
├── utils.py            # Вспомогательные функции
├── reddit_client.py    # Клиент Reddit API с использованием PRAW
├── extract.py          # Извлечение утверждений о проблемах
├── cluster.py          # Алгоритмы кластеризации
├── core_filter.py      # Фильтрация основного объема
├── ideas.py            # Генерация идей приложений
└── output.py           # Генераторы Markdown и JSON отчетов

tests/
├── __init__.py
├── test_extract.py     # Тесты извлечения
├── test_cluster.py     # Тесты кластеризации
└── test_core_filter.py # Тесты фильтрации
```

## Ограничения частоты запросов и хорошие манеры

Этот инструмент соблюдает рекомендации API Reddit:

- **Троттлинг**: Настраиваемые задержки между запросами (по умолчанию: 800-2500мс)
- **Повторные попытки**: Экспоненциальная отсрочка при сбоях
- **Кеширование**: Результаты кешируются для минимизации повторных вызовов API
- **User Agent**: Идентифицируется как инструмент для личных исследований

Пожалуйста:
- Не уменьшайте задержки ниже рекомендуемых минимумов
- Используйте кеширование, чтобы избежать ненужных вызовов API
- Не запускайте инструмент чрезмерно часто
- Соблюдайте условия обслуживания Reddit

## Устранение неполадок

### Ошибка "Environment variable not set"

Убедитесь, что вы экспортировали все необходимые переменные окружения:

```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USERNAME="..."
export REDDIT_PASSWORD="..."
```

### Ошибка "Authentication failed"

- Убедитесь, что ваше приложение Reddit имеет тип "script"
- Проверьте правильность имени пользователя и пароля
- Убедитесь, что приложение авторизовано для вашего аккаунта

### Предупреждение "No pain statements extracted"

- Проверьте конфигурацию `include_phrases`
- Уменьшите `min_pain_length`, если утверждения слишком короткие
- Убедитесь в правильности имен subreddit-ов

### Ошибки "Rate limited"

- Увеличьте `min_delay_ms` и `max_delay_ms`
- Уменьшите `max_posts` на subreddit
- Подождите и попробуйте снова позже

## Лицензия

Лицензия MIT - только для личного исследования.

## Отказ от ответственности

Этот инструмент предназначен только для личных исследований. Используйте ответственно и в соответствии с условиями обслуживания Reddit. Сгенерированные идеи приложений являются предложениями, основанными на наблюдаемых паттернах, и должны быть подтверждены дополнительными исследованиями.
