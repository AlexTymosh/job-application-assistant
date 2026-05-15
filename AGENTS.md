# AGENTS.md

Инструкции для Codex, ChatGPT, QA-агентов и других помощников, работающих над проектом `job-application-assistant`.

Этот файл фиксирует стабильные правила проекта после архитектурного разворота: от YAML/Markdown-first инструмента к SQL-first Resume Builder + AI Tailoring системе.

---

## 1. Перед началом любой задачи

Всегда сначала прочитать:

1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. `README.md`, если задача влияет на продукт, UI, пользовательские сценарии или документацию
4. файлы, напрямую связанные с текущей задачей

Если документация противоречит фактическому коду, брать за истину только три файла: `AGENTS.md`, `SESSION_NOTES.md`, `README.md`.

Если пользовательская задача противоречит этому файлу, текущая инструкция пользователя выше по приоритету
Для случаев, где это ломает безопасность, приватность или целостность репозитория необходимо сделать отдельные комментарии.

---

## 2. Назначение проекта

`job-application-assistant` — локальное FastAPI/Jinja2 приложение для создания, ведения и адаптации резюме под конкретные вакансии.

Целевой продуктовый поток:

```text
Профиль человека
→ конструктор резюме
→ вставка текста вакансии
→ AI-анализ требований
→ AI-предложения изменений по разрешённым блокам
→ review before/after
→ принятие/отклонение изменений
→ финальный export PDF/DOCX/HTML/Markdown
→ история заявок
```

Приложение не является auto-apply ботом.

Приложение не должно автоматически подавать заявки, автоматизировать LinkedIn, отправлять email, выполнять массовый scraping сайтов вакансий или действовать от имени пользователя без явного действия пользователя.

---

## 3. Главный архитектурный разворот

Старая модель `YAML/Markdown profile as source of truth` больше не является целевой.

Новая модель:

```text
SQLite is the source of truth.
```

Удалить из пользовательской модели:

- YAML как хранилище настроек;
- YAML как хранилище fact bank;
- Markdown как основной источник резюме;
- старую import-first архитектуру;
- зависимость pipeline от file-based profile как основного пути.

Сохранить как техническую инфраструктуру, если полезно:

- FastAPI/Jinja2;
- SQLite;
- app data folder;
- OS keyring для OpenAI API key;
- exporters PDF/DOCX/HTML/Markdown;
- artefact writer/download safety;
- тестовую инфраструктуру;
- CI/ruff/pre-commit;
- часть существующего UI shell, если его проще переиспользовать.

Не нужно поддерживать импорт старых Markdown/YAML CV, потому что программой ещё никто не пользовался и миграционные обязательства отсутствуют.


---

## 4. Product model

### 4.1 Person Profile

Профиль — это человек, например Alex, Luda или другой пользователь.

Профиль содержит:

- имя профиля;
- отображаемое имя;
- приватный слой контактных данных;
- ссылки;
- location;
- work authorisation, если нужно;
- языки;
- глобальные verified facts;
- набор резюме;
- историю заявок;
- generated artefacts.

У приложения может быть несколько профилей для разных людей.
Профили должны создаваться в настройках программы.

### 4.2 Resume

Один профиль может иметь несколько резюме, напрмиер:

```text
Profile: Alex
├── Software Engineer
├── Backend Developer
├── Automation Engineer
└── Data Analyst
```

Резюме — это не Markdown-файл. Это SQL-сущность с секциями, блоками, bullet points, настройками AI-редактирования и порядком отображения.

### 4.3 Resume sections and blocks

Резюме должно работать как конструктор.

Типовые секции:

- Personal details layer;
- Summary;
- Skills;
- Work Experience;
- Projects;
- Education;
- Certifications;
- Languages;
- References;
- Custom sections.

Пользователь должен уметь:

- создавать резюме;
- создавать секции;
- создавать блоки внутри секций;
- менять порядок секций и блоков;
- включать/выключать секции и блоки;
- задавать, какие блоки может менять AI;
- создавать разные версии резюме под разные роли.

---

## 5. Единицы AI-редактирования

AI не должен получать всё резюме как бесформенный текст.

AI должен работать по блочной модели, подобно тому, как формируется резюме на сайте при подаче заявки на вакансию в компании.

