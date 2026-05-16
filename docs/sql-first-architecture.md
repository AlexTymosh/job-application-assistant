# SQL-first Architecture

## Source of truth

SQLite is the source of truth for user-managed data. YAML and Markdown are not runtime sources of truth. Markdown is allowed only as an optional export artifact.

## Layers

```text
FastAPI routes -> services -> SQLAlchemy models / LLM clients / exporters / artifact boundary
```

Routes stay thin and delegate business logic to services. Services own active-profile resolution, dashboard statistics, resume building, application events, AI tailoring, cover-letter generation, snapshots, and exports.

## Core data model

The app-level SQLite database stores:

- app settings, including `active_profile_id`;
- person profiles and private contact details;
- resumes, sections, blocks, bullets, skills, facts, and fact links;
- prompt templates;
- applications and extracted requirements;
- application events;
- tailoring runs and AI change proposals;
- tailored resume snapshots;
- cover letters;
- artifact metadata.

## Active profile

There is one active profile for the local app. `SettingsService` validates that `active_profile_id` points to an existing profile. If the profile is missing, the setting is cleared and the UI shows no active profile.

Dashboard, Application, CV Builder links, facts, and resume selection are profile-scoped. Settings is global and available without an active profile.

## Application events

Application events record significant workflow actions such as application creation, requirement extraction, proposal decisions, snapshot creation, artifact export, copy events, download events, likely-applied transitions, and manual applied marking.

Copy and download events update likely-applied state only. Manual marking is the user-confirmed applied state.

## Prompt templates

Prompt templates are DB-backed. User-editable prompt text is stored separately from protected safety prompt text. Protected safety rules are always preserved and include no fabrication, untrusted job posting, private contact exclusion, and structured output.

## Snapshots and exports

Approved snapshots are created from accepted AI proposals and intentionally exclude private contact data. Final export rendering adds private contact data only at the final render/export boundary.

## Schema changes

Current initialisation is deterministic through SQLAlchemy metadata creation. Any future persistent-user release should add explicit versioned migrations before relying on existing user data upgrades.
