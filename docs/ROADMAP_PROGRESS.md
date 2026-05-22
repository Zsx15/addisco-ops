# ROADMAP PROGRESS — ADDISCO OPS PHASE 2

Suivi automatique des tasks de la phase 2.
Mis à jour via `python tools/roadmap/update_progress.py` ou `close_task.py`.

Ordre stratégique : moteur → calibration → maintenance → admin → UX.
Règle : aucune tâche ne démarre sans validation explicite de la précédente.

---

## TASK-051 — Sources visibles / contexte pédagogique

STATUS   : DONE
DATE     : 2026-05-21
COMMIT   : 8aebae7
SNAPSHOT : snapshot_task051_ok

Livré :
- expander "Contexte RAG utilisé" avec top-k chunks
- rang (Source principale / Source 2 / Source 3)
- document source + score RAG (%)
- section + extrait 200 chars
- fallback texte brut : expander masqué

Observations :
- retrieval parfois bruité (chunks tabulaires, listes de noms) — prévu TASK-054

Prochaine : TASK-051B

---

## TASK-051B — Consolidation UX profil pédagogique

STATUS   : DONE
DATE     : 2026-05-21
COMMIT   : f31f117
SNAPSHOT : snapshot_task051b_ok

Livré :
- séparation confiance statistique (volume de données) et signal pédagogique (écart entre modes)
- affichage côte à côte dans le profil enrichi
- nettoyage dominant_style_label (plus de "signal faible" dans le texte de style)
- smoke test mis à jour (required_keys + affichage)

Observations :
- observation chunks bruités enregistrée dans DEVLOG — à traiter dans TASK-054

Prochaine : TASK-052

---

## TASK-052 — Score de confiance correction V1

STATUS   : DONE
DATE     : 2026-05-21
COMMIT   : d56a087
SNAPSHOT : snapshot_task052_ok

---

## TASK-053 — Rejet hors sujet / non évaluable

STATUS   : DONE
DATE     : 2026-05-21
COMMIT   : 9f98dbb
SNAPSHOT : snapshot_task053_rerun_fix

---

## TASK-054 — Chunk Quality Analyzer V1

DATE     : 2026-05-21
COMMIT   : b39bc6e
SNAPSHOT : snapshot_task054_ok
STATUS   : DONE

---

## TASK-055 — Skill Graph Engine V1

DATE     : 2026-05-21
COMMIT   : 3eaf9b4
SNAPSHOT : snapshot_task055_ok
STATUS   : DONE

---

## TASK-056A — Simulateur session pédagogique réelle

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 2909343

---

## TASK-056 — Adaptive Difficulty Engine V2

DATE     : 2026-05-22
COMMIT   : 412101e
SNAPSHOT : snapshot_task056_ok
STATUS   : DONE

---

## TASK-056B — Centralisation seuils mastery + filtre non_evaluable

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : f556673

---

## TASK-057A — Correction Map observabilité

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : bd2d044
SNAPSHOT : snapshot_task057a_ok

---

## TASK-057 — Error Pattern Memory

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 4a6c69c

Mémoire persistante d'erreurs pédagogiques. 5 tendances (critique/chronique/récent/en_amelioration/stabilisé). Injection non-bloquante dans generate_question(). 10/10 tests simulation, 239→246 tests régression.

---

## TASK-057B — Script vérification session 30Q Error Pattern Memory

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 7413854

---

## TASK-058 — Curriculum Engine V1

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 0c750cc

Moteur curriculum déterministe (Phase 1 observation). build_learning_queue() : 3 sources (error_pattern/skill_mastery/revision), rotation anti-saturation, déduplication. Observer CLI. 14/14 tests simulation, 246/246 régression. generate_question() non modifié en Phase 1.

---

## TASK-058B — Script vérification alignement Curriculum Engine

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 8f7b5e3

---

## TASK-059 — Runtime Curriculum Arbitration

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : ce5e88b

Intégration curriculum dans generate_question() comme arbitre prioritaire. Override question_type si skill Fragile ou priorité >= 0.80. Fallback garanti. Validation 20Q : 5% → 70% alignement curriculum. 246/246 tests.

---

## TASK-060 — Maintenance Assistée V1

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 690fa07

Livré :
- `tools/maintenance/maintenance_report.py` — script standalone read-only
- 6 sections : chunks (WEAK/ORPHAN/NOISY), skills (morts/surchargés), documents
  problématiques, dérive de scores (7j vs global), anomalies attempts (non-évaluable
  / réponses rapides / streaks score=0), guardrails architecture
