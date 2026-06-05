# ARCHITECTURE — ADDISCO OPS

> Dernière mise à jour : Phase 20 complète (2026-06-05)

---

## 1. Vue d'ensemble

```text
Utilisateur (navigateur)
  ↓
app.py  (Streamlit — auth, routing, sidebar)
  ↓  ↓  ↓  ↓  ↓
tabs/tab_training.py   — session d'entraînement
tabs/tab_dashboard.py  — analytics & profil
tabs/tab_documents.py  — import & gestion documents
tabs/tab_history.py    — historique des tentatives
tabs/tab_admin.py      — gestion des rôles (admin)
tabs/tab_trainer.py    — dashboard formateur (frontend/)
  ↓
ai_service.py       — RAG, embeddings, LLM (via ai_gateway)
database.py         — SQLite + shim re-exports (délègue vers db/)
adaptive_engine.py  — façade pure (délègue vers engine/)
auth_service.py     — authentification, rôles
document_service.py — ingestion, chunking, seed démo
rag_service.py      — recherche vectorielle cosinus
logger.py           — configuration logging centralisée
  ↓
ai_gateway/         — abstraction OpenAI (chat + embeddings + logs)
engine/             — moteur pédagogique pur (zéro import projet)
db/                 — couche DB segmentée (TASK-064, en cours)
```

---

## 2. Modules et responsabilités

### app.py
- Point d'entrée Streamlit
- Authentification et session state
- Routing vers les onglets
- Sidebar (navigation, info utilisateur, déconnexion)
- Nettoyage complet de session_state au logout (UX-01)

### auth_service.py
- Création / vérification de compte (hash bcrypt)
- Gestion des rôles : `apprenant`, `formateur`, `admin`
- `promote_user()` — promotion vers admin (bootstrap initial)

### ai_service.py
- Embeddings : délègue à `ai_gateway.call_embedding_api` (`text-embedding-3-small`, 1 536 dims)
- Génération de questions via RAG + LLM (`gpt-4o-mini`) — 6 types pédagogiques
- Pré-validation déterministe des réponses (`_check_answer_evaluable`)
- Correction des réponses (JSON structuré, temp=0.3)
- Fallback texte brut si RAG échoue
- `_CORRECT_FALLBACK` — retour défensif si API indisponible
- Sélection du type via `choose_adaptive_question_type()` (engine/adaptive_difficulty)
- Arbitrage curriculum via `select_next_learning_step()` (engine/curriculum_engine) — non-bloquant

### ai_gateway/
- `gateway.py` — wrapper OpenAI : `call_chat_completion`, `call_embedding_api`
  - `timeout=30`, retry sur erreur réseau, log systématique
  - `task_type` discriminant pour le logging
- `request_logger.py` — appende chaque appel API en JSONL dans `logs/ai_requests.jsonl`

### database.py
- **Shim de compatibilité** : re-exporte les symboles stables vers les anciens importeurs
- `DB_PATH`, `init_db()` — infrastructure SQLite
- Fonctions legacy encore directes : `save_attempt`, `get_attempts`, profil, analytics
- Re-exports depuis `adaptive_engine` : `_adaptive_interval`, `REVIEW_INTERVALS` (ne pas casser)
- **Délègue progressivement** vers les modules `db/` (TASK-064 en cours)

### db/ — Couche DB segmentée (TASK-064)
- `db/chunks.py` — chunks, embeddings, révision espacée, `get_revision_suggestion`
- `db/profile.py` — profil apprentissage, `get_learning_profile`, `compute_and_save_learning_profile`
- `db/skills.py` — CRUD skills, `user_skill_mastery`, `get_user_skill_mastery`
- `db/sessions.py` — sessions d'entraînement : ouverture, fermeture, analytics session
- `db/analytics.py` — analytics tentatives, évolution score, fréquence erreurs
- `db/corpus.py` — corpus multi-documents, sentinels, filtrage analytics/training/dashboard
- `db/admin.py` — gestion utilisateurs, rôles, `count_admins`, `get_all_users`
- `db/runtime_metrics.py` — métriques runtime système

