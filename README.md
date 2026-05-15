# Local Job Application Assistant

Локальное приложение для создания резюме, адаптации резюме под конкретные вакансии с помощью AI и подготовки финальных документов PDF/DOCX.

Проект проходит архитектурный reset.

Старая идея “профиль как YAML/Markdown файлы” больше не является целевой. Новая цель — SQL-first Resume Builder.

---

## Простое объяснение

Программа нужна, чтобы пройти путь:

```text
Создать профиль человека
→ создать одно или несколько резюме
→ вставить текст вакансии
→ выбрать профиль и резюме
→ AI предложит изменения только в разрешённых блоках
→ пользователь проверит before/after с возможностью коррекции предложенных ИИ изменений
→ пользователь примет или отклонит изменения
→ программа соберёт финальное резюме с контактными данными
→ export PDF/DOCX
```

Главный смысл: не писать новое CV с нуля под каждую вакансию, а управляемо и проверяемо адаптировать существующее резюме под требования и ключевые слова вакансии.

---

## Что программа НЕ должна делать

Программа не должна:

- автоматически подаваться на вакансии;
- автоматизировать LinkedIn;
- отправлять email без пользователя;
- массово парсить сайты вакансий;
- выдумывать опыт как подтверждённый факт;
- хранить OpenAI API key в SQLite;
- отправлять приватные контактные данные в AI prompt.

---

## Новая целевая модель

### 1. Профили

Профиль — это человек.

Примеры:

```text
Alex
Luda
Another Person
```

У каждого профиля есть:

- контактные данные;
- приватный слой данных;
- facts/evidence;
- набор резюме;
- история заявок;
- generated artefacts.

Контактные данные не должны попадать в AI prompt. Они добавляются только на финальном этапе export.

---

### 2. Резюме

У одного профиля может быть несколько резюме:

```text
Alex
├── Software Engineer
├── Backend Developer
├── Automation Engineer
└── Data Analyst
```

Каждое резюме — это конструктор из секций, блоков и bullet points, которые хранятся в SQLite.

YAML и Markdown не должны быть основным источником данных и должны быть удалены из настроек пользователя как устаревшая модель (это не распространяется на данный тип файлов, если они труебуются для ран-тайм)

---

### 3. Секции и блоки

Типовые секции:

- Summary;
- Skills;
- Work Experience;
- Education;
- Certifications;
- Languages;
- References;
- Custom sections.

Пользователь должен уметь:

- создавать секции;
- создавать custom sections;
- менять порядок секций;
- менять порядок блоков;
- включать/выключать блоки;
- указывать, какие блоки может менять AI;
- создавать разные версии резюме.

---

### 4. Что может менять AI

AI не должен менять всё резюме одним большим текстом.

AI работает по блокам и отдельным prompts.

| Область | Что редактирует AI |
|---|---|
| Summary | весь блок |
| Resume title / Job title | всё название, если разрешено |
| Skills | весь набор skills |
| Work Experience | отдельные bullets |
| Education | обычно не редактируется |
| Certifications | обычно не редактируется |
| Languages | обычно не редактируется |
| References | обычно не редактируется |

Для каждого блока можно настроить:

- можно ли AI переписывать;
- можно ли AI добавлять bullet;
- можно ли AI скрывать нерелевантный bullet;
- обязательно ли связывать bullet с fact;
- какой prompt использовать.

---

### 5. Facts

Facts — это проверяемые утверждения о человеке.

Пример:

```text
Used Python in backend projects.
Built FastAPI services.
Worked with SQL databases.
Used GitHub Actions.
```

Facts должны храниться в SQL.

Каждый bullet может быть связан с одним или несколькими facts.

Связь bullet → fact может быть обязательной или необязательной в зависимости от настройки.

По умолчанию принцип такой:

```text
Нет verified fact → AI не должен усиливать claim как подтверждённый опыт.
```

---

### 6. Вакансии и заявки

Страница новой заявки должна иметь:

1. выбор профиля;
2. выбор резюме из этого профиля;
3. поле для текста вакансии.

Поток:

```text
New Application
→ choose profile
→ choose resume
→ paste job text
→ extract requirements
→ propose resume changes
→ review changes
→ export final documents
```

История заявок хранится по профилю.

---

### 7. AI tailoring

AI должен предлагать изменения, а не сразу переписывать резюме окончательно.

Каждое предложение изменения должно хранить:

- какой блок меняется;
- старый текст;
- новый текст;
- причину;
- связанные требования вакансии;
- связанные facts;
- уровень риска;
- статус: proposed, accepted, rejected.

Review page должна показывать before/after.

Git-like diff желателен, но на первом этапе достаточно простого сравнения старого и нового текста.

---

### 8. Cover letter

Cover letter — отдельный поток.

