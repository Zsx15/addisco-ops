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

\- governance stabilization;

\- RAG stabilization;

\- pedagogical tracking;

\- architecture consistency.



Current next milestone:

\- attempts.chunk\_id implementation.



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