- verdict GO SAFE / WARNING / FAILED
- import direct de chunk_quality_analyzer et architecture_guardrails (sans duplication)
- 254/254 tests régression OK

Prochaine : TASK-061 — Vue admin

---

## TASK-061 — Vue admin

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : bc8f50f

Livré :
- migration douce `users.is_active INTEGER DEFAULT 1` dans `init_db()`
- `db/admin.py` : `set_user_active()`, `get_platform_stats()`, `get_document_admin_stats()`,
  `get_system_alerts()` (read-only, aucun appel API)
- `get_all_users()` enrichi : `is_active`, `n_attempts`, `last_attempt`
- `tabs/tab_admin.py` : 4 zones (KPIs globaux, alertes système, gestion utilisateurs
  activation/désactivation + promotion rôle, documents avec stats)
- `app.py` : tab "Admin" visible uniquement `role == "admin"`
- py_compile 4/4 OK · 254/254 tests régression OK

Prochaine : TASK-062 — Rapports HTML/PDF

---

## TASK-062 — Rapports HTML/PDF

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 56f3981

Livré :
- `tools/reports/generate_learning_report.py` — standalone, read-only, aucun appel API
- 7 sections HTML : résumé exécutif, KPIs, maîtrise par section, profil d'apprentissage,
  patterns d'erreurs, plan de session, sections à réviser
- CSS inline · compatible impression → PDF (Ctrl+P)
- sortie : `reports/rapport_<user_id>_<YYYYMMDD>.html`
- rapports exclus du git via .gitignore
- py_compile OK · 254/254 tests régression OK

Prochaine : TASK-063 — UX responsive tablette

---

## TASK-063 — UX responsive tablette

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : 079298a

Livré :
- `tabs/styles.py` : `RESPONSIVE_CSS` (media 900px/600px), `PRESENTATION_CSS`,
  `PRESENTATION_BANNER`, classe `pipeline-pills-row` sur header pills
- `app.py` : toggle sidebar "Mode présentation", injection CSS conditionnelle,
  navigation réduite à 3 tabs essentiels en mode présentation
- py_compile 2/2 OK · 254/254 tests régression OK

---

# Phase 17 — Production Readiness

Note : Phase 17 commence à TASK-064 pour éviter toute collision avec Phase 16 (TASK-060 à TASK-063).

## TASK-064 — Tests d'intégration complets

STATUS   : DONE
DATE     : 2026-05-22

Livré :
- `test_integration.py` — 24 tests, pipeline complet sans appel API réel
- 4 classes : TestIngestionPipeline, TestQuestionGenerationPipeline,
  TestCorrectionPipeline, TestAnalyticsPipeline, TestFullSessionPipeline
- Mocks : `ai_service.call_embedding_api` + `ai_service.call_chat_completion`
- Cas couverts : ingest (doc/chunks/embeddings, vide, trop large), génération
  (avec/sans document_id, fallback, panne LLM), correction (JSON valide/invalide,
  réponse vide/courte, panne LLM), analytics (save/retrieve, compteur, évolution),
  session bout-en-bout (ingest→generate→correct→save→analytics)
- `.github/workflows/ci.yml` : step `Run integration tests` ajouté
- 254/254 régression + 24/24 intégration OK

Prochaine : TASK-065 — Rate limiting LLM

---

## TASK-064B — Fix ResourceWarning SQLite

STATUS   : DONE
DATE     : 2026-05-22

Livré :
- Ajout de `conn.close()` explicite après chaque bloc `with sqlite3.connect()` dans tous les modules
- Fichiers corrigés : `database.py`, `db/analytics.py`, `db/chunks.py`, `db/profile.py`,
  `db/skills.py`, `engine/curriculum_engine.py`, `engine/error_pattern_memory.py`,
  `rag_service.py`, `test_integration.py`, `test_regression.py`
- Résultat : 0 ResourceWarning depuis notre code (warnings résiduels = `python-docx` tiers, hors périmètre)
- 254/254 régression + 24/24 intégration OK, 0 régression

Observations :
- Python 3.14 : `with sqlite3.connect() as conn:` gère la transaction uniquement,
  pas la fermeture — `conn.close()` obligatoire.
- Warnings `docx/shared.py` non corrigibles sans patcher la lib tierce.

Prochaine : TASK-065 — Rate limiting LLM

---

## TASK-064C — SQLite Connection Audit

STATUS   : DONE
DATE     : 2026-05-22

