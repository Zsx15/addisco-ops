# ROADMAP — Projet IA Révision / RAG / Adaptatif

## Phase 0 — Point de départ

Objectif : obtenir un prototype simple qui fonctionne.

Livrables :
- app Streamlit fonctionnelle ;
- génération de question ;
- correction IA ;
- score ;
- historique SQLite.

Critère de réussite :
- l’utilisateur peut coller un texte, répondre à une question et voir une correction enregistrée.

---

## Phase 1 — Stabilisation du prototype

Objectif : rendre le code propre et maintenable.

Tâches :
- créer `database.py` ;
- créer `ai_service.py` ;
- créer `utils.py` ;
- isoler la logique IA ;
- isoler la logique base de données ;
- ajouter `requirements.txt` ;
- ajouter `.env.example` ;
- améliorer README.

Critère de réussite :
- `app.py` devient plus lisible ;
- les fonctions principales sont séparées ;
- l’application se lance sans erreur.

---

## Phase 2 — Historique enrichi

Objectif : rendre les données exploitables.

Ajouter aux tentatives :
- question ;
- réponse utilisateur ;
- correction ;
- score ;
- date ;
- notion ;
- type d’erreur ;
- temps de réponse ;
- mode pédagogique utilisé.

Critère de réussite :
- l’historique permet de repérer les erreurs fréquentes.

---

## Phase 3 — Analyse des erreurs

Objectif : passer de “score” à “diagnostic pédagogique léger”.

Types d’erreurs :
- oubli d’étape ;
- confusion de notion ;
- réponse trop vague ;
- erreur d’ordre ;
- erreur d’exception ;
- mauvaise priorité ;
- réponse hors sujet.

Critère de réussite :
- chaque correction stocke un type d’erreur exploitable.

---

## Phase 4 — Import documentaire

Objectif : ne plus dépendre uniquement du copier-coller.

Fonctions :
- importer PDF ;
- importer DOCX ;
- extraire texte ;
- nettoyer texte ;
- stocker document en base.

Critère de réussite :
- un document importé peut servir de source aux questions.

---

## Phase 5 — Découpage documentaire

Objectif : préparer le RAG.

Découpage :
- par titre ;
- par paragraphe ;
- par section logique ;
- par procédure ;
- par règles / exceptions.

Critère de réussite :
- le document est découpé en chunks propres et réutilisables.

---

## Phase 6 — Embeddings et base vectorielle

Objectif : ajouter la recherche sémantique.

Fonctions :
- créer embeddings ;
- stocker chunks + vecteurs ;
- rechercher les passages proches d’une question.

Base vectorielle possible :
- Qdrant local ;
- Chroma pour prototype ;
- Milvus pour version avancée.

Critère de réussite :
- une question retrouve les passages pertinents du document.

---

## Phase 7 — RAG complet

Objectif : générer questions et corrections depuis les passages retrouvés.

Pipeline :
1. question ou objectif ;
2. recherche sémantique ;
3. récupération des chunks ;
4. génération de réponse contextualisée ;
5. correction avec source.

Critère de réussite :
- la réponse IA est ancrée dans le document.

---

## Phase 8 — Apprentissage adaptatif

Objectif : adapter la pédagogie selon les résultats.

Données observées :
- scores ;
- erreurs ;
- temps de réponse ;
- réussite après reformulation ;
- mode pédagogique utilisé.

Modes pédagogiques :
- logique ;
- procédural ;
- narratif ;
- analogique ;
- synthétique ;
- schématique.

Critère de réussite :
- le système change de forme d’explication si l’utilisateur bloque.

---

## Phase 9 — Répétition espacée

Objectif : mieux mémoriser.

Fonctions :
- détecter notion fragile ;
- programmer révision ;
- prioriser les erreurs récurrentes ;
- espacer les rappels selon la réussite.

Critère de réussite :
- l’utilisateur révise davantage ce qu’il oublie.

---

## Phase 10 — Industrialisation

Objectif : préparer une version entreprise.

Fonctions :
- authentification ;
- multi-utilisateur ;
- dashboard formateur ;
- exports ;
- logs ;
- sécurité ;
- Docker ;
- tests automatisés ;
- monitoring.

Critère de réussite :
- le projet peut être présenté comme base industrielle.

**Phase 10 — COMPLÈTE.** Commit `8b9354a`. Backup stable : `BACKUP_DEMO_STABLE_ai-v2_2026-05-16_17-24`.

---

# Roadmap industrielle — Phase 11 à 17

## Philosophie progressive