### adaptive_engine.py
- **Façade pure** — zéro logique propre, délègue vers `engine/`
- Re-exporte tous les symboles publics pour compatibilité ascendante

### engine/ — Moteur pédagogique pur
Contrainte absolue : **zéro import projet** dans tous les modules `engine/`.

| Module | Rôle |
|---|---|
| `thresholds.py` | Source unique des seuils : `MASTERY_FRAGILE=0.60`, `MASTERY_MASTERED=0.80`, `MASTERY_MIN_ATTEMPTS=5`, intervalles révision |
| `spaced_rep.py` | `classify_mastery()` (chunk-level), `_adaptive_interval()` — répétition espacée |
| `question_type.py` | `QUESTION_TYPES`, `_MASTERY_BIAS`, `_choose_question_type()`, `explain_type_choice()` |
| `adaptive_difficulty.py` | `choose_adaptive_question_type()` V2 — 5 priorités : erreur dominante → difficulté → rotation → filtre → profil |
| `session_plan.py` | `build_session_plan()` — plan ordonné par priorité, objectifs pédagogiques |
| `retention.py` | `compute_retention_metrics()` — fenêtres J+1/J+7/J+30 |
| `profile_metrics.py` | `compute_momentum()`, `compute_learning_velocity()`, `compute_consistency_score()` |
| `skill_engine.py` | `classify_skill_mastery()` (skill-level), `compute_skill_mastery()` |
| `skill_graph.py` | Graphe Bloom 5 niveaux — `SKILL_GRAPH`, `is_ready()`, `get_blocking()`, `get_session_order()` |
| `skill_mapper.py` | Mapping tentatives → skills détectés |
| `skill_keywords.py` | Dictionnaire mots-clés → skill slug |
| `skill_analytics.py` | Analytics agrégées par skill |
| `skill_debug.py` | Utilitaire debug skill graph |
| `error_pattern_memory.py` | `detect_persistent_error_patterns()` — mémoire erreurs persistantes cross-sessions |
| `curriculum_engine.py` | `build_learning_queue()`, `select_next_learning_step()` — curriculum V1 (observation + arbitrage) |
| `user_profile_insights.py` | Insights profil utilisateur enrichis |

### document_service.py
- Import PDF / texte brut
- Chunking intelligent (section_title, char_count, ~500 chars)
- Seed démo (`seed_demo_documents`)

### rag_service.py
- Recherche vectorielle cosinus (numpy, SQLite BLOB)
- `search_similar_chunks(query_vector, document_id, top_k)`
- `search_similar_chunks_multi(query_vector, document_ids, top_k)` — multi-documents

### logger.py
- Configuration logging centralisée
- Importé via `logging.getLogger(__name__)` dans tous les modules

### tabs/
- `tab_training.py` — génération question, soumission réponse, feedback, RAG display
- `tab_dashboard.py` — graphes, profil pédagogique, métriques adaptatives, dark theme
- `tab_documents.py` — upload, liste, stats embeddings, corpus multi-documents
- `tab_history.py` — historique paginé des tentatives
- `tab_admin.py` — liste utilisateurs, promotion/rétrogradation de rôles
- `tab_trainer.py` — dashboard formateur (délègue vers `frontend/dashboard/`)

### frontend/dashboard/
- `trainer_dashboard.py` — dashboard formateur Streamlit
- `components/` — stat_card, learner_card, adaptive_profile, alerts_panel, progress_chart, recommendation_panel
- `mock_data/` — données démo formateur

### tools/
- `tools/qa/` — tests robustesse, screenshots, simulation 100 questions
- `tools/testing/` — simulation sessions, tests curriculum, error pattern
- `tools/observability/` — audit skills, skill graph observer, correction map, error pattern observer
- `tools/admin/` — create_admin, reset_password
- `tools/roadmap/` — update_progress, close_task
- `tools/guardrails/` — règles d'architecture, guardrails automatisés

---

## 3. Pipeline RAG

