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

STATUS : TODO

---

## TASK-057 — Error Pattern Memory

STATUS : TODO

---

## TASK-058 — Curriculum Engine V1

STATUS : TODO

---

## TASK-059 — Calibration Engine V1

STATUS : TODO

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