Для каждого типа блока должен быть отдельный prompt/policy.

Базовые единицы редактирования:

| Тип блока | Единица редактирования |
|---|---|
| Summary / Description | весь блок |
| Job title / resume title | всё название |
| Skills | весь набор skills |
| Work Experience | отдельный bullet |
| Projects | отдельный bullet или описание проекта, по настройке блока |
| Education | обычно не редактируется AI, если пользователь явно не разрешил |
| Certifications | обычно не редактируется AI |
| Languages | обычно не редактируется AI |
| References | обычно не редактируется AI |
| Custom section | по policy конкретного блока |

AI может менять job title, если пользователь разрешил это для конкретного title/resume/title field.

Не требуется автоматическое сокращение CV до 1–2 страниц.

---

## 6. AI edit policy

Для каждого блока или поля нужна политика редактирования.

Минимальные настройки:

- `ai_editable`: может ли AI менять блок;
- `ai_can_rewrite`: может ли AI переписывать текст;
- `ai_can_add`: может ли AI добавлять новый bullet/content;
- `ai_can_hide`: может ли AI предложить скрыть нерелевантный bullet/block;
- `fact_link_required`: должен ли каждый новый/изменённый bullet иметь `fact_id`;
- `prompt_key`: какой prompt использовать для этого блока;
- `review_required`: изменения требуют review перед export.

Удаление/скрытие bullet должно быть опциональным и проходить через review.

---

## 7. Facts and evidence

Факты хранятся в SQL, а не в YAML.

Факт описывает проверяемое утверждение о человеке:

```text
Fact
├── profile_id
├── title/name
├── category
├── evidence
├── source/note
├── allowed_claim_level
├── is_verified
└── is_active
```

Каждый bullet может быть связан с одним или несколькими facts.

Связь bullet → fact должна быть опционально обязательной через настройку `fact_link_required`.

По умолчанию продукт должен быть conservative:

```text
Нет verified fact → AI не должен усиливать claim как подтверждённый опыт.
```

Если пользователь отключил обязательную связь с facts, AI всё равно должен маркировать unsupported/risky suggestions как рискованные и показывать их на review page.

---

## 8. Приватный слой резюме

Контактные данные и приватная идентификационная информация не должны попадать в AI prompt.

Приватный слой включает:

- phone;
- email;
- address;
- private links;
- date of birth, если когда-либо будет добавлено;
- любые sensitive/private notes.

AI должен получать только тот слой, который нужен для tailoring:

```text
AI-safe resume content
+ editable blocks
+ allowed facts
+ job requirements
```

Финальный export собирается так:

```text
private contact layer
+ approved tailored resume content
+ selected export format
→ final document
```

---

## 9. Application flow

Страница вставки вакансии должна требовать выбор:

1. профиля;
2. резюме внутри этого профиля;
3. текста вакансии.

Поток:

```text
New Application
→ choose profile
→ choose resume
→ paste job text
→ extract job requirements
→ propose AI changes
→ review before/after
→ accept/reject changes
→ create cover letter
→ export final documents
```

История заявок должна храниться по профилю.

---

## 10. AI tailoring flow

AI должен возвращать structured changes, а не готовый бесконтрольный Markdown.

Минимальная структура change proposal:

```json
{
  "target_id": "resume_bullet_id_or_block_id",
  "target_type": "work_experience_bullet",
  "before_text": "Old bullet",
  "after_text": "New bullet",
  "reason": "Matches backend API requirement",
  "job_requirement_ids": ["req_1"],
  "fact_ids": ["fact_1"],
  "risk_level": "low",
  "warning_codes": []
}
```

Review page должна показывать before/after обязательно.

Git-like diff желателен, но может быть отложен, если на первом этапе будет простое сравнение old/new.

Accepted/rejected AI changes должны сохраняться в базе.

---

## 11. Cover letter

Сопроводительное письмо должно быть отдельной сущностью.

Поток:

```text
Application
→ selected profile
→ selected resume
→ job requirements
→ cover letter prompt
→ generated cover letter draft
→ review/edit
→ export/save
```

Cover letter должен генерироваться по отдельному prompt и не должен выдумывать опыт.

---

## 12. Export rules

На первом этапе нужен один простой стиль PDF/DOCX.