```text
Document importé
  ↓ document_service.py
Extraction texte + nettoyage
  ↓
Chunking (section_title, ~500 chars)
  ↓ ai_service.generate_embedding() → ai_gateway.call_embedding_api()
Embedding float32 BLOB (1 536 dims) → chunks.embedding
  ↓
Requête utilisateur
  ↓ ai_gateway.call_embedding_api()
Vecteur requête
  ↓ rag_service.search_similar_chunks_multi()
Top-3 chunks (cosinus, multi-documents)
  ↓ ai_service.generate_question()
Prompt LLM → Question typée
```

---

## 4. Moteur adaptatif — pipeline complet

```text
attempts (score, pedagogy_type, error_type, topic, chunk_id, created_at)
  ↓
┌──────────────────────── Niveau chunk ────────────────────────┐
│ classify_mastery()  [engine/spaced_rep.py]                    │
│ Fragile (<0.60) | En consolidation | Maîtrisé (≥0.80, n≥5)  │
│ trend : Amélioration / Stable / Dégradation / N/A            │
└──────────────────────────────────────────────────────────────┘
  ↓
┌──────────────────────── Niveau skill ────────────────────────┐
│ skill_mapper.py → skills détectés par tentative              │
│ classify_skill_mastery() [engine/skill_engine.py]            │
│ Fragile | En cours | Acquis (≥0.80, n≥5)                    │
│ skill_graph.py → prérequis, niveau Bloom (0-4)               │
└──────────────────────────────────────────────────────────────┘
  ↓
┌──────────────── Sélection type de question ──────────────────┐
│ choose_adaptive_question_type() [engine/adaptive_difficulty]  │
│ 1. Erreur dominante persistante (error_pattern_memory)        │
│ 2. Cible difficulté (easy/medium/hard)                        │
│ 3. Rotation équitable (moins utilisé sur ce chunk)            │
│ 4. Filtre difficulté (bucket matching)                        │
│ 5. Tie-breaker profil (preferred_pedagogy)                    │
│                                                               │
│ Arbitrage curriculum (curriculum_engine) — non-bloquant      │
│ Override si skill Fragile ou priority ≥ 0.80                 │
└──────────────────────────────────────────────────────────────┘
  ↓ generate_question() — LLM gpt-4o-mini (temp=0.7, max=200)
Question typée
  ↓ _check_answer_evaluable() — pré-validation déterministe
  ↓ correct_answer() — LLM gpt-4o-mini (temp=0.3, JSON forcé)
Score [0.0-1.0] + error_type + topic + correction
  ↓
compute_and_save_learning_profile()
preferred_pedagogy, fragile_topics, momentum, velocity, consistency
```

---

## 5. Schéma base de données

### Table `attempts`
| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| user_id | TEXT | défaut `'default'` |
| document_id | INTEGER | FK → documents.id |
| chunk_id | INTEGER | FK → chunks.id — répétition espacée |
| question | TEXT | |
| user_answer | TEXT | |
| expected_answer | TEXT | |
| correction | TEXT | |
| score | REAL | 0.0–1.0 |
| error_type | TEXT | oubli_etape / confusion_notion / reponse_vague / erreur_ordre / hors_sujet |
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
| id | INTEGER PK | |
| document_id | INTEGER | FK → documents.id |
| chunk_index | INTEGER | |
| section_title | TEXT | |
| chunk_text | TEXT | |
| char_count | INTEGER | |
| embedding_id | TEXT | |
| embedding | BLOB | float32 LE, 1 536 dims |
| created_at | TIMESTAMP | |

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

### Table `skills` (Phase 17+)
| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| slug | TEXT UNIQUE | immuable après déploiement |
| label_fr | TEXT | |
| description | TEXT | |
| is_active | INTEGER | 0/1 |

### Table `user_skill_mastery` (Phase 17+)
| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| user_id | TEXT | FK → users.user_id |
| skill_id | INTEGER | FK → skills.id |
| mastery_score | REAL | moyenne des scores sur ce skill |
| attempts_count | INTEGER | nombre de tentatives |
| last_reviewed_at | TIMESTAMP | |

