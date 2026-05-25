# ADDISCO OPS — Dossier Technique
## À destination des équipes engineering

---

## Vue d'ensemble

ADDISCO OPS est une application SaaS pédagogique construite en Python/Streamlit, SQLite et API OpenAI. Elle implémente un pipeline RAG (Retrieval-Augmented Generation) couplé à un moteur d'apprentissage adaptatif fondé sur la répétition espacée.

Le projet compte **20 phases documentées**, chacune avec objectif, livrables et critères de réussite mesurables. Le moteur pédagogique est complet et stable depuis la Phase 11. Les phases 12 à 20 couvrent la robustesse, l'observabilité, le déploiement et la qualité RAG.

**Stack technique :**

| Couche | Technologie |
|--------|-------------|
| Frontend / routing | Python 3.11 — Streamlit 1.57 |
| Persistance | SQLite (numpy BLOB pour embeddings) |
| LLM | OpenAI gpt-4o-mini + text-embedding-3-small |
| Containerisation | Docker — docker-compose |
| CI/CD | GitHub Actions |
| Observabilité | Sentry — logs JSONL — dashboard Plotly |
| Auth | bcrypt — python-dotenv |
| Import documents | pypdf — python-docx |

---

## Architecture

```
app.py                      ← routeur Streamlit, auth, session state
├── tabs/                   ← un fichier par onglet (9 onglets)
├── ai_service.py           ← RAG pipeline, génération, correction
├── rag_service.py          ← recherche vectorielle cosinus (numpy)
│                              + compute_retrieval_overlap()
├── chunk_quality_analyzer.py ← heuristique TRUNC, qualité chunking
├── adaptive_engine.py      ← façade de compatibilité → engine/
├── engine/                 ← moteur pur — zéro import projet
│   ├── thresholds.py       ← source unique de vérité des seuils
│   ├── spaced_rep.py       ← répétition espacée + classify_mastery
│   ├── question_type.py    ← sélection adaptative des types
│   ├── adaptive_difficulty.py
│   ├── curriculum_engine.py
│   └── skill_engine.py
├── database.py             ← couche accès données + re-exports backward compat
├── db/                     ← modules DB segmentés
│   ├── analytics.py        ← attempts CRUD
│   ├── chunks.py           ← documents, chunks, embeddings
│   ├── profile.py          ← profil pédagogique utilisateur
│   ├── admin.py            ← gestion utilisateurs/rôles
│   ├── corpus.py           ← corpus personnalisés multi-documents
│   ├── sessions.py         ← session tracking
│   └── runtime_metrics.py  ← métriques LLM
├── ai_gateway/             ← couche d'accès API OpenAI
│   ├── gateway.py          ← appels chat + embeddings
│   ├── rate_limiter.py     ← sliding window par (user_id, task_type)
│   └── request_logger.py   ← logs JSONL par appel
├── auth_service.py         ← bcrypt, rôles, promote_user
├── document_service.py     ← import PDF/DOCX, chunking, seed
├── seed_presentation.py    ← seed démo — sessions et tentatives simulées
└── ui_helpers.py           ← rendu HTML, sanitize, explainability
```

**Contrainte architecturale critique :** `engine/` est un module pur — aucun import projet. Il est testable et exécutable sans Streamlit, sans base de données, sans API. C'est la garantie que le moteur pédagogique reste testable de façon isolée.

---

## Pipeline RAG

```
1. Import document (PDF / DOCX / TXT)
   → document_service.py : extraction texte, nettoyage, chunking (~500 chars, par section)
   → ai_service.generate_embedding() : appel text-embedding-3-small
   → db/chunks.py : stockage BLOB float32 little-endian dans SQLite (1 536 dimensions)

2. Génération de question (session utilisateur)
   → source_text → _call_embedding_api() → vecteur requête
   → rag_service.search_similar_chunks() : cosinus numpy sur tous les chunks en mémoire
   → top-K chunks retenus (K=3 par défaut)
   → ai_service.generate_question() : prompt LLM avec contexte RAG injecté

3. Correction de la réponse
   → correct_answer() : pré-validation déterministe (_check_answer_evaluable)
   → si évaluable → appel LLM → JSON structuré (score, correction, error_type, topic)
   → save_attempt() → persistance + mise à jour profil utilisateur

4. Mesure de la qualité RAG (Phase 20)
   → compute_retrieval_overlap() : score 0.0–1.0 (recouvrement lexical question ↔ chunks)
   → stocké dans attempts.retrieval_overlap_score à chaque tentative
   → chunk_quality_analyzer.py : heuristique TRUNC — détecte chunks tronqués
     (début minuscule = coupe milieu de phrase, fin sans ponctuation = suite coupée)
```

