\# CLAUDE.md



\## Runtime Purpose



This file defines the operational rules Claude Code must follow while working on this repository.



Goals:

\- preserve architecture consistency;

\- preserve MVP stability;

\- minimize technical debt;

\- enforce safe incremental development;

\- maintain clear and predictable workflows.



\---



\# Required Reading Order



Before implementing any modification, always read:



1\. TASK\_MASTER.md

2\. ROADMAP.md

3\. PRD.md

4\. ARCHITECTURE.md

5\. TASKS/current\_tasks.json



Never start implementation without understanding:

\- current milestone;

\- architecture constraints;

\- task dependencies;

\- current priorities.



\---



\# Mandatory Workflow



\## 1. Analyze First



Before changing code:

\- inspect related files;

\- understand current pipelines;

\- identify dependencies;

\- identify regression risks;

\- identify impacted systems.



Never assume architecture behavior.



\---



\## 2. Plan Before Modify



Always explain before implementation:

\- impacted files;

\- intended logic;

\- risks;

\- required tests.



No major modification without explicit validation.



\---



\## 3. Safe Implementation Rules



Rules:

\- minimize modified files;

\- avoid uncontrolled refactors;

\- preserve backward compatibility;

\- preserve fallback behavior;

\- avoid unnecessary abstractions;

\- avoid unnecessary dependencies.



Prefer:

\- targeted modifications;

\- incremental evolution;

\- explicit logic;

\- reversible changes.



\---



\## 4. Mandatory Validation



Always validate:

\- Python imports;

\- py\_compile;

\- Streamlit startup;

\- SQLite compatibility;

\- retrieval pipeline;

\- fallback mode;

\- non-regression behavior.



Never assume generated code works.



\---



\## 5. Final Response Requirements



After each implementation:

\- summarize modified files;

\- explain architecture impact;

\- explain added logic;

\- explain remaining risks;

\- recommend next logical step.



\---



\# Critical Runtime Rules



\## Never Break MVP Stability



The project must always remain:

\- launchable;

\- testable;

\- demonstrable;

\- minimally functional.



\---



\## Never Break Fallback Mode



If:

\- embeddings fail;

\- retrieval fails;

\- APIs fail;

\- RAG systems fail;



the application must automatically fallback to raw-text mode.



Fallback stability is mandatory.



\---



\## Preserve Stable IDs



Avoid:

\- DELETE + INSERT workflows.



Prefer:

\- targeted UPDATE operations.



Future systems depend on stable identifiers:

\- attempts.chunk\_id;

\- pedagogical memory;

\- analytics;

\- spaced repetition.



\---



\## Never Delete Without Explicit Approval



Never perform without explicit user approval:

\- database reset;

\- mass deletion;

\- document deletion;

\- embedding deletion;

\- history deletion.



\---



\# UX / UI GOVERNANCE



\## Scope Separation



The pedagogical MVP engine is now stable (TASK-001 to TASK-011).

UX and UI improvements are a separate scope from the backend engine.



Every task that primarily affects the visual layer, user experience,

labels, layout, or demonstration flow must be identified as FRONTEND/UX

in its description.



\---



\## Protected Files — Critical Engine



The following files form the critical pedagogical engine.

A UX task must NOT modify them without explicit user validation:



\- database.py — SQLite, analytics, spaced repetition, mastery;

\- ai\_service.py — RAG, embeddings, LLM calls, question types, correction;

\- document\_service.py — ingestion pipeline, chunking, demo seed.



If a UX task requires a change to a critical engine file,

state the reason explicitly and wait for GO before proceeding.



\---



\## UX Task Perimeter



UX modifications must target:



\- app.py — layout, widgets, tabs, conditional blocks;

\- displayed text — labels, captions, headers, button text;

\- visual hierarchy — colors, expanders, columns, metrics;

\- demonstration flow — section order, entry points, suggestions.



\---



\## Pre-Task UX Checklist



Before implementing any UX task, explicitly state:



\- files to be modified;

\- user-visible impact (what changes on screen);

\- regression risk on the pedagogical engine;

\- visual tests to perform after implementation.



\---



\## Double Validation for Engine Changes



Any modification to a critical engine file requires:



1\. explicit analysis and plan;

2\. explicit GO from the user;

3\. py\_compile + Streamlit startup + non-regression check.



A UX task that inadvertently touches the engine must stop and ask before proceeding.



\---



\## Goal



Make the demonstration clearer and more impactful

without modifying the pedagogical engine behavior.



\---



\# Git Policy



Commits must be:

\- isolated;

\- descriptive;

\- reversible;

\- logically scoped.



Commit prefixes:

\- feat:

\- fix:

\- docs:

\- refactor:

\- qa:



\---



\# Current Technical Priorities



Current priorities:

\- UX/UI clarity for demonstration (FRONTEND/UX tasks);

\- adaptive pedagogical engine evolution (Phase 8);

\- production readiness preparation (Phase 10).



Current state:

\- MVP pedagogical engine complete (TASK-001 to TASK-011).

\- RAG, embeddings, spaced repetition, 6 question types, mastery bias: operational.



Current next milestone:

\- UX polish and demonstration flow.



\---



\# Explicit Non-Priorities



Do not introduce yet:

\- complex multi-agent systems;

\- Kubernetes;

\- external vector databases;

\- premature scaling infrastructure;

\- autonomous orchestration systems;

\- unnecessary abstractions;

\- premature microservices.



SQLite + numpy remain the official MVP solution.



\---



\# Engineering Philosophy



Prefer:

\- clarity over sophistication;

\- robustness over complexity;

\- maintainability over optimization;

\- incremental progress over massive rewrites;

\- explicit architecture over implicit behavior.



The project is evolving toward:

\- adaptive pedagogical systems;

\- cognitive learning pipelines;

\- intelligent revision workflows;

\- long-term knowledge consolidation.



\---



\# APP FACTORY + DEVLOG POLICY



\## App Factory role



App Factory is a task orchestration layer only.

It does not change the stack, the architecture, or the business logic.



Files added by App Factory:

\- task.mjs — orchestration CLI;

\- taskrc.schema.json — config schema;

\- .taskrc.json — project config (Python/Streamlit, py\_compile review);

\- DEVLOG.md — chronological development journal.



\## Workflow



Use App Factory commands via Node:

\- node task.mjs brief — daily briefing;

\- node task.mjs status — project overview;

\- node task.mjs review \<id\> — run py\_compile on core files;

\- node task.mjs prompt \<id\> — generate Claude Code prompt;

\- node task.mjs claim \<id\> — mark task in-progress;

\- node task.mjs ship \<id\> — stage + commit;

\- node task.mjs done \<id\> — mark done.



\## DEVLOG policy



After each significant task or milestone:

\- add a dated entry to DEVLOG.md;

\- record actions, decisions, and invariants preserved;

\- record next step.



Never skip DEVLOG update after a completed task.



\## Constraints



App Factory constraints:

\- never replaces existing governance files;

\- never modifies business logic;

\- never breaks MVP stability;

\- never breaks fallback mode;

\- py\_compile is the mandatory minimum review for any Python change.

