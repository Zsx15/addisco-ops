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

## TASK-056 — Adaptive Difficulty Engine V2

DATE     : 2026-05-22
COMMIT   : 412101e
SNAPSHOT : snapshot_task056_ok
STATUS   : DONE

---

## TASK-057 — Error Pattern Memory

STATUS : DONE — 2026-05-22
Mémoire persistante d'erreurs pédagogiques. 5 tendances (critique/chronique/récent/en_amelioration/stabilisé). Injection non-bloquante dans generate_question(). 10/10 tests simulation, 239→246 tests regression.

---

## TASK-058 — Curriculum Engine V1

STATUS : DONE — 2026-05-22
Moteur curriculum déterministe (Phase 1 observation). build_learning_queue() : 3 sources (error_pattern/skill_mastery/revision), rotation anti-saturation, déduplication. Observer CLI. 14/14 tests simulation, 246/246 regression. generate_question() non modifié en Phase 1.

---

## TASK-059 — Runtime Curriculum Arbitration

STATUS : DONE — 2026-05-22
Intégration curriculum dans generate_question() comme arbitre prioritaire. Override question_type si skill Fragile ou priorité >= 0.80. Fallback garanti. Validation 20Q : 5% → 70% alignement curriculum. 246/246 tests.

---

## TASK-060 — Maintenance Assistée V1

STATUS : TODO

---

## TASK-061 — Vue admin

STATUS : TODO

---

## TASK-062 — Rapports HTML/PDF

STATUS : TODO

---

## TASK-063 — UX responsive tablette

STATUS : TODO

---

## TASK-057A

STATUS   : DONE
DATE     : 2026-05-22
COMMIT   : bd2d044
SNAPSHOT : snapshot_task057a_ok