Chaque phase laisse le produit plus solide et plus démontrable qu'avant.
Aucune phase ne casse la précédente.
Le moteur pédagogique et la stabilité sont non-négociables à chaque étape.

Principes :
- étapes petites et validables ;
- tests après chaque tâche ;
- aucun refactor massif ;
- pas de modification destructrice ;
- priorité stabilité > features ;
- backup démo stable préservé.

---

## Phase 11 — Socle architectural sain

Objectif : aligner le code réel sur l'architecture documentée (ARCHITECTURE.md).
Aucune fonctionnalité ajoutée — uniquement clarté et maintenabilité.

Dépendance : Phase 10 complète.

Tâches :
- TASK-038 : solder dettes résiduelles (`str | None` dans `ai_service.py` + `ui_helpers.py`,
  résoudre `config.py`, unifier `_PEDAGOGY_GROUPS` / `_PROFILE_TYPES`) ;
- TASK-039 : extraire `rag_service.py` — sortir `search_similar_chunks`, `_cosine_similarity`,
  `_blob_to_vector` de `database.py` ;
- TASK-040 : modulariser `app.py` en fichiers d'onglets (`tabs/tab_training.py`,
  `tab_dashboard.py`, `tab_documents.py`, `tab_history.py`, `tab_engine.py`,
  `tab_trainer.py`) — `app.py` devient un routeur < 150 lignes.

Critère de sortie :
- `app.py` < 150 lignes ;
- `rag_service.py` existant et importé ;
- zéro dette résiduelle connue ;
- 77/77 tests OK.

Risques :
- modularisation `app.py` peut introduire des régressions Streamlit (session_state partagé) ;
  mitigation : migration onglet par onglet avec test Streamlit headless après chaque onglet.

**Phase 11 — COMPLÈTE.** Commit `5876c03`. TASK-038 → 040 soldés. `rag_service.py` extrait, `app.py` modulaire (tabs/), dettes `str | None` soldées.

---

## Phase 12 — Authentification réelle

Objectif : remplacer le `text_input` user_id et l'`APP_PASSWORD` unique
par un vrai système d'identité multi-rôles.

