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

STATUS : TODO

---

# Phase 17 — Production Readiness

Note : Phase 17 commence à TASK-064 pour éviter toute collision avec Phase 16 (TASK-060 à TASK-063).

## TASK-064 — Tests d'intégration complets

STATUS : TODO

---

## TASK-065 — Rate limiting LLM

STATUS : TODO

---

## TASK-066 — Monitoring applicatif (Sentry)

STATUS : TODO

---

## TASK-067 — CI/CD complet

STATUS : TODO