Livré :
- `tools/qa/audit_sqlite_connections.py` — script read-only, scan AST complet
- 99 fichiers .py scannés (hors .venv, backups, __pycache__, .git)
- Détecte : with sqlite3.connect() as conn + conn = sqlite3.connect()
- Vérifie : conn.close() présent après la fin du bloc dans le même scope
- Sortie   : OK / WARNING / UNKNOWN + verdict GO SAFE / [!!] WARNING
- Exit code 0 (GO SAFE) ou 1 (WARNING) — intégrable CI

Résultat de l'audit :
  Total sqlite3.connect : 101
  OK                    : 56   (pipeline core + tests unitaires)
  WARNING               : 45   (hors scope TASK-064B — voir ci-dessous)
  UNKNOWN               : 0

Fichiers avec WARNING (non corrigés — rapport seul, selon spec) :
  - app.py (1) — _count_users
  - auth_service.py (2) — register_user, get_user_by_username
  - db/admin.py (6) — count_admins, get_all_users, set_user_role, set_user_active,
                       get_platform_stats, get_document_admin_stats, get_system_alerts
  - engine/skill_analytics.py (6) — get_skill_frequency, get_skill_collisions, ...
  - engine/skill_debug.py (1) — explain_chunk_skills
  - seed_demo_attempts.py (1) — seed
  - test_auth_service.py (1) — test_verify_null_hash_returns_none
  - tools/* (28) — scripts utilitaires, scripts de vérification, tools/qa/*.py

Prochaine : TASK-064D (optionnel — fermer les connexions restantes)
         ou TASK-065 — Rate limiting LLM (si TASK-064C validé)

---

## TASK-065 — Rate limiting LLM

STATUS   : DONE
DATE     : 2026-05-22
SNAPSHOT : snapshot_task65_ok

Livré :
- `ai_gateway/rate_limiter.py` — sliding window in-memory, par utilisateur + call_type
  - Thread-safe (threading.Lock), stdlib pur (threading, time, collections.deque)
  - Deux fenêtres : par minute + par heure
  - API : check_rate_limit(user_id, call_type) → (bool, reason_str)
  - reset_rate_limiter() pour tests/admin
  - Configurable : RATE_CHAT_PER_MINUTE, RATE_CHAT_PER_HOUR,
                   RATE_EMBED_PER_MINUTE, RATE_EMBED_PER_HOUR
- `ai_gateway/gateway.py` — user_id: str = "default" sur les 2 fonctions publiques
  - Gate avant chaque appel API : if not allowed → log WARNING + return None
  - Backward-compatible (paramètre optionnel, callers existants non modifiés)
- `.env.example` — 4 nouvelles vars documentées avec valeurs par défaut
- `test_regression.py` — 8 nouveaux tests (TestRateLimiter)
  : first_call_allowed, minute_limit_blocks, reset_clears_counter,
    users_tracked_independently, call_types_tracked_independently,
    window_count_after_calls, unknown_call_type_uses_chat_limits

Résultats :
  - 262/262 régression OK (254 + 8 nouveaux)
  - 24/24 intégration OK
  - Limites par défaut : chat 20/min 200/h — embed 30/min 500/h

Observations :
  - Tests existants mockent call_chat_completion → rate limiter bypassé → aucun impact
  - En production : Streamlit passe user_id via session_state pour limiter par utilisateur réel
  - Redémarrage app = reset des compteurs (acceptable MVP)

Prochaine : TASK-066 — Monitoring applicatif (Sentry)

---

## TASK-067 — CI/CD complet

STATUS   : DONE
DATE     : 2026-05-22
SNAPSHOT : snapshot_task67_ok

Livré :
- `requirements.txt` : ajout de `numpy>=1.26.0` (dépendance directe de rag_service.py,
  absente jusqu'ici — installée implicitement via pandas, risque si pandas change ses deps)
- `.github/workflows/ci.yml` : refonte du pipeline
  - Bloc `env` global : PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED, OPENAI_API_KEY fictive
  - `Compile all Python files` : find . -name "*.py" | xargs -0 python -m py_compile
    → couvre 100 fichiers au lieu des 5 hardcodés précédemment (auto-maintenu)
  - Tests inchangés : test_regression.py + test_integration.py
- Validation locale : 100 fichiers py_compile OK + 286/286 tests OK

Résultats :
  - py_compile : 100 fichiers (était 5)
  - Régression : 262/262
  - Intégration : 24/24
  - Total : 286 tests

Critère de sortie Phase 17 atteint : CI green à chaque commit.

Prochaine : TASK-066 — Monitoring applicatif (Sentry)

---

## TASK-066 — Monitoring applicatif (Sentry)

STATUS : TODO

---

## TASK-067 — CI/CD complet

STATUS : TODO

