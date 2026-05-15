# SESSION_NOTES.md

Назначение: короткое состояние проекта для следующей AI/Codex-сессии. Это не пользовательская документация.

Читать сначала:

1. `AGENTS.md`
2. `SESSION_NOTES.md`
3. `README.md`, 
4. документы, связанные с текущей задачей

---

## Текущий статус

Проект прошёл через несколько технических этапов: app data folder, setup diagnostics, settings, keyring, managed profiles, managed CV storage, import tools, editor, managed-first pipeline, final export и smoke tests.

Но продуктовая модель оказалась неправильной.

Старый курс был слишком завязан на:

- file-based profiles;
- YAML config;
- YAML fact bank;
- Markdown CV variants;
- import from old files;
- pipeline compatibility with legacy data.

Это не соответствует новой цели.

Новая цель:

```text
SQL-first Resume Builder + AI Tailoring + Review/Export
```

Программу ещё никто не использовал, поэтому можно радикально переделывать модель без миграционных обязательств и без страха потерять реальные пользовательские данные.

---

## Главный продуктовый вывод

Текущий проект не нужно удалять полностью, потому что полезная инфраструктура уже есть:

- FastAPI/Jinja2 каркас;
- SQLite;
- app data folder;
- OS keyring для OpenAI key;
- PDF/DOCX/HTML/Markdown exporters;
- artefact writer/download safety;
- тесты, CI, ruff, pre-commit;
- часть settings/setup shell.

Но текущую YAML/Markdown-oriented продуктовую модель нужно заменить в корне.

Решение:

```text
Не начинать новый репозиторий.
Сделать архитектурный reset внутри текущего проекта.
```

---

## Новые продуктовые принципы

### 1. YAML удалить из пользовательского source of truth

Удалить как целевой пользовательский механизм:

- YAML settings;
- YAML fact bank;
- Markdown CV as source of truth;
- старые import flows;
- обязательную поддержку старых CV.

### 2. SQLite — основной источник данных

Все основные сущности должны жить в SQL:

- profiles/persons;
- private contact layer;
- resumes;
- sections;
- blocks;
- bullets;
- skills;
- facts;
- block/bullet AI policies;
- prompt templates/keys;
- applications;
- job requirements;
- AI change proposals;
- accepted/rejected changes;
- cover letters;
- artefacts.

### 3. Профиль — это человек

Профиль должен представлять человека, а не папку с YAML.

Один профиль может иметь много резюме, например:

```text
Alex
├── Software Engineer
├── Backend Developer
├── Automation Engineer
└── Data Analyst
```

### 4. Резюме — это конструктор

Резюме должно состоять из секций, блоков и bullet points.

Пользователь должен уметь:

- создавать резюме;
- добавлять стандартные и custom sections;
- менять порядок секций;
- менять порядок блоков;
- создавать разные версии резюме;
- выбирать, какие блоки может менять AI.

### 5. Приватный слой не попадает в AI

Phone, email, address, private links и другие private data не должны включаться в AI prompts.

Финальный документ собирается после AI review:

```text
Private contact layer
+ approved tailored resume content
→ final PDF/DOCX/HTML/Markdown
```

### 6. AI меняет не всё резюме, а разрешённые units

Базовые единицы редактирования:

| Область | Единица AI-редактирования |
|---|---|
| Summary / Description | весь блок |
| Job title / Resume title | всё название, если разрешено |
| Skills | весь набор skills |
| Work Experience | отдельный bullet |
| Projects | bullet или description по настройке |
| Education / Certifications / Languages / References | обычно readonly, если пользователь не разрешил |

Для каждого типа блока нужен отдельный prompt.

### 7. AI может менять job title

Job title можно менять, если пользователь разрешил это для данного поля/блока.

### 8. AI может создавать новые bullets

Разрешено, если:

- политика блока это позволяет;
- есть supporting facts или пользователь отключил обязательный fact link;
- change proposal помечает risk level;
- пользователь видит before/after и принимает изменение.

### 9. AI может скрывать нерелевантные bullets

Опционально. Скрытие должно быть change proposal, а не silent deletion.

### 10. Accepted/rejected changes нужно хранить

Каждое AI-предложение должно иметь статус:

- proposed;
- accepted;
- rejected;
- superseded, если будет нужно позже.

Не использовать ENUM чтобы не ограничивать возможность удаления.

Review page должна показывать before/after. Git-like diff желателен, но можно начать с простого old/new comparison.

### 11. Cover letter — отдельная сущность

