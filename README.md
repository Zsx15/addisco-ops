# ADDISCO OPS — Moteur de révision pédagogique par IA

> Plateforme de formation professionnelle déployée en production.
> Chaque organisation importe ses propres documents métier ; le moteur génère
> des sessions de révision personnalisées et adapte la pédagogie en temps réel.

**Demo live :** [addisco-ops-production.up.railway.app](https://addisco-ops-production.up.railway.app)
&nbsp;·&nbsp; Compte démo : `demo` / `Demo2026!`

![CI](https://github.com/Zsx15/addisco-ops/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-red)
![Tests](https://img.shields.io/badge/tests-383%20passing-brightgreen)
![Deployed](https://img.shields.io/badge/Railway-live-success)
![Auditor](https://img.shields.io/badge/System%20Auditor-99%2F100-brightgreen)

---

## Sommaire

1. [Vision et problématique](#1-vision-et-problématique)
2. [Fonctionnalités](#2-fonctionnalités)
3. [Architecture générale](#3-architecture-générale)
4. [Structure du projet](#4-structure-du-projet)
5. [Base de données](#5-base-de-données)
6. [Moteur adaptatif — seuils calibrés](#6-moteur-adaptatif--seuils-calibrés)
7. [Skills Engine V1.0](#7-skills-engine-v10)
8. [Corpus personnalisés](#8-corpus-personnalisés)
9. [Système de rôles](#9-système-de-rôles)
10. [QA, observabilité et outils internes](#10-qa-observabilité-et-outils-internes)
11. [Tests automatisés](#11-tests-automatisés)
12. [Déploiement Railway](#12-déploiement-railway)
13. [Lancement local](#13-lancement-local)
14. [Stack technique](#14-stack-technique)
15. [État du projet](#15-état-du-projet)

---

## 1. Vision et problématique

Les équipes opérationnelles doivent maîtriser des procédures, des réglementations
et des protocoles en constante évolution. Les formations classiques — PDF, présentiel,
e-learning statique — produisent des connaissances fragiles qui s'érodent rapidement.

**ADDISCO OPS** permet à une organisation d'importer ses propres documents (procédures
internes, référentiels métier, réglementations) et de générer automatiquement des
sessions de révision personnalisées pour ses collaborateurs.

Le moteur adapte la pédagogie à chaque apprenant en temps réel : type de question,
niveau de difficulté, rythme de révision et priorité des notions fragiles évoluent
selon les résultats observés. Les intervalles de répétition espacée sont calculés
par un moteur calibré empiriquement — pas par des heuristiques arbitraires.

---

## 2. Fonctionnalités

### Gestion documentaire

| Fonctionnalité | État |
|---|---|
| Import PDF (pypdf) | Stable |
| Import DOCX (python-docx) | Stable |
| Import texte brut | Stable |
| Découpage en chunks sémantiques (~500 chars) | Stable |
| Calcul d'embeddings (text-embedding-3-small, 1 536 dims) | Stable |
| Catégorisation par domaine | Stable |
| Recherche cross-documents (RAG multi-doc) | Stable |

### Corpus personnalisés

| Fonctionnalité | État |
|---|---|
| Création de corpus nommés (ex : "VO583", "Sécurité ferroviaire") | Stable |
| Sélection multi-documents par corpus | Stable |
| Corpus actif — entraînement, analytics et révisions filtrés | Stable |
| Badge corpus actif dans la sidebar | Stable |
| Fallback automatique si aucun corpus actif | Stable |

### Moteur pédagogique

| Fonctionnalité | État |
|---|---|
| Génération de questions — 6 types pédagogiques | Stable |
| Correction IA structurée (score 0–1, type d'erreur, notion) | Stable |
| Recherche RAG contextuelle (cosinus numpy) | Stable |
| Fallback texte brut si RAG indisponible | Stable |
| Répétition espacée — intervalles adaptatifs calibrés | Stable |
| Sélection du type de question selon le profil utilisateur | Stable |
| Difficulté adaptative (force easy / allow hard) | Stable |

Les 6 types de questions : `question_directe`, `cas_pratique`, `vrai_faux`,
`question_piege`, `reformulation`, `consequence`.

### Analytics et profil d'apprentissage

| Fonctionnalité | État |
|---|---|
| Score moyen global et par document | Stable |
| Momentum sur 7 jours | Stable |
| Learning velocity (delta inter-sessions) | Stable |
| Consistency score (régularité sur 30 jours) | Stable |
| Notions fragiles détectées automatiquement | Stable |
| Répartition par type d'erreur | Stable |
| Profil pédagogique dominant (logique/procédural/narratif/analogique) | Stable |
| Métriques de rétention J+1 / J+7 / J+30 | Stable (données >30j requises) |
| Plan de session adaptatif | Stable |

### Interface et dashboard

| Fonctionnalité | État |
|---|---|
| Dashboard apprenant dark premium (Plotly) | Stable |
| KPI cards — score, tentatives, maîtrisées, en retard, momentum | Stable |
| Storytelling moteur — signaux réels, zéro marketing | Stable |
| Recommandation IA Coach contextualisée | Stable |
| Cockpit pédagogique formateur (cohorte) | Stable |
| Historique paginé des tentatives | Stable |
| Mode présentation (navigation réduite, F11) | Stable |

### Gestion des utilisateurs

| Fonctionnalité | État |
|---|---|
| Authentification par compte (bcrypt) | Stable |
| Rôles : apprenant / formateur / admin | Stable |
| Bootstrap premier admin (interface one-shot) | Stable |
| Inscription publique — rôle apprenant uniquement | Stable |
| Promotion de rôle via interface admin | Stable |
| Outils CLI admin (create_admin, reset_password) | Stable |
| Gate APP_PASSWORD (accès global protégé) | Stable |

---

## 3. Architecture générale

### Pipeline documentaire et pédagogique

```
Document (PDF / DOCX / TXT)
        │
        ▼
  document_service.py
  Extraction + nettoyage du texte
        │
        ▼
  Découpage en chunks (~500 chars, par section logique)
        │
        ▼
  ai_service.py — generate_embedding()
  Embedding float32 BLOB → chunks.embedding (1 536 dims)
        │
        ▼
  ─────────────── Session d'entraînement ───────────────
        │
        ▼
  rag_service.py — search_similar_chunks()
  Recherche cosinus — top-K chunks les plus pertinents
  (filtrés par corpus actif si défini)
        │
        ▼
  ai_service.py — generate_question()
  Prompt LLM (gpt-4o-mini) + type pédagogique sélectionné
        │
        ▼
  Réponse de l'apprenant
        │
        ▼
  ai_service.py — correct_answer()
  Correction structurée : score (0–1), error_type, notion
        │
        ▼
  database.py — save_attempt()
  Enregistrement + chunk_id préservé (répétition espacée)
        │
        ▼
  adaptive_engine.py
  classify_mastery() → _adaptive_interval()
  _choose_question_type() selon profil
        │
        ▼
  Dashboard — analytics, notions fragiles, progression
```

### Modules et responsabilités

| Fichier | Rôle |
|---|---|
| `app.py` | Point d'entrée Streamlit — auth, routing, sidebar, session_state |
| `ai_service.py` | RAG, embeddings, génération LLM, correction, fallback |
| `database.py` | Couche SQLite — init_db, tentatives, profils, documents, re-exports |
| `adaptive_engine.py` | Moteur pur — zéro import projet (contrainte critique) |
| `rag_service.py` | Recherche vectorielle cosinus (numpy, BLOB SQLite) |
| `document_service.py` | Import, chunking, seed démo |
| `auth_service.py` | Bcrypt, rôles, register/verify |
| `logger.py` | Logging centralisé |
| `config.py` | Configuration centralisée |
| `ui_helpers.py` | Helpers UX partagés entre onglets |

### Séparation des couches

```
Runtime applicatif (app.py + tabs/ + db/ + engine/ + ai_service.py + ...)
        │
        ├── Ne dépend jamais de tools/
        └── Ne dépend jamais de tests

tools/  (CLI internes — jamais importés par le runtime)
        ├── tools/admin/        — scripts admin CLI
        ├── tools/testing/      — calibration + simulation
        ├── tools/observability/ — audit read-only
        ├── tools/qa/           — QA + auditor système
        ├── tools/reports/      — génération rapports
        └── tools/guardrails/   — validation architecture

tests/
        ├── test_regression.py  — 262 tests (pytest)
        ├── test_integration.py — tests intégration
        └── test_auth_service.py — tests auth
```

---

## 4. Structure du projet

```
addisco-ops/
│
├── app.py                        — Routeur Streamlit (auth, sidebar, navigation multi-rôles)
├── ai_service.py                 — RAG, embeddings, génération, correction (OpenAI)
├── adaptive_engine.py            — Moteur pur (zéro dépendance projet)
├── database.py                   — Couche SQLite + re-exports
├── rag_service.py                — Recherche vectorielle cosinus
├── document_service.py           — Import, chunking, seed démo
├── auth_service.py               — Authentification bcrypt, rôles
├── seed_demo_attempts.py         — Données de démo pour démarrage
├── logger.py                     — Logging centralisé
├── config.py                     — Configuration centralisée
├── ui_helpers.py                 — Helpers UX partagés
│
├── tabs/                         — Onglets Streamlit
│   ├── styles.py                 — CSS globaux, dark dashboard, header
│   ├── tab_training.py           — Session d'entraînement + corpus actif
│   ├── tab_dashboard.py          — Analytics dark premium (Plotly)
│   ├── tab_corpus.py             — Corpus personnalisés (créer, activer, supprimer)
│   ├── tab_history.py            — Historique paginé des tentatives
│   ├── tab_documents.py          — Import et gestion des documents
│   ├── tab_engine.py             — Paramètres moteur + métriques runtime
│   ├── tab_trainer.py            — Cockpit formateur (cohorte)
│   └── tab_admin.py              — Gestion des utilisateurs et rôles
│
├── db/                           — Sous-modules base de données (séparés de database.py)
│   ├── analytics.py              — get_attempts, get_score_evolution, get_error_frequency,
│   │                               get_topic_stats (filtrage document_ids)
│   ├── chunks.py                 — get_chunk_stats, get_revision_suggestion
│   ├── corpus.py                 — CRUD corpus personnalisés
│   ├── skills.py                 — Moteur de compétences
│   ├── profile.py                — Profil d'apprentissage
│   ├── runtime_metrics.py        — Métriques runtime LLM
│   └── admin.py                  — Gestion utilisateurs
│
├── engine/                       — Modules moteur adaptatif
│   ├── thresholds.py             — Source unique de vérité des seuils calibrés
│   ├── spaced_rep.py             — Répétition espacée (intervalles adaptatifs)
│   ├── adaptive_difficulty.py    — Force easy / allow hard
│   ├── question_type.py          — Sélection du type pédagogique
│   ├── skill_engine.py           — Mapping chunks → compétences
│   ├── skill_graph.py            — Graphe de dépendances entre compétences
│   ├── skill_mapper.py           — Détection compétences par mots-clés
│   ├── skill_keywords.py         — Référentiel de mots-clés par compétence
│   ├── skill_analytics.py        — Métriques par compétence
│   ├── skill_debug.py            — Diagnostic Skills Engine
│   ├── curriculum_engine.py      — Curriculum adaptatif ordonné
│   ├── error_pattern_memory.py   — Mémoire des patterns d'erreur
│   ├── profile_metrics.py        — Momentum, velocity, consistency
│   ├── retention.py              — Métriques de rétention J+1/J+7/J+30
│   ├── session_plan.py           — Plan de session adaptatif
│   └── user_profile_insights.py  — Insights profil utilisateur
│
├── ai_gateway/                   — Gateway LLM (rate limiting, logging)
│   ├── gateway.py                — Interception et logging des appels LLM
│   ├── rate_limiter.py           — Limitation par user/type
│   └── request_logger.py         — Journal des appels en JSONL
│
├── observability/                — Métriques runtime
│   ├── metrics.py                — Collecte latences, fallback rate, error rate
│   └── error_tracker.py          — Remontée Sentry
│
├── architecture_guard/           — Validation structurelle
│   ├── file_audit.py             — Audit des fichiers critiques
│   └── rules.py                  — Règles architecturales
│
├── frontend/                     — Composants dashboard formateur
│   └── dashboard/
│       ├── trainer_dashboard.py  — Vue cohorte
│       └── components/           — Cartes, graphes, alertes, profil adaptatif
│
├── tools/                        — Outils internes (jamais importés par le runtime)
│   ├── admin/
│   │   ├── create_admin.py       — CLI : créer un compte admin
│   │   └── reset_password.py     — CLI : réinitialiser un mot de passe
│   ├── testing/
│   │   ├── run_training_calibration_suite.py  — Suite complète de calibration
│   │   ├── simulate_adaptive_training.py      — Simulation moteur adaptatif
│   │   ├── simulate_learning_session.py       — Simulation session complète
│   │   ├── calibrate_mastery_threshold.py     — Calibration seuil maîtrise
│   │   ├── calibrate_mastery_boundaries.py    — Calibration bornes maîtrise
│   │   ├── calibrate_adaptive_difficulty.py   — Calibration difficulté adaptative
│   │   ├── calibrate_review_intervals.py      — Calibration intervalles révision
│   │   └── calibrate_engine.py               — Calibration moteur global
│   ├── observability/
│   │   ├── audit_skills_empirique.py         — Audit read-only Skills Engine
│   │   ├── chunk_quality_analyzer.py         — Analyse qualité des chunks
│   │   ├── runtime_analytics.py              — Métriques runtime LLM
│   │   ├── error_pattern_observer.py         — Patterns d'erreurs observés
│   │   └── curriculum_observer.py            — Observation curriculum
│   ├── qa/
│   │   ├── global_system_auditor.py          — Audit système complet (10 sections, score /100)
│   │   ├── test_robustesse_100q.py           — 100 cycles simulés (mock ou API)
│   │   └── audit_sqlite_connections.py       — Audit connexions SQLite
│   ├── reports/
│   │   └── generate_learning_report.py       — Rapport HTML par apprenant
│   ├── roadmap/
│   │   ├── close_task.py                     — Fermeture de tâches roadmap
│   │   └── update_progress.py                — Mise à jour progression
│   ├── maintenance/
│   │   └── maintenance_report.py             — Rapport de maintenance
│   └── guardrails/
│       └── architecture_guardrails.py        — Vérification des contraintes architecturales
│
├── docs/assets/                  — Captures d'écran pour la documentation
│
├── reports/                      — Rapports générés (gitignorés, créés à la demande)
│
├── logs/                         — Logs runtime (app.log, ai_requests.jsonl, errors.jsonl)
│
├── test_regression.py            — Suite de régression principale (262 tests)
├── test_integration.py           — Tests d'intégration
├── test_auth_service.py          — Tests authentification
│
├── Dockerfile                    — Image Docker python:3.11-slim
├── docker-compose.yml            — Stack locale avec volume database.db
├── railway.toml                  — Configuration déploiement Railway
├── requirements.txt              — Dépendances Python
├── .env.example                  — Template variables d'environnement
│
├── README.md                     — Ce fichier
├── README_DEV.md                 — Comptes de test, outils CLI, règles admin
├── ARCHITECTURE.md               — Architecture technique détaillée
├── DEVLOG.md                     — Journal de développement chronologique
├── ROADMAP.md                    — Phases et tâches
└── TASK_MASTER.md                — Registre principal des tâches
```

---

## 5. Base de données

SQLite (`database.db`), mode WAL activé. Stable pour ~10 utilisateurs simultanés.
Le chemin est configurable via `DB_PATH` (variable d'environnement).

### Table `attempts`

| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| user_id | TEXT | |
| document_id | INTEGER | FK → documents.id |
| chunk_id | INTEGER | FK → chunks.id — répétition espacée |
| question | TEXT | |
| user_answer | TEXT | |
| expected_answer | TEXT | |
| correction | TEXT | |
| score | REAL | 0.0–1.0 |
| error_type | TEXT | correct / reponse_vague / oubli_etape / hors_sujet / non_evaluable / confusion_notion / erreur_ordre / … |
| topic | TEXT | normalisé capitalize |
| pedagogy_type | TEXT | 6 types |
| response_time_seconds | REAL | |
| success_after_retry | INTEGER | 0/1 |
| created_at | TIMESTAMP | |

### Table `documents`

| Colonne | Type |
|---|---|
| id | INTEGER PK |
| title | TEXT |
| source_type | TEXT |
| filename | TEXT |
| raw_text | TEXT |
| cleaned_text | TEXT |
| char_count | INTEGER |
| created_at | TIMESTAMP |

### Table `chunks`

| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | Stable — ne jamais DELETE+INSERT |
| document_id | INTEGER | FK → documents.id |
| chunk_index | INTEGER | |
| section_title | TEXT | |
| chunk_text | TEXT | |
| char_count | INTEGER | |
| embedding | BLOB | float32 LE, 1 536 dims |
| created_at | TIMESTAMP | |

### Table `chunk_skills`

| Colonne | Type | Note |
|---|---|---|
| chunk_id | INTEGER | FK → chunks.id |
| skill_name | TEXT | 10 compétences V1.0 |
| is_active | INTEGER | 0/1 |
| confidence | REAL | score de confiance du mapping |

### Table `corpus`

| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| user_id | TEXT | |
| corpus_name | TEXT | ex : "VO583", "Sécurité ferroviaire" |
| created_at | TIMESTAMP | |

### Table `corpus_documents`

| Colonne | Type | Note |
|---|---|---|
| corpus_id | INTEGER | FK → corpus.id — PK composite |
| document_id | INTEGER | FK → documents.id — PK composite |

### Table `user_learning_profile`

| Colonne | Type | Note |
|---|---|---|
| user_id | TEXT PK | |
| preferred_pedagogy | TEXT | logical/procedural/narrative/analogy |
| logical_score | REAL | |
| procedural_score | REAL | |
| narrative_score | REAL | |
| analogy_score | REAL | |
| average_score | REAL | |
| fragile_topics | TEXT | JSON array |
| momentum | REAL | delta score 7j |
| learning_velocity | REAL | delta inter-sessions |
| consistency_score | REAL | jours actifs / 30 |
| updated_at | TIMESTAMP | |

### Table `users`

| Colonne | Type | Note |
|---|---|---|
| user_id | TEXT PK | |
| username | TEXT UNIQUE | |
| password_hash | TEXT | bcrypt |
| role | TEXT | apprenant / formateur / admin |
| created_at | TIMESTAMP | |

### Table `runtime_metrics`

| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| metric_type | TEXT | latency / fallback / error |
| value | REAL | |
| metadata | TEXT | JSON |
| created_at | TIMESTAMP | |

---

## 6. Moteur adaptatif — seuils calibrés

Les seuils sont définis dans `engine/thresholds.py` — source unique de vérité.
Ils ont été calibrés empiriquement via les scripts `tools/testing/calibrate_*.py`
(Phase 18B–18C). Les valeurs sont protégées par des tripwires dans `test_regression.py`.

```python
# engine/thresholds.py

MASTERY_FRAGILE      = 0.60   # avg_score < seuil → Fragile
MASTERY_MASTERED     = 0.80   # avg_score ≥ seuil ET n ≥ MIN_ATTEMPTS → Maîtrisé
MASTERY_MIN_ATTEMPTS = 5      # tentatives minimum pour valider la maîtrise

ADAPTIVE_FORCE_EASY  = 0.40   # forcer easy quelle que soit la mastery
ADAPTIVE_ALLOW_HARD  = 0.65   # autoriser hard si Maîtrisé

REVIEW_INTERVALS = {
    "Fragile":          1,    # revoir en 1 jour
    "En consolidation": 3,    # revoir en 3 jours
    "Maîtrisé":         7,    # revoir en 7 jours
}
```

### Classification de maîtrise par chunk

```
n_attempts < MIN_ATTEMPTS → Débutant
avg_score < MASTERY_FRAGILE → Fragile
avg_score < MASTERY_MASTERED → En consolidation
avg_score ≥ MASTERY_MASTERED → Maîtrisé
```

### Sélection du type de question

```
adaptive_engine._choose_question_type()
  ├── biais mastery (fragile → vrai_faux, débutant → question_directe, …)
  ├── biais profil pédagogique (preferred_pedagogy de l'utilisateur)
  └── rotation anti-répétition (évite le même type 2x de suite)
```

### Suite de calibration

```bash
# Vérification rapide (2s) — GO SAFE attendu
python tools/testing/run_training_calibration_suite.py --quick

# Suite complète avec rapport markdown
python tools/testing/run_training_calibration_suite.py --full
```

---

## 7. Skills Engine V1.0

10 compétences définies dans `engine/skill_keywords.py` :

| Compétence | Description |
|---|---|
| `memorisation_faits` | Mémorisation de faits, dates, définitions |
| `comprehension_procedure` | Compréhension de procédures étape par étape |
| `identification_concepts` | Identification et classification de concepts |
| `application_regles` | Application de règles à des cas concrets |
| `analyse_causale` | Analyse des causes et conséquences |
| `resolution_problemes` | Résolution de problèmes complexes |
| `prise_decision` | Prise de décision sous contraintes |
| `evaluation_critique` | Évaluation critique d'une situation |
| `synthese_reformulation` | Synthèse et reformulation |
| `conformite_reglementaire` | Conformité aux normes et règlements |

Le mapping chunks → compétences est déterministe par mots-clés (`skill_mapper.py`).
Un chunk peut être associé à plusieurs compétences. La `confidence` indique la
qualité du mapping.

---

## 8. Corpus personnalisés

Un corpus est un sous-ensemble nommé de documents. Il permet de cibler
l'entraînement, les analytics et les suggestions de révision sur une thématique précise.

### Fonctionnement

```
Utilisateur crée "VO583" (3 documents sélectionnés)
        │
        ▼
corpus.id enregistré en DB
        │
        ▼
Corpus activé → st.session_state["active_corpus_id"]
        │
        ├── tab_training.py  — questions générées sur les docs du corpus
        ├── tab_dashboard.py — analytics filtrées sur document_ids du corpus
        └── tab_history.py   — (fallback : all docs si corpus inactif)
```

### Sentinels internes (tab_training.py)

| Valeur | Signification |
|---|---|
| `_CORPUS = -1` | Tous les documents (comportement existant) |
| `_NAMED_CORPUS = -2` | Corpus nommé actif |

Ces valeurs ne sont jamais des IDs SQLite valides (AUTOINCREMENT part de 1).

### API `db/corpus.py`

```python
create_corpus(user_id, corpus_name, document_ids) -> int
get_user_corpus(user_id) -> list[dict]         # inclut n_docs
get_corpus_documents(corpus_id) -> list[int]
get_corpus_by_id(corpus_id, user_id?) -> dict|None
delete_corpus(corpus_id, user_id) -> bool
```

Le corpus actif est stocké en `session_state` (MVP — pas de persistance DB).
Si `active_corpus_id` est `None`, le comportement existant est inchangé.

---

## 9. Système de rôles

### Navigation par rôle

| Rôle | Onglets visibles |
|---|---|
| `apprenant` | Entraînement · Historique · Dashboard · Corpus · Moteur IA |
| `formateur` | + Documents · Formateur |
| `admin` | + Admin |
| Mode présentation | Entraînement · Dashboard · Moteur IA |

### Apprenant

- Sélectionne un document ou active un corpus pour s'entraîner.
- Consulte son dashboard personnel (scores, profil, notions fragiles).
- Crée et gère ses corpus personnalisés.
- Consulte son historique de tentatives.

### Formateur

- Importe et gère les documents du corpus organisationnel.
- Accède au cockpit pédagogique de cohorte.
- Suit la progression des apprenants (scores, profils, alertes).

### Administrateur

- Gère les comptes utilisateurs et les promotions de rôle.
- Accède aux outils CLI d'administration.

### Création du premier administrateur

```bash
# Option 1 — interface one-shot (apparaît si aucun admin en DB)
# Onglet "Premier administrateur" au démarrage

# Option 2 — CLI (recommandé en production)
python tools/admin/create_admin.py

# Reset mot de passe
python tools/admin/reset_password.py
```

---

## 10. QA, observabilité et outils internes

### Global System Auditor

Audit complet du système en lecture seule — 10 sections, score /100, verdict coloré.

```bash
python tools/qa/global_system_auditor.py
python tools/qa/global_system_auditor.py --verbose
python tools/qa/global_system_auditor.py --check-calibration --run-tests
```

**Score actuel : 99/100** (WARNING résiduel : SENTRY_DSN absent en local — config prod).

| Section | Pts | Contenu |
|---|---|---|
| STRUCTURE | 15 | fichiers clés, py_compile, imports, seuils moteur |
| DATABASE | 20 | tables, index, orphelins, colonnes |
| CORPUS | 15 | cohérence corpus/documents |
| LEARNING | 15 | scores, error_types, question_types |
| CHUNKS | 0* | couverture, longueurs, skills par doc |
| SKILLS | 10 | V1.0, thresholds, mastery_score |
| RUNTIME | 10 | latences, fallback rate, taux erreur |
| CALIBRATION | 0* | scripts présents, suite runner |
| SECURITY | 10 | .env, clés API, DB size, backup, Docker |
| TESTS | 5 | présence + exécution optionnelle |

*Sections informatives, sans impact sur le score.

La connexion DB est toujours ouverte en `mode=ro` — aucune écriture possible pendant l'audit.
Le rapport markdown est généré dans `reports/global_audit_YYYYMMDD_HHMM.md`.

### Test de robustesse 100 questions

```bash
python tools/qa/test_robustesse_100q.py --mock --no-confirm
# Simule 100 cycles (génération → correction → sauvegarde → profil)
# Verdict : GO SAFE | GO WITH WARNING | FAILED
```

### Simulation moteur adaptatif

```bash
python tools/testing/simulate_adaptive_training.py --n 50 --mock
# Simule n sessions, vérifie la distribution mastery, les types de questions, le fallback
```

### Audit des compétences

```bash
python tools/observability/audit_skills_empirique.py --username test
# Audit read-only : couverture, mastery, discrimination, patterns émergents
```

### Rapport de progression HTML

```bash
python tools/reports/generate_learning_report.py --username alice
# Génère reports/rapport_alice_YYYYMMDD.html
```

### Monitoring runtime

Les appels LLM sont enregistrés dans `logs/ai_requests.jsonl` (gateway).
Les métriques de latence, fallback et erreurs sont disponibles dans l'onglet
**Moteur IA** et dans `runtime_metrics` en DB.

---

## 11. Tests automatisés

```bash
# Suite complète (262 tests — ~6 secondes)
python -m pytest test_regression.py test_integration.py test_auth_service.py -v

# Régression uniquement
python -m pytest test_regression.py -q

# Vérification rapide de la calibration moteur
python tools/testing/run_training_calibration_suite.py --quick
```

**Couverture :** auth, RAG, analytics, répétition espacée, profils, Skills Engine,
corpus, mastery classification, adaptive difficulty, review intervals, calibration tripwires.

**Tripwires calibration** : `TestReviewIntervalsCoherence` dans `test_regression.py`
détecte toute divergence entre `engine/thresholds.py` et la logique SQL de
`db/chunks.get_revision_suggestion`. Toute modification des seuils doit passer ces tests.

---

## 12. Déploiement Railway

### Prérequis

- Repo GitHub (public ou privé)
- Compte Railway (railway.app — plan Starter gratuit suffisant pour 10 testeurs)

### Étapes

**1. Push le code sur GitHub**

```bash
gh repo create addisco-ops --private --source=. --remote=origin --push
# ou manuellement :
git remote add origin https://github.com/MON_USERNAME/addisco-ops.git
git push -u origin main
```

**2. Créer le projet Railway**

Railway → New Project → Deploy from GitHub repo → sélectionner `addisco-ops`.
Railway détecte le Dockerfile automatiquement via `railway.toml`.

**3. Ajouter le Volume persistant (critique)**

Railway → onglet service → Add Volume :
- Mount path : `/app/data`
- Taille : 1 GB

Sans ce volume, la base de données est effacée à chaque redéploiement.

**4. Variables d'environnement**

| Variable | Valeur | Obligatoire |
|---|---|---|
| `OPENAI_API_KEY` | `sk-proj-...` | Oui |
| `DB_PATH` | `/app/data/database.db` | Oui |
| `APP_PASSWORD` | mot de passe testeurs | Recommandé |
| `SENTRY_DSN` | DSN Sentry | Non |
| `APP_ENV` | `production` | Non |

Railway injecte `PORT` automatiquement — `railway.toml` l'utilise via `$PORT`.

**5. Déploiement automatique**

Chaque `git push origin main` déclenche un redéploiement automatique.

### Architecture production Railway

```
GitHub (main branch)
        │ push
        ▼
Railway CI — docker build
        │
        ▼
Container Docker (python:3.12-slim)
  /app/                   ← code applicatif (image)
  /app/data/database.db   ← Volume Railway (persistant)
        │
        ▼
URL publique Railway (HTTPS automatique)
```

---

## 13. Lancement local

### Prérequis

- Python 3.12+
- Clé API OpenAI (modèles `gpt-4o-mini` et `text-embedding-3-small`)

### Installation

```bash
git clone <url-du-repo>
cd addisco-ops

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Renseigner dans .env :
# OPENAI_API_KEY=sk-proj-...
# APP_PASSWORD=mot_de_passe_optionnel
```

### Démarrage

```bash
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`. Au premier lancement,
un document de démonstration est automatiquement importé.

### Docker local

```bash
docker-compose up --build
# Application disponible sur http://localhost:8501
# database.db persistée dans le répertoire courant via volume
```

### Mode fallback (sans clé API)

Sans `OPENAI_API_KEY`, l'application passe automatiquement en mode fallback :
les questions sont générées depuis le texte brut des chunks (sans RAG ni LLM).
Toutes les fonctionnalités de suivi, profil et analytics restent opérationnelles.

---

## 14. Stack technique

| Composant | Technologie | Version |
|---|---|---|
| Interface | Streamlit | 1.57.0 |
| LLM | OpenAI gpt-4o-mini | API v2 |
| Embeddings | OpenAI text-embedding-3-small | 1 536 dims |
| Base de données | SQLite (stdlib) | WAL mode |
| Recherche vectorielle | numpy — similarité cosinus | ≥1.26.0 |
| Graphiques | Plotly | 6.7.0 |
| Authentification | bcrypt | 5.0.0 |
| Import PDF | pypdf | 6.11.0 |
| Import DOCX | python-docx | 1.2.0 |
| Monitoring | sentry-sdk | ≥2.0.0 |
| Tests | pytest | — |
| Conteneurisation | Docker / docker-compose | — |
| Déploiement | Railway | — |
| Langage | Python | 3.12 |

---

## 15. État du projet

### Stable et démontrable — Phase 20 · Railway en production

- **Déployé en production** sur Railway avec volume persistant (`/app/data`)
- Authentification multi-utilisateur bcrypt avec rôles (apprenant / formateur / admin)
- Import PDF / DOCX / TXT + embeddings automatiques (text-embedding-3-small, 1 536 dims)
- Pipeline RAG complet — recherche sémantique cross-documents (cosinus numpy)
- Génération de questions (6 types pédagogiques) et correction structurée par LLM
- Répétition espacée avec seuils calibrés empiriquement (GO SAFE validé)
- Corpus personnalisés — entraînement et analytics filtrés par thématique
- Dashboard dark premium avec analytics Plotly (momentum, velocity, rétention J+1/J+7/J+30)
- Skills Engine V1.0 — 10 compétences, mapping déterministe par mots-clés
- Global System Auditor — 10 sections, **score 99/100**
- AI Gateway — rate limiting, logging JSONL, monitoring Sentry
- Fallback mode automatique (texte brut) si API indisponible
- **262 tests de régression** — couverture moteur complète (~6 secondes)

### Limites assumées

- **SQLite** : stable pour ~10 utilisateurs simultanés. Migration PostgreSQL prévue
  si la cohorte dépasse 50 utilisateurs actifs.
- **Skills Engine V1.0** : mapping déterministe par mots-clés. Efficace sur un corpus
  structuré ; ne constitue pas un moteur d'inférence par apprentissage automatique.
- **Métriques de rétention J+7/J+30** : calculables dès le démarrage, interprétables
  seulement après plusieurs semaines d'usage réel.
- **Corpus actif** : stocké en `session_state` (perdu à la déconnexion). Persistance
  DB non implémentée — à évaluer selon le besoin validé.
- **Cockpit formateur** : métriques de cohorte fonctionnelles ; indicateurs de
  comparaison inter-apprenants nécessitent une cohorte réelle suffisante.

### Prochaines étapes

1. **Tests humains** sur 10 testeurs réels (données réelles nécessaires pour valider les intervalles Ebbinghaus)
2. **GitHub Actions CI** — pipeline automatique sur `push main` (py_compile + pytest)
3. **Skills Engine V2** — cartographie par LLM au lieu de mots-clés déterministes
4. **PostgreSQL + pgvector** si la cohorte dépasse 50 utilisateurs actifs simultanés

---

*ADDISCO OPS — Phase 20 · Déployé Railway · 262 tests · Auditor 99/100*
