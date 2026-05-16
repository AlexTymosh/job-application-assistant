# SQL-first architecture

SQLite is the source of truth for local product data. The app creates one database under the selected app data folder and initialises the schema deterministically on startup.

Core domains:

- app settings;
- person profiles and private contacts;
- structured resumes;
- sections, blocks, bullets, skills, and facts;
- applications and raw job descriptions;
- extracted requirements;
- tailoring runs and AI change proposals;
- accepted/rejected review decisions;
- tailored resume snapshots;
- cover letters;
- artifact metadata.

Routes remain thin and delegate business rules to services. Services validate policies before storing AI proposals. Exporters render approved snapshots only.