Программа должна создавать сопроводительное письмо по описанию вакансии и выбранному резюме на основе промпта созданного специально для написания этого потока.

Cover letter:

- создаётся отдельным prompt;
- хранится отдельно от CV;
- редактируется пользователем;
- экспортируется или сохраняется как artefact;
- не должен выдумывать опыт.

---

### 9. Export

На первом этапе нужен один простой стиль PDF/DOCX.

Красивое форматирование, несколько templates и сложная типографика — позже.

Финальный export собирает:

```text
approved tailored resume content
+ private contact layer
→ PDF/DOCX/HTML/Markdown
```

---

## Архитектура

Целевая архитектура:

```text
app/
├── api/              # тонкие FastAPI routes
├── storage/          # app data folder
├── secrets/          # OS keyring для OpenAI API key
├── settings/         # app settings без YAML
├── profiles/         # profiles/persons
├── resumes/          # resumes, sections, blocks, bullets
├── facts/            # verified facts and evidence
├── applications/     # job applications and history
├── ai/               # prompt registry, clients, structured outputs
├── tailoring/        # AI change proposal flow
├── cover_letters/    # cover letter flow
├── exporters/        # PDF/DOCX/HTML/Markdown
├── artifacts/        # file writing and safe downloads
└── web/              # Jinja2 templates
```

Правило слоёв:

```text
routes → services/use cases → repositories → SQL models
routes → services/use cases → AI clients/prompts
routes → services/use cases → exporters/artifacts
```

---

## Что можно сохранить из старой реализации

Можно переиспользовать:

- FastAPI/Jinja2 каркас;
- SQLite;
- app data folder;
- OS keyring;
- exporters;
- artifact writer;
- safe download logic;
- test infrastructure;
- CI/ruff/pre-commit;
- часть settings/setup shell.

Нужно удалить или радикально переписать:

- YAML settings;
- YAML fact bank;
- Markdown CV as source of truth;
- старые import tools;
- old file-based profile assumptions;
- старую pipeline source loading модель;
- fake tailor как основной tailoring mechanism.

---

## Первый запуск после перестройки

Целевой first-run flow:

```text
Open app
→ choose/create app data folder
→ enter OpenAI key or choose fake/demo mode
→ create profile
→ create first resume
→ add sections, blocks, bullets, facts
→ create first application
→ run AI tailoring
→ review before/after
→ export final CV
```

---

## Запуск проекта для разработки

Технические команды могут остаться такими:

```powershell
uv sync --locked --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```

Запуск приложения:

```powershell
uv run uvicorn app.main:app --reload
```

После архитектурной перестройки приложение не должно требовать YAML config для старта.

---

## OpenAI key

OpenAI API key должен вводиться через Settings UI.

Raw key:

- не хранится в SQLite;
- не выводится в HTML;
- не пишется в logs;
- хранится через OS keyring.

Для тестов использовать fake/mocked AI clients.

Тесты не должны вызывать реальный OpenAI API.

---

## UI direction

Интерфейс должен стать современнее старого прототипа.

Минимально:

- понятная навигация;
- карточки;
- таблицы;
- нормальные формы;
- визуальные статусы;
- before/after review;
- понятные action buttons;
- аккуратные empty states.

Язык интерфейса на первом этапе — английский.

Русскую локализацию можно предусмотреть, но не делать сейчас.

---

## Roadmap

### Phase 0 — Architecture reset docs

Создать документы под SQL-first Resume Builder.

### Phase 1 — SQL domain model

Создать модели для profiles, resumes, sections, blocks, bullets, facts, AI policies, applications, change proposals.

### Phase 2 — Settings without YAML

Настройки через UI и SQLite, OpenAI key через keyring.

### Phase 3 — Profile manager

Создание профилей разных людей.

### Phase 4 — Resume builder

Создание резюме, секций, блоков, bullets, facts и AI policies.

### Phase 5 — Application intake

Выбор profile + resume + вставка текста вакансии.

### Phase 6 — AI structured tailoring

Prompt per block type, structured change proposals.

### Phase 7 — Review page

Before/after, accept/reject, сохранение решений.

### Phase 8 — Final export

Approved content + private contact layer → PDF/DOCX/HTML/Markdown.

### Phase 9 — Cover letters

Отдельный prompt, draft, review, edit, save/export.

### Phase 10 — Release smoke tests

Проверить полный user journey без YAML.

---

## Текущий статус

Проект пока не является готовым продуктом.

Текущий код нужно рассматривать как инфраструктурную заготовку, которую нужно радикально перестроить в SQL-first Resume Builder.

Главная цель следующего этапа:

```text
Полностью переработать структуру программы согласно указанным требованиям в документах README, AGENTS, SESSION_NOTES. 
```