### Table `user_sessions` (Phase 18+)
| Colonne | Type | Note |
|---|---|---|
| id | INTEGER PK | |
| user_id | TEXT | |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | nullable — null si session ouverte |
| avg_score | REAL | calculé à la fermeture |
| duration_seconds | INTEGER | |

---

## 6. Seuils centralisés — engine/thresholds.py

Source unique de vérité pour tous les paramètres adaptatifs.
Toute modification se propage automatiquement à l'ensemble du moteur.

| Constante | Valeur | Usage |
|---|---|---|
| `MASTERY_FRAGILE` | 0.60 | avg_score < seuil → Fragile (chunk et skill) |
| `MASTERY_MASTERED` | 0.80 | avg_score ≥ seuil → Maîtrisé/Acquis |
| `MASTERY_MIN_ATTEMPTS` | 5 | nombre minimum de tentatives pour valider la maîtrise |
| `ADAPTIVE_FORCE_EASY` | 0.40 | avg récent < seuil → forcer easy |
| `ADAPTIVE_ALLOW_HARD` | 0.65 | avg récent ≥ seuil → autoriser hard |
| `REVIEW_INTERVALS` | Fragile:1j, Consolidation:3j, Maîtrisé:7j | intervalles répétition espacée |

---

## 7. Contraintes architecturales critiques

1. **`engine/` = modules purs** — aucun import projet dans aucun fichier `engine/`, jamais.
2. **`adaptive_engine.py` = façade uniquement** — aucune logique directe, que des re-exports.
3. **Stabilité des IDs** — `attempts.chunk_id`, `chunks.id`, `skills.slug` ne doivent jamais être recréés (DELETE+INSERT interdit).
4. **Guard `if df.empty: return df`** dans `classify_mastery()` — ne pas retirer.
5. **`pd.isna()` obligatoire** pour tester les valeurs nulles datetime (pandas 2.x, `pd.NaT is None == False`).
6. **`Optional[str]`** (from typing) — jamais `str | None` (incompatible Streamlit 1.x + Python 3.9).
7. **Re-exports `database.py`** — `_adaptive_interval` et `REVIEW_INTERVALS` sont importables via `database` — ne pas casser sans migration de tous les importeurs.
8. **UX-01** — tout nouveau state pédagogique doit être ajouté à la liste de nettoyage logout dans `app.py`.
9. **Fallback texte brut** — si RAG ou embeddings échouent, `generate_question()` utilise `source_text` direct.
10. **curriculum_engine = non-bloquant** — tout appel à `select_next_learning_step()` dans `ai_service.py` est enveloppé dans `try/except` ; un échec ne doit jamais couper la génération de question.

---

## 8. Deux systèmes de maîtrise parallèles

Le moteur distingue deux granularités — intentionnellement différentes :

| Niveau | Module | Etats | Seuil MIN_ATTEMPTS |
|---|---|---|---|
| **Chunk** | `engine/spaced_rep.py` | Fragile / En consolidation / Maîtrisé | 5 |
| **Skill** | `engine/skill_engine.py` | Fragile / En cours / Acquis | 5 |

Les labels sont volontairement différents pour éviter la confusion. Toujours vérifier quel niveau est utilisé dans un contexte donné.

---

## 9. Évolution prévue

### TASK-064 — Finalisation segmentation database.py
La segmentation `db/` est en cours. `database.py` reste un shim stable.
Après complétion, `database.py` ne contiendra plus que `DB_PATH`, `init_db()`, et les re-exports.

**Vérification post-migration** : `python -c "from database import _adaptive_interval, REVIEW_INTERVALS"`

### Phase V4 (branche ai-v4)
Fork de Phase 20, ROADMAP-V4 en 8 phases — voir `ROADMAP-V4.md`.

---

*ADDISCO OPS — Architecture vivante — ne pas modifier manuellement sans mise à jour simultanée de DEVLOG.md*