Cover letter нужно создавать по описанию вакансии на основе отдельного prompt.

Cover letter должен храниться отдельно от CV и иметь собственный review/edit/export flow.

### 12. Один простой стиль PDF/DOCX на первом этапе

Не делать красивую типографику и несколько templates сейчас.

Фокус: корректная модель данных, AI changes, review, export.

---

## Что НЕ нужно сейчас

- Не нужно поддерживать импорт старых Markdown/YAML CV.
- Не нужно делать функцию для сокращения CV до 1–2 страниц.
- Не нужно делать несколько красивых шаблонов PDF/DOCX.
- Не нужно делать русскую локализацию UI сейчас.
- Не нужно делать auto-apply.
- Не нужно делать LinkedIn automation.
- Не нужно делать email sending.
- Не нужно делать full frontend framework.
- Не нужно делать cloud/multi-user auth.
- Не нужно делать LangGraph.

---

## Детальный план архитектурной перестройки

### Phase 0 — Freeze and reset decision

Цель: создать новую логику работы программы, путем выполнения всех описанных ниже этапов (phase) работ в полном объеме за один раз.

Можно Составить список файлов/пакетов, которые можно сохранить и которые нужно удалить/переписать.

Кандидаты сохранить:

- `app/main.py` shell;
- `app/storage/`;
- `app/secrets/`;
- exporters;
- artifact writer;
- CI/test infra;
- settings shell, если можно адаптировать.

Кандидаты удалить/переписать:

- YAML config loading как основной путь;
- file-based profile assumptions;
- old import tools;
- old managed CV model, если проще заменить;
- old pipeline source loader;
- old fake tailoring model.

---

### Phase 1 — SQL data model design

Цель: создать новую SQL-доменную модель.

Минимальные сущности:

```text
Profile
ProfileContact
Resume
ResumeSection
ResumeBlock
ResumeBullet
SkillSet / SkillItem
Fact
ResumeBulletFactLink
AiEditPolicy
PromptTemplate
Application
JobRequirement
AiChangeProposal
TailoredResumeSnapshot
CoverLetter
Artifact
```

Особое внимание:

- порядок секций;
- порядок блоков;
- порядок bullets;
- включён/выключен блок;
- editable/readonly fields;
- fact link required flag;
- prompt key per block type;
- application history per profile.

Acceptance criteria:

- SQL schema создаётся детерминированно;
- нет YAML dependency;
- тесты покрывают create/list/update/order/visibility;
- private contact layer отделён от AI-safe content.

---

### Phase 2 — Settings and first-run setup

Цель: сделать настройки без YAML.

Settings page должна позволять:

- выбрать app data folder;
- ввести/заменить/удалить OpenAI API key через OS keyring;
- выбрать export formats;
- создать profile;
- открыть profile/resume management.

Важно:

- raw OpenAI key не хранится в SQLite;
- settings не требуют YAML;
- app должен стартовать без созданного профиля и показывать setup/settings.

---

### Phase 3 — Profile manager

Цель: создать профили разных людей.

Пользователь должен уметь:

- создать profile;
- добавить contact/private data;
- выбрать active profile;
- видеть application history по профилю;
- создать несколько profiles для разных людей.

Private contact data не должно попадать в AI prompt.

---

### Phase 4 — Resume builder

Цель: сделать конструктор резюме.

Пользователь должен уметь:

- создать resume внутри profile;
- создать стандартные sections;
- создать custom sections;
- создать blocks;
- создать bullets;
- менять порядок;
- включать/выключать blocks;
- задавать AI policy для blocks/fields;
- создавать разные resume variants.

На первом этапе UI должен быть современнее старого:

- нормальная навигация;
- карточки;
- таблицы;
- понятные формы;
- кнопки действий;
- empty states.

---

### Phase 5 — Facts and evidence

Цель: хранить verified facts в SQL.

Пользователь должен уметь:

- создавать facts;
- редактировать facts;
- включать/выключать facts;
- связывать facts с bullets;
- включать/выключать обязательность fact links для AI changes.

Default policy:

```text
No verified fact → no strong verified claim.
```

Но это должна быть настройка, которую можно отключить для конкретного блока/resume/prompt, если пользователь осознанно хочет больше свободы.

---

### Phase 6 — Application intake

Цель: новая страница создания заявки.

Страница должна иметь:

1. выбор profile;
2. выбор resume из этого profile;
3. поле для текста вакансии;
4. future placeholder для source URL, если понадобится позже.

После submit:

- сохранить job text;
- создать application;
- извлечь requirements;
- открыть analysis/review page.

---

### Phase 7 — AI prompt system

Цель: AI должен редактировать отдельные layers/blocks по отдельным prompts.

Нужно создать prompt registry:

```text
summary_rewrite
skills_rewrite
job_title_rewrite
work_experience_bullet_rewrite
project_bullet_rewrite
cover_letter_generate
```

Каждый prompt должен иметь:

- input schema;
- output schema;
- allowed actions;
- forbidden actions;
- fact policy;
- risk labels;
- tests with fake client.

AI должен возвращать structured output, а не готовый uncontrolled document.

---

### Phase 8 — AI tailoring and structured diffs

Цель: создать предложения изменений.

Поток:

```text
Application + selected resume
→ job requirements
→ editable blocks
→ facts
→ prompt per block
→ AI change proposals
→ review page
```

Change proposal должен хранить:

- target type;
- target id;
- before text;
- after text;
- action: rewrite/add/hide/change_title/change_skills;
- reason;
- job requirement ids;
- fact ids;
- risk level;
- warning codes;
- status accepted/rejected/proposed.

---

### Phase 9 — Review page

Цель: пользователь принимает или отклоняет каждое изменение.

Минимальный UI:

- grouping by section/block;
- before/after;
- reason;
- facts used;
- risk level;
- accept/reject buttons;
- apply accepted changes;
- preview final tailored resume.

Git-like diff можно отложить, если будет простой before/after.

---

### Phase 10 — Final resume snapshot and export

Цель: экспортировать только approved tailored resume.

Поток:

```text
accepted changes
→ tailored resume snapshot
→ add private contact layer
→ render one simple style
→ PDF/DOCX/HTML/Markdown
```

Export formats из settings должны реально работать.

---

### Phase 11 — Cover letter

Цель: создавать cover letter отдельно от CV.

Поток:

```text
Application
→ selected profile/resume
→ job requirements
→ cover letter prompt
→ draft
→ review/edit
→ export/save
```

Cover letter должен:

- не выдумывать опыт;
- ссылаться только на allowed facts/resume content;
- храниться в application history;
- быть редактируемым пользователем.

---

### Phase 12 — Smoke tests and release docs

Цель: подготовить первый новый developer release.

Smoke test должен проверять:

- first-run setup;
- settings;
- create profile;
- create resume;
- create facts;
- link bullet to fact;
- create application;
- choose profile/resume;
- run AI fake tailoring;
- review before/after;
- accept/reject changes;
- generate cover letter;
- export final CV;
- private layer not sent to AI;
- no YAML required.

---

## P0 / P1 / P2 на текущий момент

### P0

Нет P0 для продолжения, если принято решение делать архитектурный reset.

### P1

| Приоритет | Проблема | Решение |
|---|---|---|
| P1 | YAML/Markdown модель не соответствует продукту | Удалить из source of truth |
| P1 | Нет полноценного SQL resume builder | Спроектировать и реализовать новую модель |
| P1 | AI не редактирует block-level units | Ввести prompt per block type и structured changes |
| P1 | Private contact layer не отделён как first-class model | Ввести отдельную таблицу/слой и запретить попадание в AI payload |
| P1 | Review flow должен хранить accepted/rejected changes | Реализовать change proposal model |
| P1 | Cover letter нужен как отдельный flow | Добавить после базового tailoring flow |

### P2

| Приоритет | Проблема | Решение |
|---|---|---|
| P2 | Git-like diff может быть сложным | Начать с before/after, git-like diff позже |
| P2 | Несколько красивых templates не нужны сейчас | Один простой стиль export |
| P2 | Русская локализация UI не нужна сейчас | Предусмотреть архитектурно, не реализовывать |
| P2 | CV shortening to 1–2 pages не нужен сейчас | Не включать в scope |

---

## Следующий конкретный шаг

Сделать PR/задачу:

```text
Architecture Reset Phase 0: document SQL-first Resume Builder direction and remove YAML-first assumptions from project docs.
```

После этого:

```text
Phase 1: implement new SQL domain model for profiles, resumes, sections, blocks, bullets, facts, AI policies, applications, and change proposals.
```

---

## Рекомендуемый commit message для Phase 0

```text
🏗 refactor(project): reset direction to SQL-first resume builder

- replace YAML-first product model with SQL-first resume builder architecture
- define profile, resume, block, bullet, fact, AI policy and review flows
- document privacy layer and structured AI change proposal rules
```
