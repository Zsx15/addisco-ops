# ARCHITECTURE — ADDISCO OPS

> Dernière mise à jour : Phase 15B complète (2026-05-17)

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
  ↓
ai_service.py     — RAG, embeddings, LLM (OpenAI)
database.py       — SQLite, analytics, répétition espacée
adaptive_engine.py — moteur pur (zéro import projet)
auth_service.py   — authentification, rôles
document_service.py — ingestion, chunking, seed démo
rag_service.py    — recherche vectorielle cosinus
logger.py         — configuration logging centralisée
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
- Embeddings OpenAI (`text-embedding-3-small`, 1 536 dims, BLOB float32)
- Génération de questions via RAG + LLM (`gpt-4o-mini`)
- Correction des réponses (JSON structuré)
- Fallback texte brut si RAG échoue
- `timeout=30` sur tous les appels LLM
- `_CORRECT_FALLBACK` — retour défensif si API indisponible

### database.py
- Couche SQLite (via `sqlite3` stdlib)
- Cinq groupes fonctionnels (marqueurs `# ──` dans le fichier) :
  1. **Infrastructure** — `DB_PATH`, `init_db()`, migrations douces
  2. **Tentatives & Analytics** — `save_attempt`, `get_attempts`, `get_score_evolution`, `get_error_frequency`, `get_topic_stats`
  3. **Documents & Chunks** — `save_document`, `save_chunks`, `update_chunk_embedding`, `get_chunks_for_reindex`, `has_documents`, `get_documents`, `get_document_by_id`, `get_chunk_stats`, `get_chunk_question_history`, `get_chunk_mastery`, `get_revision_suggestion`
  4. **Profil d'apprentissage** — `get_learning_profile`, `compute_and_save_learning_profile`, `get_next_session_plan`, `get_retention_metrics`
  5. **Gestion admin** — `count_admins`, `get_all_users`, `set_user_role`
- Re-exports transparents depuis `adaptive_engine` : `_adaptive_interval`, `REVIEW_INTERVALS` (ne pas casser)
- Segmentation en `db_*.py` prévue post-Phase 15 (voir TASK-064)

### adaptive_engine.py
- **Module pur — zéro import projet** (contrainte architecturale critique)
- `classify_mastery`, `_adaptive_interval` — répétition espacée
- `_choose_question_type`, `explain_type_choice` — sélection pédagogique
- `compute_momentum`, `compute_learning_velocity`, `compute_consistency_score`
- `build_session_plan` — plan adaptatif ordonné par priorité
- `compute_retention_metrics` — métriques J+1/J+7/J+30

### document_service.py
- Import PDF / texte brut
- Chunking intelligent (section_title, char_count)
- Seed démo (`seed_demo_documents`)

### rag_service.py
- Découpage en chunks
- Recherche vectorielle cosinus (numpy, SQLite BLOB)
- `search_similar_chunks(query_vector, document_id, top_k)`

### logger.py
- Configuration logging centralisée (niveau, format, handlers)
- Importé par tous les modules via `logging.getLogger(__name__)`

### tabs/
- `tab_training.py` — génération question, soumission réponse, feedback
- `tab_dashboard.py` — graphes, profil pédagogique, métriques adaptatives
- `tab_documents.py` — upload, liste, stats embeddings
- `tab_history.py` — historique paginé des tentatives
- `tab_admin.py` — liste utilisateurs, promotion/rétrogradation de rôles

---

## 3. Pipeline RAG

```text
Document importé
  ↓ document_service.py
Extraction texte + nettoyage
  ↓
Chunking (section_title, ~500 chars)
  ↓ ai_service.generate_embedding()
Embedding float32 BLOB → chunks.embedding
  ↓
Requête utilisateur
  ↓ ai_service._call_embedding_api()
Vecteur requête
  ↓ rag_service.search_similar_chunks()
Top-K chunks (cosinus)
  ↓ ai_service.generate_question()
Prompt LLM → Question
```

---

## 4. Moteur adaptatif

```text
attempts (score, pedagogy_type, topic, chunk_id, created_at)
  ↓ classify_mastery()
Niveau par chunk : débutant / intermédiaire / maîtrisé / fragile
  ↓ _choose_question_type()
Type pédagogique : rotation + biais mastery + profil utilisateur
  ↓ generate_question()
Question typée (6 types disponibles)
  ↓ correct_answer()
Score + error_type + topic
  ↓ compute_and_save_learning_profile()
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
| error_type | TEXT | oubli_etape / confusion_notion / … |
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
| momentum | REAL | TASK-049 — delta score 7j |
| learning_velocity | REAL | TASK-049 — delta inter-sessions |
| consistency_score | REAL | TASK-049 — jours actifs / 30 |
| updated_at | TIMESTAMP | |

### Table `users`
| Colonne | Type | Note |
|---|---|---|
| user_id | TEXT PK | |
| username | TEXT UNIQUE | |
| password_hash | TEXT | bcrypt |
| role | TEXT | apprenant / formateur / admin |
| created_at | TIMESTAMP | |

---

## 6. Contraintes architecturales critiques

1. **`adaptive_engine.py` = module pur** — aucun import projet, jamais.
2. **Stabilité des IDs** — `attempts.chunk_id` et `chunks.id` ne doivent jamais être recréés (DELETE+INSERT interdit).
3. **Guard `if df.empty: return df`** dans `classify_mastery()` — ne pas retirer.
4. **`pd.isna()` obligatoire** pour tester les valeurs nulles datetime (pandas 2.x, `pd.NaT is None == False`).
5. **`Optional[str]`** (from typing) — jamais `str | None` (incompatible Streamlit 1.x + Python 3.9).
6. **Re-exports `database.py`** — `_adaptive_interval` et `REVIEW_INTERVALS` sont importables via `database` — ne pas casser sans migration de tous les importeurs.
7. **UX-01** — tout nouveau state pédagogique doit être ajouté à la liste de nettoyage logout dans `app.py`.
8. **Fallback texte brut** — si RAG ou embeddings échouent, `generate_question()` utilise `source_text` direct.

---

## 7. Évolution prévue

### Post-Phase 15 — TASK-064 : Segmentation database.py
Découper en modules ciblés après stabilisation Phase 15 multi-documents :
- `db_core.py` — DB_PATH, init_db
- `db_attempts.py` — save/get attempts, analytics
- `db_documents.py` — documents, chunks, embeddings, RAG helpers
- `db_profile.py` — profil, plan, rétention
- `db_admin.py` — users, rôles
- `database.py` (shim) — re-exports pour compatibilité ascendante

**Risque principal** : imports silencieux via re-exports — tester avec `python -c "from database import _adaptive_interval"` après migration.

---

*ADDISCO OPS — Architecture vivante — ne pas modifier manuellement sans mise à jour simultanée de DEVLOG.md*