Не тратить время на красивое форматирование до стабилизации модели данных и tailoring flow.

Поддерживаемые форматы:

- PDF;
- DOCX;
- Markdown, если полезно как технический export/debug, но не как source of truth.

Export должен использовать только approved tailored content.

PDF/DOCX final artefacts создаются после review/approval.

---

## 13. UI direction

Старый сырой HTML-интерфейс нужно заменить на более современный и визуально приятный UI, оставаясь в FastAPI/Jinja2.

Требования:

- чистая навигация;
- карточки и таблицы вместо голого текста;
- понятные формы;
- понятный status/empty state;
- review screen с before/after;
- аккуратные action buttons;
- responsive enough для desktop browser;
- без тяжёлого frontend framework на первом этапе.

Язык интерфейса на первом этапе — английский.

Необходимо предусмотреть многоязычный интерфейс.
Будущая локализация на русский должна быть возможна, но не реализуется сейчас.

---

## 14. Architecture rules

Предпочтительный слой:

```text
routes → services/use cases → repositories → SQL models
routes → services/use cases → AI clients/prompts
routes → services/use cases → exporters/artifact writer
```

Правила:

- routes должны быть тонкими;
- бизнес-логика не должна жить в FastAPI route handlers;
- SQL models и repositories должны быть явными;
- AI prompts должны быть доступны для коррекции из настроек;
- prompt execution должен возвращать structured output;
- все AI changes проходят через review;
- exporters не должны читать из AI напрямую;
- file writes идут через artifact boundary;
- tests не вызывают реальный OpenAI API;
- secrets не хранятся в SQLite;
- raw OpenAI key хранится через OS keyring.

---

## 15. Database direction

SQLite — основной источник данных.

Минимальные доменные области:

- app settings;
- profiles/persons;
- private contact layer;
- resumes;
- resume sections;
- resume blocks;
- resume bullets;
- facts;
- bullet-fact links;
- block AI policies;
- prompt templates / prompt keys;
- applications;
- job descriptions;
- extracted job requirements;
- AI change proposals;
- accepted/rejected changes;
- cover letters;
- generated artefacts.

Если меняется schema — нужна миграция или deterministic local schema migration, в зависимости от выбранного DB boundary.
Текущую схему можно не сохранять.

---

## 16. Что запрещено без явного разрешения

Не добавлять:

- auto-apply;
- LinkedIn automation;
- real email sending;
- universal job scraping;
- multi-user cloud auth;
- payments;
- LangGraph;
- complex frontend framework;
- automatic old Markdown/YAML import;
- beautiful template system before core flow works;
- fake ATS score;
- claim fabrication without review and explicit unsupported/risk marking.

---

## 17. Testing rules

Текущие юнит-тесты были написаны до внедрения этих изменений и могут быть удалены, изменены или заменены согласно новой логике. 

Минимальные проверки перед завершением задачи:

```powershell
uv run ruff format .
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```

Для архитектурной перестройки нужны тесты на:

- SQL schema/repositories;
- profile creation;
- resume builder;
- section/block/bullet ordering;
- AI policy enforcement;
- private layer exclusion from AI payload;
- structured AI change proposals;
- before/after review;
- accepted/rejected changes persistence;
- export from approved content;
- cover letter generation boundary;
- no real OpenAI calls in tests.

---

## 18. Documentation rules

Поддерживать актуальность:

- `AGENTS.md` — стабильные правила;
- `SESSION_NOTES.md` — текущее состояние, план, следующие шаги;
- `README.md` — понятное описание продукта и запуск.

После изменения пользовательского поведения обновлять документацию.

Не превращать `AGENTS.md` в историю этапов.

---

## 19. Commit message format

Использовать emoji + conventional commit style:

```text
emoji type(scope): concise description

- optional detail
```

Примеры:

```text
🏗 refactor(core): reset project to SQL-first resume builder
✨ feat(resumes): add resume section and bullet model
🧪 test(ai): cover private layer exclusion from prompts
📝 docs(project): document resume builder architecture reset
```

---

## 20. Completion report

После выполнения задачи сообщать:

- что изменено;
- какие файлы изменены;
- что намеренно не менялось;
- какие проверки запускались;
- какие риски остались;
- следующие рекомендуемые шаги.

Если проверки не запускались — прямо указать почему.

  