Dépendance : Phase 11 complète (`app.py` modulaire facilite l'ajout du bloc auth).

Tâches :
- TASK-041 : table `users` — migration douce `CREATE TABLE IF NOT EXISTS`
  (`user_id`, `username`, `password_hash` bcrypt, `role`, `created_at`) ;
- TASK-042 : `auth_service.py` — `register_user()`, `verify_password()`,
  `get_user_by_username()` — fonctions pures testables, bcrypt ;
- TASK-043 : remplacement du bloc login dans `app.py` — formulaire register/login,
  `session_state.user_id` ← `users.id`, mode démo préservé si aucun user en base ;
- TASK-044 : rôles actifs — formateur voit gestion documents + onglet Formateur,
  admin voit stats globales, apprenant voit son dashboard uniquement.

Critère de sortie :
- tout utilisateur possède un compte, un mot de passe haché, un rôle ;
- `user_id` n'est plus saisissable librement ;
- mode démo sans compte préservé (fallback) ;
- 10+ tests unitaires sur `auth_service.py`.

Risques :
- migration douce `users` : si `user_id` existants en base ne correspondent pas
  aux nouveaux comptes → plan de migration des données historiques nécessaire.

**Phase 12 — COMPLÈTE.** Commit `1e0691f`. TASK-041 → 044 soldés. Table `users`, `auth_service.py` (bcrypt), formulaire login/register, rôles actifs (apprenant / formateur / admin). Mode démo préservé.

---

## Phase 13 — Base de données scalable

Objectif : passer de SQLite fichier local à une base relationnelle production,
sans casser l'existant.

Dépendance : Phase 12 complète (la table `users` doit être conçue pour PostgreSQL dès le départ).

Tâches :
- TASK-045 : introduire SQLAlchemy Core dans `database.py` — remplacer `sqlite3.connect()`
  par un engine SQLAlchemy, SQLite reste le défaut, comportement identique ;
- TASK-046 : support PostgreSQL via `DATABASE_URL` — si variable présente → PostgreSQL,
  sinon SQLite ; migrations versionnées avec Alembic (réversibles) ;
- TASK-047 : embeddings dans PostgreSQL avec pgvector — `search_similar_chunks()`
  utilise `<=>` (cosinus natif) si PostgreSQL, fallback Python pur si SQLite.

Critère de sortie :
- l'application tourne sur PostgreSQL en production et SQLite en développement ;
- aucune différence de comportement visible ;
- 77/77 tests OK sur SQLite, smoke test sur PostgreSQL.

Risques :
- SQLAlchemy Core est un changement profond de `database.py` ;
  mitigation : garder les signatures de fonctions identiques, changer uniquement
  l'implémentation interne ; les tests existants valident la non-régression.

**Phase 13 — DIFFÉRÉE.** Décision `b66af9b`. SQLAlchemy / PostgreSQL reporté jusqu'à disponibilité d'une `DATABASE_URL` réelle. TASK-045 et TASK-046 combinables en une migration unique le moment venu. TASK-047 (pgvector) suit automatiquement. Stack SQLite + numpy reste officielle en attendant.

---

## Phase 14 — Moteur pédagogique complet

Objectif : matérialiser `adaptive_engine.py` planifié dans ARCHITECTURE.md
et enrichir le moteur avec des métriques de rétention réelles.

Dépendance : Phase 11 (rag_service.py extrait), Phase 13 (base scalable pour les calculs de cohorte).

Tâches :
- TASK-048 : créer `adaptive_engine.py` — y déplacer `classify_mastery`,
  `_adaptive_interval`, `compute_and_save_learning_profile`, `_MASTERY_BIAS`,
  `_PEDAGOGY_GROUPS` depuis `database.py` et `ai_service.py` ;
- TASK-049 : profil utilisateur enrichi — ajouter `momentum` (vitesse de progression
  sur 7 jours), `learning_velocity` (delta score moyen), `consistency_score`
  (régularité des sessions) ;
- TASK-050 : `get_next_session_plan(user_id)` — liste ordonnée de chunks à réviser
  avec durée estimée et objectif pédagogique ;
- TASK-051 : métriques de rétention — taux à J+1 / J+7 / J+30, efficacité par type
  de question, ratio tentatives/maîtrise.

Critère de sortie :
- `adaptive_engine.py` existant, autonome, testable sans Streamlit ;
- métriques de rétention calculables et affichées dans le Dashboard ;
- 77/77 tests OK + 15+ nouveaux tests sur `adaptive_engine.py`.

Risques :
- extraction de `adaptive_engine.py` implique des modifications dans `database.py`
  et `ai_service.py` — risk de casser les imports ;
  mitigation : extraire par copie d'abord, vérifier les tests, supprimer les originaux ensuite.

**Phase 14 — COMPLÈTE.** Commit `82c8b55`. TASK-048 → 051 soldés. `adaptive_engine.py` extrait en module `engine/`. Profil enrichi (momentum, learning_velocity, consistency_score), plan de session adaptatif, métriques de rétention J+1 / J+7 / J+30 dans le Dashboard.

---

## Phase 15 — Multi-documents et corpus

Objectif : passer d'un document par session à un corpus complet géré par l'utilisateur.

Dépendance : Phase 13 (PostgreSQL pour performances cross-documents),
Phase 14 (moteur adaptatif capable de raisonner sur plusieurs sources).

Tâches :
- TASK-052 : support DOCX dans `document_service.py` — `python-docx`,
  même pipeline qu'existant ;
- TASK-053 : catégories de documents — colonne `category` dans `documents`,
  filtre dans Entraînement et Documents ;
- TASK-054 : entraînement cross-documents — `generate_question()` accepte
  une liste de `document_id` et sélectionne le chunk le plus prioritaire parmi tous ;
- TASK-055 : recherche sémantique cross-documents — `search_similar_chunks()`
  accepte `document_ids=None` → recherche sur tout le corpus autorisé.

Critère de sortie :
- un utilisateur peut créer un corpus de plusieurs documents et s'entraîner dessus
  comme sur un seul ;
- la recherche sémantique fonctionne cross-documents ;
- DOCX importable.

Risques :
- performances cross-documents sur SQLite : acceptable jusqu'à ~50 documents,
  bottleneck au-delà → mitigation par Phase 13 (pgvector).

**Phase 15 — COMPLÈTE.** Commit `21e8e40`. TASK-052 → 055B soldés. Support DOCX, catégories de documents, entraînement cross-documents, RAG corpus complet (`search_similar_chunks_multi`), contexte RAG visible en UI. Architecture segmentée (`engine/`, `db/`, `ai_gateway`). 227/227 tests.

---

## Phase 16 — Consolidation pédagogique / Analytics / UX  ← PHASE ACTUELLE

Objectif : moteur pédagogique explicable, robuste et calibrable.
Chaque livrable renforce la confiance dans les décisions du moteur.

Dépendance : Phase 15 complète (corpus multi-documents opérationnel).

### Historique réel — TASK-051 à TASK-059 DONE

| Task | Titre | Commit | Statut |
|------|-------|--------|--------|
| TASK-051 | Sources visibles / contexte pédagogique | `8aebae7` | DONE |
| TASK-051B | Consolidation UX profil pédagogique | `f31f117` | DONE |
| TASK-052 | Score de confiance correction V1 | `d56a087` | DONE |
| TASK-053 | Rejet hors sujet / non évaluable | `9f98dbb` | DONE |
| TASK-054 | Chunk Quality Analyzer V1 | `b39bc6e` | DONE |
| TASK-055 | Skill Graph Engine V1 | `3eaf9b4` | DONE |
| TASK-056A | Simulateur session pédagogique réelle | `2909343` | DONE |
| TASK-056 | Adaptive Difficulty Engine V2 | `412101e` | DONE |
| TASK-056B | Centralisation seuils mastery + filtre non_evaluable | `f556673` | DONE |
| TASK-057A | Correction Map observabilité | `bd2d044` | DONE |
| TASK-057 | Error Pattern Memory V1 | `4a6c69c` | DONE |
| TASK-057B | Script vérification session 30Q | `7413854` | DONE |
| TASK-058 | Curriculum Engine V1 | `0c750cc` | DONE |
| TASK-058B | Script vérification alignement Curriculum Engine | `8f7b5e3` | DONE |
| TASK-059 | Runtime Curriculum Arbitration | `ce5e88b` | DONE |

### Tâches Phase 16

| Task | Titre | Commit | Statut |
|------|-------|--------|--------|
| TASK-060 | Maintenance Assistée V1 | `690fa07` | DONE |
| TASK-061 | Vue admin | `bc8f50f` | DONE |
| TASK-062 | Rapports HTML/PDF | `56f3981` | DONE |
| TASK-063 | UX responsive tablette | `079298a` | DONE |

**Phase 16 — COMPLÈTE.** Commits `690fa07` → `079298a`. Maintenance assistée (6 sections, verdict GO/WARNING/FAILED), vue admin (KPIs globaux, gestion utilisateurs, alertes système), rapports pédagogiques HTML (7 sections, CSS inline, export PDF), UX responsive tablette + mode présentation.

---

## Phase 17 — Production Readiness

Objectif : déploiement zéro-friction, monitoring, résilience, CI/CD complet.

Dépendance : Phase 16 complète.

Note de numérotation : les tâches Phase 17 commencent à TASK-064 pour éviter
toute collision avec les tâches Phase 16 restantes (TASK-060 à TASK-063).

| Task | Titre | Commit | Statut |
|------|-------|--------|--------|
| TASK-064 | Tests d'intégration complets | `9ca1bed` | DONE |
| TASK-065 | Rate limiting LLM | `698dbe5` | DONE |
| TASK-066 | Monitoring applicatif (Sentry) | `ec034a2` | DONE |
| TASK-067 | CI/CD complet | `11369b8` | DONE |

**Docker livré — 2026-05-20.**
`docker compose up --build` opérationnel. Image `python:3.11-slim`, bind mounts `database.db` + `docs`, `env_file .env`, HTTP 200 OK validé. Commits `3741e82` + `d6128f3`.

**Phase 17 — COMPLÈTE.** Commits `9ca1bed` → `11369b8`. Tests d'intégration 24 cas end-to-end, rate limiting sliding window per-user/per-type, Sentry LoggingIntegration, CI/CD py_compile exhaustif (100 fichiers auto) + numpy explicite.

---

## Phase 18 — Observabilité LLM et Calibration Moteur

Objectif : instrumenter le pipeline LLM, rendre le moteur auditable et calibrable par données réelles.

Dépendance : Phase 17 complète.

### Phase 18A — Observabilité LLM avancée

| Task | Titre | Commit | Statut |
|------|-------|--------|--------|
| TASK-068 | Runtime metrics DB (`db/runtime_metrics.py`) | `7dac9df` | DONE |
| TASK-069 | Gateway instrumenté (latence/tokens/coût/fallback) | `7dac9df` | DONE |
| TASK-070 | CLI runtime analytics (5 sections, verdict OK/WARNING/CRITICAL) | `7dac9df` | DONE |
| TASK-071 | tab_admin — section Observabilité Runtime 8 KPIs | `7dac9df` | DONE |
| TASK-072 | Tendances historiques Plotly (24h + 7j, 8 charts) | `4a5fb49` | DONE |

### Phase 18B — Simulation et calibration

| Task | Titre | Commit | Statut |
|------|-------|--------|--------|
| TASK-073 | Simulation contrôlée moteur adaptatif (mock + API) | `fa994ac` | DONE |
| TASK-074 | Engine Calibration Harness (5 séquences, SEQ-C révèle MIN_ATTEMPTS) | `6b54cea` | DONE |
| TASK-074B | MASTERY_MIN_ATTEMPTS calibration 3 → 5 (validée SEQ-C) | `897824d` | DONE |

### Phase 18C — Calibration complète des seuils moteur

| Task | Titre | Commit | Statut |
|------|-------|--------|--------|
| TASK-075 | Mastery Boundary Calibration (FRAGILE + MASTERED) | `95ff428` | DONE |
| TASK-076 | Adaptive Difficulty Calibration (FORCE_EASY + ALLOW_HARD) | `214c4de` | DONE |
| TASK-077 | Review Intervals Calibration (REVIEW_INTERVALS + sensibilité) | `ab81614` | DONE |

**Phase 18C — COMPLÈTE.** Tous les 6 seuils de `engine/thresholds.py` validés par harness de calibration isolé (DB temporaire, patch en mémoire, aucune modification du fichier source). Conclusion : MASTERY_FRAGILE=0.60, MASTERY_MASTERED=0.80, MASTERY_MIN_ATTEMPTS=5, ADAPTIVE_FORCE_EASY=0.40, ADAPTIVE_ALLOW_HARD=0.65, REVIEW_INTERVALS=1/3/7 — tous confirmés corrects.

**Phase 18 — COMPLÈTE.** Commits `7dac9df` → `ab81614`. Table `runtime_metrics`, gateway instrumenté, CLI analytique, dashboard admin enrichi (8 KPIs + 8 charts Plotly), simulation contrôlée (mock/API, profils pondérés, verdict COHERENT/WARNING/REGRESSION), calibration harness (5 séquences backdatées, injection SQL directe), MASTERY_MIN_ATTEMPTS validé à 5, calibration complète des 6 seuils moteur (18C).

---

# Vision produit cible

## Ce que devient ADDISCO OPS

Un SaaS pédagogique B2B permettant à toute organisation de créer
un corpus documentaire intelligent et de former ses collaborateurs
par révision adaptative basée sur l'IA.

## Architecture modulaire cible

```
app.py              — routeur Streamlit (< 150 lignes)
tabs/               — un fichier par onglet
auth_service.py     — authentification, hachage, rôles
database.py         — accès données (SQLAlchemy, SQLite/PostgreSQL)
ai_service.py       — LLM, embeddings, génération, correction
rag_service.py      — chunking, recherche vectorielle, retrieval
adaptive_engine.py  — profil utilisateur, biais pédagogiques, répétition espacée
document_service.py — import, extraction, nettoyage, réindexation
ui_helpers.py       — rendu HTML, validation, explainability
logger.py           — logging structuré avec rotation
```

## Authentification réelle

- Comptes utilisateurs avec mot de passe haché (bcrypt).
- Rôles : apprenant / formateur / admin.
- Sessions sécurisées via Streamlit session_state.
- Mode démo préservé (sans compte requis).

## Base de données

- SQLite en développement (zéro configuration).
- PostgreSQL en production (scalable, concurrent, robuste).
- pgvector pour la recherche sémantique native (cosinus indexé).
- Migrations versionnées via Alembic (réversibles, auditables).

## Moteur adaptatif

- Profil pédagogique par utilisateur (4 dimensions + momentum + velocity).
- Répétition espacée modulée par tendance et maîtrise.
- Biais de question adaptatif (mastery + profil + rotation).
- Plan de session personnalisé calculable à la demande.
- Métriques de rétention J+1 / J+7 / J+30.

## Corpus multi-documents

- Import PDF, TXT, DOCX.
- Catégorisation des documents par domaine métier.
- Entraînement cross-documents sur un corpus complet.
- Recherche sémantique sur l'intégralité du corpus autorisé.

## UX SaaS B2B

- Interface apprenant : entraînement guidé, dashboard de progression, explainability.
- Interface formateur : suivi de cohorte, comparaison, export rapport PDF.
- Interface admin : gestion utilisateurs, documents, stats globales.
- Responsive, mode présentation, rapport automatique hebdomadaire.

## Monitoring et CI/CD

- Sentry pour les erreurs en production.
- Métriques d'usage : appels LLM, latence, taux d'erreur par utilisateur.
- Rate limiting par utilisateur sur les appels API.
- CI GitHub Actions : tests + py_compile + déploiement automatique.
- Docker standardisé : déploiement reproductible sur tout hébergeur.