**Fallback garanti :**
- Si le RAG échoue → `generate_question` utilise `source_text` brut
- Si l'API LLM est indisponible → `correct_answer` retourne `_CORRECT_FALLBACK`
- `fallback_used` est tracé dans `runtime_metrics` à chaque événement

---

## Moteur adaptatif

### Classification de maîtrise (`engine/spaced_rep.py — classify_mastery`)

Chaque chunk est classé selon l'historique des tentatives :

| Classe | Condition |
|--------|-----------|
| Fragile | `avg_score < 0.60` |
| En consolidation | `0.60 ≤ avg_score < 0.80` ou `attempts < 5` |
| Maîtrisé | `avg_score ≥ 0.80` ET `attempts ≥ 5` |

Seuils validés empiriquement via le harness Phase 18C (5 séquences, DB temporaire isolée, séquences backdatées pour simuler l'espacement temporel).

### Répétition espacée (`engine/spaced_rep.py — _adaptive_interval`)

| Classe | Tendance | Intervalle |
|--------|----------|------------|
| Fragile | Amélioration | 2 jours |
| Fragile | Stable / Dégradation | 1 jour |
| En consolidation | Amélioration | 5 jours |
| En consolidation | Dégradation | 2 jours |
| En consolidation | Stable | 3 jours |
| Maîtrisé | — | 7 jours |

### Sélection du type de question (`engine/question_type.py`)

6 types : `question_directe`, `cas_pratique`, `vrai_faux`, `question_piege`, `reformulation`, `consequence`.

Priorités de sélection (ordre décroissant) :
1. **Rotation équitable** — type le moins posé sur ce chunk
2. **Biais mastery** — types adaptés à la classe de maîtrise (`_MASTERY_BIAS`)
3. **Biais profil** — `preferred_pedagogy` de l'utilisateur comme tie-breaker

### Curriculum Engine (`engine/curriculum_engine.py`)

Arbitrage au-dessus du moteur adaptatif. Si un skill est Fragile ou si la priorité curriculum ≥ 0.80, le `question_type` curriculum override la sélection adaptative. Non-bloquant : tout échec conserve le comportement précédent.

---

## Schéma base de données — tables principales

| Table | Rôle |
|-------|------|
| `attempts` | Historique complet (score, error_type, topic, chunk_id, pedagogy_type, **retrieval_overlap_score**) |
| `chunks` | Sections de documents + embedding BLOB float32 1 536 dims |
| `documents` | Documents importés (PDF/DOCX/TXT + cleaned_text) |
| `users` | Auth (user_id UUID, password_hash bcrypt, role) |
| `user_learning_profile` | Profil adaptatif (preferred_pedagogy, scores, momentum, velocity, consistency) |
| `runtime_metrics` | Métriques LLM par appel (latence, tokens, coût estimé, fallback_used) |
| `learning_sessions` | Sessions de travail (durée, avg_score, dominant_error) |
| `skills` / `chunk_skills` / `user_skill_mastery` | Skill Graph Engine — mastery par compétence affiché dans `tab_engine` (graphe Bloom temps réel) |
| `corpus` / `corpus_documents` | Corpus personnalisés multi-documents |

**Migrations douces** via `ALTER TABLE ADD COLUMN IF NOT EXISTS` dans `init_db()`. Aucune migration destructive.

**Contrainte critique :** `chunks.id` et `attempts.chunk_id` sont des identifiants stables. DELETE+INSERT est interdit — la mémoire pédagogique et la répétition espacée en dépendent directement. Toute opération de mise à jour passe par `UPDATE` ciblé.

---

## Sécurité

| Point | Implémentation |
|-------|----------------|
| Mots de passe | bcrypt, `gensalt()` par appel — pas de sel statique |
| Comparaison mot de passe | `hmac.compare_digest` — résistant aux timing attacks |
| Requêtes SQL | 100% paramétrées — zéro f-string sur valeurs utilisateur |
| Rate limiting LLM | Sliding window par `(user_id, task_type)` — `ai_gateway/rate_limiter.py` |
| Sanitisation entrées | `sanitize_user_id()` : strip + troncature à 50 chars |
| Vérification de rôle | `promote_user()` vérifie en base, pas en `session_state` |

**Limitation connue (MVP) :** pas de protection brute-force sur le login. À ajouter avant mise en production à charge réelle.

---

## Observabilité

- **`runtime_metrics`** : chaque appel LLM enregistre latence, tokens, coût estimé, modèle, fallback_used
- **`attempts.retrieval_overlap_score`** : score 0.0–1.0 par tentative — mesure le recouvrement question/chunks depuis Phase 20
- **`chunk_quality_analyzer.py`** : heuristique TRUNC sur le corpus — sur les décrets en vigueur : 255/391 chunks tronqués identifiés (découpage à taille fixe qui coupe les articles au milieu de phrase)
- **Sentry** : intégration `LoggingIntegration`, capture des erreurs en production
- **`logs/ai_requests.jsonl`** : log local JSONL par appel LLM
- **CLI analytics** : 5 sections, verdict OK / WARNING / CRITICAL
- **Admin dashboard** : 8 KPIs + 8 charts Plotly (tendances 24h/7j), dark mode

---

## Tests et calibration

**262 vérifications au snapshot Phase 20, réparties en 4 niveaux :**

| Niveau | Outil | Couverture |
|--------|-------|------------|
| Syntaxe | `py_compile` sur 100+ fichiers | CI/CD — zéro SyntaxError en merge |
| Invariants | `test_regression.py` tripwires | Seuils moteur, REVIEW_INTERVALS — détection de drift |
| Unitaire | `test_auth_service.py` | register, verify, promote |
| Calibration | Harness Phase 18C/19 | 5 séquences, DB temporaire isolée, backdatées |

**Test de robustesse Phase 20 — 500 attempts mock (user test2, seed=99) :**

| Indicateur | Résultat |
|------------|----------|
| Attempts sauvegardés | 500/500 |
| Taux fallback pipeline | 0% |
| Score moyen (last 20) | 0.586 |
| Non-évaluable | 22 (4.4%) |
| Patterns détectés | reponse_vague, oubli_etape, hors_sujet |
| Curriculum alignment | 19% (> 16.7% aléatoire pur — confirmation non-triviale) |
| Verdict moteur | **COHERENT** |
| **Note globale** | **93/100** |

Les 7 points perdus sont structurels au mode mock (variance aléatoire, skills non activables avant 5 attempts/chunk, curriculum alignment incompressible en mode aléatoire pur) — aucun bug identifié.

**Dette test connue :** couverture unitaire faible sur `engine/` et `db/`. Les fonctions critiques sont protégées par les tripwires d'invariants, mais le coverage pytest global serait < 30%. Chantier identifié post-première collecte de sessions humaines réelles.

---

## Docker et déploiement

```yaml
# docker-compose.yml
image: python:3.11-slim
volumes:
  - ./database.db:/app/database.db
  - ./docs:/app/docs
env_file: .env
```

`docker compose up --build` → HTTP 200 OK, validé.

**Statut Railway :** déployé en production. Variables d'environnement injectées via le dashboard Railway. Volume persistant monté sur `database.db`. Déploiement déclenché au push sur `main`.

---

## Limitations techniques connues et assumées (MVP)

| Limitation | Impact | Statut |
|------------|--------|--------|
| Recherche vectorielle en RAM | Bottleneck > 50 documents | Migration pgvector prévue (Phase 13, différée jusqu'à DATABASE_URL réel) |
| SQLite mono-fichier | Concurrence limitée | Migration PostgreSQL via DATABASE_URL prévue |
| Pas de protection brute-force login | Risque sécurité | Rate limiting à étendre avant charge réelle |
| `datetime.utcnow()` deprecated | Alerte Python 3.12+ | Migrer vers `datetime.now(timezone.utc)` |
| Chunking taille fixe | 65% des chunks TRUNC sur décrets | Instrumenté (TRUNC heuristic) — chunking sémantique à implémenter |

---

## Points d'extension naturels

- **Migration PostgreSQL** : signatures `database.py` conservées, changement uniquement interne — backward compatible sans modification des appelants
- **pgvector** : `rag_service.search_similar_chunks()` isolé — remplaçable sans toucher au reste du pipeline
- **Chunking sémantique** : `document_service.py` encapsule le chunking — heuristique TRUNC déjà disponible pour guider le remplacement
- **Multi-tenant** : `user_id` présent sur toutes les tables — isolation par organisation prête à activer
- **API REST** : `ai_service.py`, `engine/`, `db/` sont découplés de Streamlit — exposables via FastAPI sans refactoring structurel

---

## Outillage projet

```
node task.mjs brief          ← briefing quotidien
node task.mjs status         ← état global du projet
node task.mjs review <id>    ← py_compile sur les fichiers core
node task.mjs prompt <id>    ← génère un prompt Claude Code pour la tâche
node task.mjs claim <id>     ← marque la tâche en cours
node task.mjs ship <id>      ← stage + commit
node task.mjs done <id>      ← marque la tâche terminée

python seed_presentation.py  ← seed démo : sessions simulées, analytics peuplées
```

`DEVLOG.md` tenu à jour après chaque phase ou tâche significative — journal chronologique des décisions, des invariants préservés et des prochaines étapes.

---

*Documentation technique — ADDISCO OPS — Phase 20 — Mai 2026*
