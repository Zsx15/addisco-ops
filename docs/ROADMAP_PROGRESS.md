# ROADMAP PROGRESS — ADDISCO OPS PHASE 2

Suivi automatique des tasks de la phase 2.
Mis à jour via `python tools/roadmap/update_progress.py` ou `close_task.py`.

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

STATUS : TODO

---

## TASK-053 — Rejet hors sujet / non évaluable

STATUS : TODO

---

## TASK-054 — Chunk Quality Analyzer V1

STATUS : TODO

---

## TASK-055 — Adaptive Next Question V1

STATUS : TODO

---

## TASK-056 — Calibration Engine V1

STATUS : TODO

---

## TASK-057 — Maintenance Assistée V1

STATUS : TODO

---

## TASK-058 — Health Score Projet

STATUS : TODO


