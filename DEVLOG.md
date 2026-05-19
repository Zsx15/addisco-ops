# DEVLOG — AI Révision Métier

Journal de développement chronologique du projet.

---

## 2026-05-19 — Test corpus paramétrable (`--n`) — stress-test 300 cycles

**Objectif :** rendre le nombre de cycles configurable pour permettre une couverture totale du corpus et des stress-tests à grande échelle.

### Modifications apportées à `test_robustesse_100q.py`

11 changements ciblés, 0 refactor, comportement identique sans `--n` :

- `run_test(... n_questions: int = N_QUESTIONS)` — paramètre runtime
- `_n = n_questions` en tête de fonction ; tous les `N_QUESTIONS` internes remplacés par `_n`
- `--n` (argparse, défaut : 100) — transmis à `run_test(n_questions=args.n)`
- Rapport étendu : `N demande`, `attempts/s`, couverture `%` chunks + docs, chunks non sollicités avec liste d'exemples

### Commande lancée

```
python test_robustesse_100q.py --mock --profile mixed --username test --scope corpus --n 300 --no-confirm
```

### Résultats

| Métrique | Valeur |
|---|---|
| N demandé | 300 |
| Attempts sauvegardées | 300 / 300 |
| Score moyen | 70 % (0.697) |
| Temps total | 1 s |
| Débit | 368 attempts/s |
| Documents sollicités | 4 / 4 (100 %) |
| Chunks sollicités | 295 / 295 (100 %) |
| Chunks non sollicités | 0 (couverture totale) |

Répartition attempts par document :

| doc | titre | attempts | % |
|---|---|---|---|
| 1 | Procédure d'accueil voyageur | x10 | 3 % |
| 2 | Addisco Ops | x6 | 2 % |
| 3 | Police | x8 | 3 % |
| 4 | Decrets | x276 | 92 % |

### Diagnostic structurel

- Moteur stable sur 300 cycles, 0 erreur, profil recalculé 30 fois
- `user_skill_mastery` cohérente : `conformite_reglementaire` à 425 tentatives cumulées, pas de saturation
- 368 attempts/s — coût SQL marginal sur SQLite
- Couverture totale (100 %) atteinte à N >= 295 (= nombre de chunks)

### Limites observées

- Déséquilibre attendu : doc 4 (`Decrets`, 275 chunks) capte 92 % des attempts par effet modulo
- 64 / 295 chunks sans skills (22 %) — structurel, non bloquant
- `synthese_reformulation` : 11 tentatives seulement (peu de chunks mappés)

### Invariants respectés

- 0 appel API, données `test` préservées, `chunks.id` intacts, 227/227 tests

**Commit :** `33acba3`

**Prochaine étape suggérée :** vue admin (gestion utilisateurs) ou augmenter N pour stress-test > 1000 cycles.

---

## 2026-05-19 — Snapshot `snapshot_test_robustesse_corpus_v1`

Backup stable après validation du mode `--scope corpus` et des 3 profils mock sur utilisateur cible `test`.

**Fichier :** `backups/snapshot_test_robustesse_corpus_v1_20260519_1714.zip`  (36 fichiers, 122 Ko)

**Contenu :** `test_robustesse_100q.py` (version complète avec `--username`, `--scope`), `database.py`, `db/`, `engine/`, `tabs/`, `app.py`, `ai_service.py`, `rag_service.py`, `adaptive_engine.py`, `auth_service.py`, `document_service.py`, `ui_helpers.py`, `DEVLOG.md`, `ROADMAP.md`.

**État au snapshot :**
- 400 attempts sur utilisateur `test` (300 profils + 100 corpus)
- 10 skills actifs dans `user_skill_mastery`
- 295 chunks disponibles sur 4 documents
- 227/227 tests
- Dernier commit : `02e9b2f`

---

## 2026-05-19 — Test robustesse corpus complet (`--scope corpus`)

**Objectif :** vérifier la solidité du moteur sur l'ensemble du corpus (tous documents, tous chunks) via une couverture maximale en mode mock.

### Modification apportée à `test_robustesse_100q.py`

Ajout de `--scope {default,corpus}` — 9 changements ciblés, 0 refactor :

- `run_test(scope="default")` — nouveau paramètre
- `corpus_schedule` construit si `scope=="corpus"` : liste de `{chunk_id, doc_id}` couvrant l'ensemble des chunks liés à leur document réel
- Boucle principale : `doc_id` et `chunk_ids` sélectionnés depuis `corpus_schedule` en mode corpus
- Compteurs `used_doc_ids: Counter` et `used_chunk_ids: set` pour tracking de couverture
- Section "Couverture corpus" ajoutée au rapport : documents/chunks disponibles vs sollicités, attempts par document, chunks/docs avec et sans skills
- `--scope corpus` dans argparse + epilog + header

### Commande lancée

```
python test_robustesse_100q.py --mock --profile mixed --username test --scope corpus --no-confirm
```

### Résultats

| Métrique | Valeur |
|---|---|
| Chunks disponibles | 295 |
| Documents disponibles | 4 |
| Documents sollicités | 4 / 4 |
| Chunks sollicités | 100 / 295 |
| Attempts sauvegardées | 100 / 100 |
| Score moyen global | 72 % |

Répartition par document :

| doc | titre | attempts |
|---|---|---|
| 1 | Procédure d'accueil voyageur | x5 |
| 2 | Addisco Ops | x6 |
| 3 | Police | x8 |
| 4 | Decrets | x81 |

| Chunks avec skills | 231 / 295 |
|---|---|
| Chunks sans skills | 64 / 295 |
| Documents avec skills | 4 / 4 |

### Diagnostic de solidité

- Moteur stable sur 295 chunks, 4 documents, 0 erreur
- `user_skill_mastery` mise à jour correctement (10 skills actifs)
- Profil recalculé tous les 10 cycles sans exception
- Isolation multi-user confirmée

### Limites observées

- Déséquilibre attendu : doc 4 (`Decrets`, ~275 chunks) capture 81/100 attempts par effet du modulo sur corpus de taille inégale.
- 64/295 chunks sans skills (22 %) : chunks courts/introductifs sans mots-clés pédagogiques. Génèrent des attempts valides mais n'alimentent pas `user_skill_mastery`.
- Couverture chunks : 100/295 (34 %) avec N=100. Couverture complète nécessiterait N >= 295.

### Invariants respectés

- 0 appel API
- `chunks.id` et documents non modifiés
- Données utilisateur `test` préservées (ajout seul)
- 227/227 tests maintenus

**Commit :** `d493a8b`

**Prochaine étape suggérée :** vue admin (gestion utilisateurs, stats globales) ou augmenter N pour couverture corpus complète.

---

## 2026-05-19 — Test corpus réels sur utilisateur cible `test`

**Objectif :** alimenter les métriques pédagogiques de l'utilisateur `test` (attempts, profil, skill mastery) via les 3 profils mock, sans créer d'utilisateur temporaire ni supprimer aucune donnée.

### Modification apportée à `test_robustesse_100q.py`

Ajout du paramètre `--username` (5 changements ciblés, 0 refactor) :

- `_get_or_create_test_user(username=TEST_USERNAME)` — paramétrisé
- `run_test(mock, profile, username=TEST_USERNAME)` — paramétrisé, rapport mis à jour
- `argparse` — nouvelle option `--username` (défaut : `test_100_questions`)
- Guard : `--cleanup` refuse tout `--username != TEST_USERNAME` (exit 1)

### Commandes lancées

```
python test_robustesse_100q.py --mock --profile good  --username test --no-confirm
python test_robustesse_100q.py --mock --profile mixed --username test --no-confirm
python test_robustesse_100q.py --mock --profile weak  --username test --no-confirm
```

### Résultats par profil

| Profil | Attempts | Score moyen | Dominant error_type |
|---|---|---|---|
| good  | 100 | 80 % | correct (80) |
| mixed | 100 | 72 % | correct (60) + reponse_vague (17) |
| weak  | 100 | 55 % | correct (30) + confusion_notion (24) |

Tous les runs : **GO SAFE**. 300/300 attempts sauvegardés.

### Métriques finales utilisateur `test` (cumulées — 300 attempts)

| Métrique | Valeur |
|---|---|
| Total attempts | 300 |
| Score moyen global | 69 % (0.689) |
| Profil pédagogique préféré | narrative |
| Erreur dominante | correct (170) · confusion_notion (42) · reponse_vague (40) · oubli_etape (33) |

### user_skill_mastery finale

| Skill | Mastery | Attempts |
|---|---|---|
| comprehension_procedure | 78 % | 9 |
| identification_concepts | 76 % | 6 |
| prise_decision | 74 % | 81 |
| analyse_causale | 74 % | 60 |
| synthese_reformulation | 72 % | 6 |
| memorisation_faits | 71 % | 57 |
| application_regles | 70 % | 30 |
| conformite_reglementaire | 69 % | 171 |
| resolution_problemes | 65 % | 33 |
| evaluation_critique | 64 % | 30 |

Skills faibles : `evaluation_critique`, `resolution_problemes`, `conformite_reglementaire`.
Skills forts : `comprehension_procedure`, `identification_concepts`.

### Invariants respectés

- Aucune donnée de `test` supprimée
- `chunks.id` non touchés
- Documents et embeddings intacts
- 0 appel API (mode mock)
- 227/227 tests maintenus

**Commit :** `c05f818`

**Prochaine étape suggérée :** ouvrir le dashboard avec l'utilisateur `test` pour valider l'affichage des métriques en conditions réelles.

---

## 2026-05-19 — ROADMAP : mise à jour phase actuelle

**Objectif :** synchroniser ROADMAP.md avec l'état réel du projet après les sessions TASK-056 à TASK-059.

### Actions

- Phases 11, 12, 14, 15 marquées **COMPLÈTE** avec commit de référence pour chacune.
- Phase 13 marquée **DIFFÉRÉE** (SQLAlchemy/PostgreSQL reporté jusqu'à disponibilité d'une `DATABASE_URL` réelle — TASK-045+046 combinables en migration unique le moment venu).
- Phase 16 marquée **EN COURS** avec :
  - liste des tâches effectivement livrées (TASK-056, 056B, 057*, 058*, 058B*, 059*) avec commits ;
  - note explicite sur la divergence entre la numérotation planifiée (vue admin / PDF / responsive) et les tâches réellement exécutées (Skills Engine, test robustesse, remap) ;
  - section "Restant à réaliser" : vue admin, rapport PDF, UX responsive.
- Phase 17 inchangée (non démarrée).

### État du projet à cette date

| Couche | État |
|---|---|
| Moteur pédagogique (RAG, adaptatif, répétition espacée) | Stable — 227/227 tests |
| Skills Engine V1.0 + V1.1 | Opérationnel — 20 chunk_skills actifs |
| Authentification multi-rôles | Opérationnel |
| Corpus multi-documents + cross-RAG | Opérationnel |
| Cockpit formateur | Opérationnel |
| Test robustesse 100q (API + mock) | Livré |
| Vue admin / rapport PDF / UX responsive | Non démarrés |
| PostgreSQL / SQLAlchemy | Différé |

**Commit :** `4f47f2c`

**Prochaine étape suggérée :** vue admin (gestion utilisateurs, stats globales) ou rapport export.

---

## 2026-05-19 — TASK-059 : Remap Skills V1.1 — documents de démo

**Objectif :** peupler `chunk_skills` sur les documents existants afin d'activer `user_skill_mastery` dans le simulateur mock.

### Contexte

Avant cette opération, les documents de démo avaient 0 `chunk_skills` — ils avaient été importés avant l'ajout du Skills Engine V1.0. Le simulateur mock créait des attempts sur des chunks sans mapping skills → `user_skill_mastery` restait vide.

### Opération

Appel de `remap_all_documents()` (db/skills.py) — keyword-only, non destructif.

### Résultats

| doc | titre | chunks éligibles | inserts | updates | désactivations |
|---|---|---|---|---|---|
| 1 | Procédure d'accueil voyageur | 4 / 5 | 10 | 0 | 0 |
| 2 | Addisco Ops | 6 / 6 | 10 | 0 | 0 |

**Total : 20 chunk_skills insérés.**

### Analytics post-remap

| Skill | Chunks | Avg weight |
|---|---|---|
| `evaluation_critique` | 6 / 11 | 0.444 |
| `resolution_problemes` | 6 / 11 | 0.500 |
| `memorisation_faits` | 4 / 11 | 0.667 |
| `prise_decision` | 2 / 11 | 0.333 |
| `identification_concepts` | 1 / 11 | 0.333 |
| `comprehension_procedure` | 1 / 11 | 0.333 |

Skills absents des docs démo : `analyse_causale`, `application_regles`, `conformite_reglementaire`, `synthese_reformulation` — vocabulaire non couvert par la procédure d'accueil voyageur.

1 chunk sans skill : en-tête d'intro du doc 1 (aucun mot-clé pédagogique détectable).

Collision principale : `resolution_problemes` × `evaluation_critique` co=3 (attendu sur chunks incidents).

### Invariants respectés

- `chunks.id` intouchables — aucun chunk modifié
- `is_validated=1` — aucune ligne de ce type présente (tous inserts frais)
- Aucun attempt supprimé

### Validation — rerun mock weak

Après remap, `test_robustesse_100q.py --mock --profile weak` produit :

```
comprehension_procedure    68%  (9 tent.)
resolution_problemes       56%  (54 tent.)
memorisation_faits         53%  (36 tent.)
evaluation_critique        52%  (54 tent.)
identification_concepts    50%  (9 tent.)
prise_decision             40%  (18 tent.)
```

6 skills alimentés (vs 0 avant remap). Verdict : **GO SAFE**.

### Prochaine étape suggérée

Vérifier le dashboard pédagogique Zone 8 avec un utilisateur réel après quelques tentatives sur les documents remappés.

---

## 2026-05-19 — TASK-058B : Mode mock — test robustesse 100 questions

**Objectif :** permettre un test complet sans appels API OpenAI pour valider la robustesse du moteur (attempts, profil, skill mastery, analytics) en < 5 secondes.

### Ajouts à `test_robustesse_100q.py`

```
python test_robustesse_100q.py --mock                   # profil mixed (défaut)
python test_robustesse_100q.py --mock --profile good    # 80 % bonnes / 20 % partielles
python test_robustesse_100q.py --mock --profile weak    # 30 % / 50 % / 20 % mauvaises
python test_robustesse_100q.py --mock --profile random  # aléatoire à chaque lancement
```

### Distribution des profils

| Profil | good (0.75–1.0) | partial (0.35–0.65) | bad (0.0–0.34) |
|---|---|---|---|
| `good` | 80 % | 20 % | 0 % |
| `mixed` | 60 % | 40 % | 0 % |
| `weak` | 30 % | 50 % | 20 % |
| `random` | aléatoire | — | — |

### Fonctions ajoutées

- `_build_mock_score_schedule(n, profile, seed)` — distribution déterministe (seed=42)
- `_mock_score(band, rng)` — retourne `(score, error_type)` cohérents
- Pools locaux : 15 questions, 15 topics, 6 question_types
- `run_test(mock, profile)` — branche `if mock:` sans modifier le chemin API

### Validation

- GO SAFE sur les 3 commandes de validation (mixed, random, cleanup)
- Durée : < 1 seconde pour 100 cycles
- Mode API inchangé — 0 régression
- 227/227 tests maintenus

---

## 2026-05-19 — TASK-058 : Test de robustesse pédagogique — 100 questions simulées

**Objectif :** vérifier la robustesse de l'ensemble du moteur ADDISCO OPS (RAG, attempts, profil, skill mastery, multi-user) par un test contrôlé end-to-end simulant un utilisateur réel sur 100 questions.

### Fichier livré

`test_robustesse_100q.py` — script autonome, non collecté par pytest.

```
python test_robustesse_100q.py            # lance le test (confirmation interactive)
python test_robustesse_100q.py --no-confirm  # mode CI
python test_robustesse_100q.py --cleanup  # efface les données du user test
```

### Isolation et réversibilité

- Utilisateur test dédié : `test_100_questions` (rôle apprenant)
- Toutes les données écrites sous ce `user_id` — zéro pollution des vrais utilisateurs
- `--cleanup` supprime proprement attempts + profil + skill mastery + user (DELETE ciblé)
- Relançable à l'identique (seed=42, distribution déterministe)
- Aucune modification des documents, chunks ou attempts existants

### 100 cycles par question

Pour chaque cycle : `generate_question` → réponse simulée → `correct_answer` → `save_attempt` → recalcul profil tous les 10 cycles.

### Distribution des réponses simulées (seed=42, déterministe)

| Type | N | Comportement attendu |
|---|---|---|
| `good` | 40 | extrait du chunk → score élevé |
| `partial` | 25 | extrait court → score moyen |
| `bad` | 15 | affirmation contraire → score faible |
| `short` | 10 | "Je ne sais pas." → score très faible |
| `off_topic` | 10 | hors sujet total → hors_sujet |

### Vérifications post-test

- Historique attempts peuplé (`get_attempts`)
- Profil calculé (`get_learning_profile`)
- `user_skill_mastery` mise à jour
- Isolation multi-user (autres tentatives non touchées)
- Taux cycles réussis ≥ 90 %

### Verdict automatique

- **GO SAFE** : 0 erreur, ≥ 90 % cycles, profil + mastery OK
- **GO WITH WARNING** : ≥ 90 % cycles mais erreurs non bloquantes
- **FAILED** : < 90 % cycles ou crash bloquant

### Contraintes respectées

- `chunks.id` intouchable — aucun chunk modifié
- `attempts` immutables — INSERT uniquement pour le user test
- Fallback mode préservé — test fonctionne sans embeddings
- 227/227 tests de régression maintenus

### Prochaine étape suggérée

Lancer le test sur la DB réelle et analyser le rapport (répartition error_type, skills détectés, score moyen par type de réponse).

---

## 2026-05-19 — TASK-057 : Skills Engine V1.0 + V1.1

**Objectif :** couche analytique skills déterministe — mapper automatiquement les chunks à des compétences pédagogiques sans dépendance réseau ni IA, puis calibrer et outiller le debug.

### Architecture créée

```
engine/
├── skill_keywords.py   — SKILL_KEYWORDS : 10 slugs → listes keywords (V1.1 calibrée)
├── skill_mapper.py     — classify_chunk_skills(), keyword_match_score()
├── skill_engine.py     — compute_skill_mastery(), classify_skill_mastery()
├── skill_debug.py      — explain_skill_detection(), explain_chunk_skills() [lecture seule]
└── skill_analytics.py  — 6 fonctions analytiques descriptives [lecture seule]

db/
└── skills.py           — CRUD complet + seed 10 slugs + remap V1.1
```

### Tables ajoutées (database.py)

| Table | Rôle |
|---|---|
| `skills` | Référentiel 10 slugs, immutables après déploiement |
| `chunk_skills` | Lien chunk ↔ skill avec weight, source, is_validated, is_active |
| `user_skill_mastery` | Score de maîtrise par user × skill, mis à jour après chaque profil |

### Invariants critiques respectés

- `chunks.id` — jamais recréé, jamais supprimé
- `attempts` — immutable après insertion
- `is_validated=1` — intouchable par tout remap automatique
- `chunk_skills` — couche additive uniquement (INSERT OR IGNORE en V1.0)
- Pipeline ingestion — si mapping skills échoue → log warning → ingestion continue
- Application — fonctionnelle avec 0 skill, 0 mapping, 0 mastery

### V1.0 — Foundation

- `classify_and_save_document_skills()` appelé à la fin de chaque ingestion (non bloquant)
- `update_user_skill_mastery()` appelé à la fin de `compute_and_save_learning_profile()` (non bloquant)
- Zone 8 dans tab_dashboard.py : barres de maîtrise par skill (Fragile / En cours / Acquis)

### V1.1 — Calibration & Debug

- **Keywords calibrés** : retrait de 10 termes trop génériques (`doit`, `procédure`, `puis`, `ensuite`, `traiter`, `gérer`, `en cas de`, `sécurité`, `article`, `ainsi`)
- **`remap_document_skills()`** : recalcule les mappings keyword sans toucher `is_validated=1`; soft-delete (`is_active=0`) des skills obsolètes
- **Expander Debug V1.1** dans tab_dashboard.py : fréquence skills, collisions, diagnostic chunk (compare DB vs live)
- **Bouton "Recalculer les skills V1.1"** dans tab_documents.py : remap par document à la demande

### Validations

- py_compile 7 fichiers OK
- **227/227 tests** — aucune régression
- Fallback mode préservé

### Prochaine étape suggérée

Valider le mapping sur des documents réels (bouton remap → vérifier discriminabilité des skills via l'expander Debug), puis envisager V1.2 : scoring adaptatif skill-aware dans `build_session_plan()`.

---

## 2026-05-19 — TASK-056B : UX Polish / Densification visuelle cockpit formateur

**Objectif :** passer du prototype validé à une interface premium, dense et crédible professionnellement.

### Améliorations par composant

| Composant | Changement |
|---|---|
| `learner_card.py` | Full HTML compact — single `st.markdown()`, progress bar 5px, pills metadata, ~40% moins de hauteur |
| `adaptive_profile.py` | CSS grid HTML (2 col) — supprime l'overhead `st.columns()`, cards `.ap-card` avec hover indigo |
| `stat_card.py` | Paramètre `trend_str` : indicateur ↗/↘/→ coloré sous la valeur |
| `alerts_panel.py` | Padding réduit 12px→10px, transitions CSS |
| `progress_chart.py` | Palette indigo primaire, barres opacity .85, messages vides gracieux |
| `recommendation_panel.py` | Classe `.rec-card` avec hover, badge priority 9.5px compact |
| `trainer_dashboard.py` | CSS global `_COCKPIT_CSS`, header accent bar indigo, `_section_header()` indigo, apprenants 2 colonnes, tendances KPI, charts dans `st.container(border=True)` |

### CSS global (`_COCKPIT_CSS`)

- `.lc:hover` — ombre indigo subtile + border #c7d2fe
- `.ap-card:hover` — ombre légère + border #cbd5e1
- `.rec-card:hover` — fond #f1f5f9
- `stVerticalBlockBorderWrapper:hover` — ombre globale sur containers Streamlit

### Tendances KPI

- Mode mock : `↗ +8 pts cette semaine` · `→ stable` · `↘ −1 vs hier`
- Mode réel : `_score_trend_str()` — delta premier/second moitié de `get_score_evolution()`

**Validations :** py_compile 7 fichiers OK · **206/206 tests** · Streamlit HTTP 200

### Prochaine étape suggérée

TASK-057 : vue admin — gestion des utilisateurs, stats globales plateforme.

---

## 2026-05-19 — TASK-056 : Cockpit Pédagogique Formateur — Dashboard Premium

**Objectif :** transformer l'onglet Formateur en cockpit pédagogique professionnel à fort impact visuel et démonstratif.

### Architecture créée

```
frontend/
└── dashboard/
    ├── trainer_dashboard.py        — orchestrateur principal
    ├── components/
    │   ├── stat_card.py            — KPI cards HTML pures (no Streamlit)
    │   ├── learner_card.py         — fiche individuelle apprenant
    │   ├── alerts_panel.py         — panneau d'alertes pédagogiques
    │   ├── adaptive_profile.py     — profils IA détectés
    │   ├── progress_chart.py       — graphiques progression + erreurs
    │   └── recommendation_panel.py — recommandations pédagogiques IA
    └── mock_data/
        └── trainer_mock_data.py    — 4 apprenants, 4 profils, 3 alertes, 4 reco
```

### Modifications

| Fichier | Changement |
|---|---|
| `tabs/tab_trainer.py` | Thin wrapper → `_render_cockpit()` + `_render_admin_section()` |
| `frontend/dashboard/trainer_dashboard.py` | Orchestrateur : réel si ≥ 2 apprenants, mock sinon |
| `frontend/dashboard/components/*` | 6 composants réutilisables |
| `frontend/dashboard/mock_data/trainer_mock_data.py` | Données démo centralisées |

### Fonctionnalités livrées

- **Header KPI** : 5 stat cards (apprenants, score moyen, actifs, documents, alertes)
- **Alertes pédagogiques** : panneau priorisé critical/warning/info avec recommandation rapide
- **Cartes apprenants** : score, progression, profil IA, difficulté dominante, statut, tendance
- **Profils adaptatifs IA** : 4 profils (séquentiel, surcharge cognitive, mémoire contextuelle, répétition espacée)
- **Analyse de performance** : graphique d'évolution + distribution des erreurs en barres colorées
- **Recommandations IA** : 3–4 recommandations priorisées générées depuis les données réelles
- **Export rapport** : texte structuré `.txt` avec synthèse cohorte + détail apprenant + alertes + recommandations

### Invariants respectés

- Aucune modification moteur (ai_service, database, rag_service, adaptive_engine)
- Aucune migration DB
- `_render_admin_section()` préservée à l'identique
- Mode réel activé automatiquement dès ≥ 2 apprenants inscrits (structure identique mock/réel)

**Validations :** py_compile 12 fichiers OK · **206/206 tests** · Streamlit HTTP 200 (port 8560)

### Prochaine étape suggérée

TASK-057 : vue admin — gestion des utilisateurs (activation/désactivation), stats globales plateforme.

---

## 2026-05-18 — TASK-055B : Correction UX — contexte RAG visible après génération

**Objectif :** afficher explicitement le document source, la section et un extrait du chunk utilisé par le RAG avant la question générée.

### Modifications

| Fichier | Changement |
|---|---|
| `db/chunks.py` | `get_chunk_by_id(chunk_id)` — SELECT chunks JOIN documents, retourne `section_label`, `document_title`, `chunk_text` |
| `database.py` | Re-export de `get_chunk_by_id` + `__all__` |
| `tabs/tab_training.py` | Import · fetch chunk primaire après génération · stockage session state · bloc `📄 Contexte RAG utilisé` avant la question · reset dans le cas aucun chunk |
| `test_regression.py` | `TestGetChunkById` (3 tests) |

**Comportements garantis :**
- `ai_service.py` / `generate_question()` : **zéro modification** — moteur indépendant de l'UI
- Mono-doc : contexte affiché (document + section + extrait)
- Corpus multi-doc : contexte affiché (document source du chunk primaire + section)
- Mode texte brut (aucun chunk) : expander absent, aucun crash
- Fetch échoue : try/except silencieux → question fonctionnelle, contexte omis

**Validations :** py_compile OK · **206/206 tests** · Streamlit HTTP 200

### Prochaine étape suggérée

TASK-056 : dashboard formateur avancé (Phase 16).

---

## 2026-05-18 — TASK-055 : Recherche sémantique corpus complet — clôture Phase 15

**Objectif :** étendre `search_similar_chunks_multi()` pour accepter `document_ids=None` → recherche sur tout le corpus sans filtre `document_id`.

### Modifications

| Fichier | Changement |
|---|---|
| `rag_service.py` | `Optional[list[int]]` sur `document_ids` · branche SQL sans `WHERE document_id IN (...)` quand `None` · garde `[]` → return immédiat inchangée |
| `ai_service.py` | Branche `else` corpus complet — `search_similar_chunks_multi(None)` quand ni `document_id` ni `document_ids` fourni |
| `test_regression.py` | `TestCorpusSearch` (5 tests) · correction mock manquant sur `test_happy_path_no_rag` |

**Comportements garantis :**
- `search_similar_chunks(document_id)` → **strictement inchangé**
- `search_similar_chunks_multi([1,2,3])` → **strictement inchangé**
- `search_similar_chunks_multi([])` → `[]` immédiat **inchangé**
- `search_similar_chunks_multi(None)` → SQL corpus complet, top-k respecté
- `generate_question()` sans doc → corpus complet (fallback texte brut si corpus vide)

**Invariants respectés :**
- Aucun DELETE+INSERT, aucune migration DB
- Fallback texte brut préservé si le corpus complet retourne []
- `document_ids` reste prioritaire sur `document_id` et sur le mode corpus
- Backward compat totale — aucun caller existant cassé

**Limites connues (à documenter pour Phase 13+) :**
Le mode corpus complet (`document_ids=None`) charge tous les chunks avec embedding en mémoire et calcule la similarité cosinus en Python. Acceptable pour MVP / ~50 documents. Au-delà, envisager : ranking plus avancé, limite de chunks pré-filtrée, cache, index ANN, pgvector (Phase 13), ou base vectorielle dédiée.

**Validations :** py_compile OK · **203/203 tests** · Streamlit HTTP 200

### Clôture Phase 15

Phase 15 — Multi-documents et corpus : TASK-052 (DOCX) + TASK-053 (catégories) + TASK-054 (entraînement cross-docs) + TASK-055 (corpus complet RAG) = **Phase 15 complète**.

### Prochaine étape suggérée

TASK-056 : dashboard formateur avancé (Phase 16 — UX professionnelle finale).

---

## 2026-05-18 — TASK-054 : Entraînement cross-documents / corpus RAG multi-docs

**Objectif :** permettre de s'entraîner sur un corpus multi-documents via RAG sémantique.

### Modifications (commit 2041154)

| Fichier | Changement |
|---|---|
| `rag_service.py` | `search_similar_chunks_multi(query_embedding, document_ids, top_k)` — IN clause, même ranking cosinus |
| `ai_service.py` | `generate_question(document_ids=None)` — branche multi-doc prioritaire sur `document_id` |
| `tabs/tab_training.py` | Sentinel `_CORPUS=-1` · option corpus dans sélecteur · label dynamique catégorie/complet · sync `active_document_ids` · `save_attempt(document_id=None)` en mode corpus |
| `test_regression.py` | `TestCrossDocuments` (5 tests) |

**Invariants respectés :**
- `document_ids` prioritaire sur `document_id` — backward compat totale (tous les callers existants passent `document_id` uniquement)
- Fallback RAG multi-doc → texte brut si embedding API échoue (même garde que mono-doc)
- `save_attempt(document_id=None)` acceptable en mode corpus — FK nullable
- Sentinel `_CORPUS=-1` jamais un AUTOINCREMENT SQLite valide
- `active_document_ids` resyncé à chaque render selon le filtre catégorie actif

**Validations :** py_compile OK · **198/198 tests** · Streamlit HTTP 200

### Prochaine étape suggérée

TASK-055 ou suite UX / dashboard.

---

## 2026-05-18 — TASK-053 : Catégories de documents

**Objectif :** structurer la bibliothèque par catégorie sans casser l'existant.

### Modifications (commit 8bb0b57)

| Fichier | Changement |
|---|---|
| `database.py` | Migration douce `ALTER TABLE documents ADD COLUMN category TEXT` |
| `db/chunks.py` | `save_document(category=None)` + `d.category` dans `get_documents()` |
| `document_service.py` | `ingest_document(category=None)` → transmis à `save_document` |
| `tabs/tab_documents.py` | Champ catégorie dans le form · filtre selectbox · badge 🏷 |
| `tabs/tab_training.py` | Filtre catégorie au-dessus du sélecteur (masqué si sans catégories) |
| `test_regression.py` | `TestDocumentCategory` (6 tests) |

**Invariants respectés :**
- Migration idempotente : `try/except OperationalError` — base existante préservée, document de démo inchangé
- `category=None` par défaut partout → backward compat totale, aucun caller existant cassé
- Normalisation : `strip()` + `""` → `None` dans `save_document`
- Aucun DELETE+INSERT, aucun changement pipeline IA

**Validations :** py_compile OK · **214/214 tests** · migration DB vérifiée · Streamlit HTTP 200

### Prochaine étape suggérée

TASK-054 : entraînement cross-documents — `generate_question()` accepte une liste de `document_id`.

---

## 2026-05-18 — TASK-052 : Support DOCX (document_service.py)

**Objectif :** ajouter le support DOCX au pipeline d'ingestion existant sans modifier le reste du moteur.

### Modifications (commit aa93bbb)

| Fichier | Changement |
|---|---|
| `document_service.py` | +`_extract_text_docx()` + 1 branche dans `_extract_text()` |
| `tabs/tab_documents.py` | `type=["txt","pdf","docx"]` + label "TXT, PDF ou DOCX" |
| `requirements.txt` | +`python-docx==1.2.0` |
| `test_regression.py` | +`TestDocxExtraction` (3 tests) |

**Invariants respectés :**
- Import lazy (`try/except ImportError`) — python-docx absent → `ValueError` user-readable + hint `pip install python-docx`
- Pipeline inchangé : extract → clean → chunk → embed — aucune modification des autres étapes
- Aucun changement DB (source_type TEXT accepte "docx" sans migration)
- Moteur IA inchangé

**Tests DOCX :** happy path (3 paragraphes extraits) · DOCX vide → ValueError · ImportError mocké via `sys.modules` → ValueError

**Validations :** py_compile OK · **208/208 tests** · Streamlit HTTP 200

### Prochaine étape suggérée

Architecture Guard audit post-TASK-052.
TASK-053 : catégories de documents (colonne `category` dans `documents`).

---

## 2026-05-18 — TASK-050 + TASK-051 : Plan de session et Rétention (UI Dashboard)

**Objectif :** afficher les deux dernières sorties du moteur adaptatif dans le Dashboard.

### Modifications (commit 5f88999)

- `tabs/tab_dashboard.py` — **seul fichier modifié** (+66 lignes, +2 imports)

**Zone 2b — Plan de session (TASK-050)**
- `get_next_session_plan()` → jusqu'à 5 sections ordonnées par priorité
- Chaque item : rang · section · document / objectif pédagogique · badge mastery · score · durée estimée · statut révision
- Masqué si aucune donnée (pas de chunk avec historique)

**Zone 4e — Rétention pédagogique (TASK-051)**
- `get_retention_metrics()` → 3 KPI cards 🧠 J+1 / 📅 J+7 / 📆 J+30
- Code couleur : vert ≥ 70 % · orange ≥ 50 % · rouge < 50 % · gris —
- Message d'attente si toutes les valeurs sont None (données insuffisantes)

**Validations :** `py_compile` OK · **205/205 tests** · Streamlit HTTP 200

### Prochaine étape suggérée

Architecture Guard audit pour confirmer l'état du projet post-Phase 15.
TASK-052 si phase 15 complète (support DOCX).

---

## 2026-05-18 — TASK-049 : Profil utilisateur enrichi (UI Dashboard)

**Objectif :** afficher les 3 métriques dynamiques calculées depuis Phase 14 dans le Dashboard.

**Constat pré-implémentation :** backend 100% complet (compute, store, retrieve, 25+ tests). Seule la couche UI manquait.

### Modification (commit d698cc0)

- `tabs/tab_dashboard.py` — **seul fichier modifié**
- Zone 7 (Profil d'apprentissage) : ajout d'une ligne « Dynamique d'apprentissage » après les 4 scores pédagogiques
- 3 KPI cards réutilisant `_kpi_card` existant :
  - **Momentum 7j** : 📈/📉/➡️ · +XX % vert / −XX % rouge / Stable gris
  - **Vélocité** : ⚡ · même code couleur
  - **Régularité 30j** : 🔄 · ≥ 50 % vert · ≥ 30 % orange · > 0 % rouge · 0 gris
- Aucun nouvel appel DB — `get_learning_profile()` déjà appelé ligne 373
- Aucun changement backend, DB, helpers

**Validations :**
- `py_compile` : OK
- Tests : **205/205 OK**
- Streamlit : HTTP 200

### Prochaine étape suggérée

TASK-050 : afficher `get_next_session_plan` dans le Dashboard (backend déjà complet).
TASK-051 : afficher les métriques de rétention J+1/J+7/J+30 (backend déjà complet).

---

## 2026-05-18 — Segmentation database.py → db/ + Migration ai_service → ai_gateway

**Objectif :** réduire la dette technique identifiée par l'Architecture Guard (database.py 719L CRITICAL) et compléter la migration ai_service → gateway.

### Migration ai_service → ai_gateway (commit 4c5cda4)

- `ai_gateway/gateway.py` : ajout `call_embedding_api()` + normalisation contenu vide → `None`
- `ai_service.py` : suppression `_get_client()` + `_client` singleton — 3 call sites délégués au gateway (`question_generation`, `correction`, `embedding`)
- `test_regression.py` : patches migrés `ai_service._get_client` → `ai_service.call_chat_completion` (pattern : toujours patcher là où le nom est importé)
- **Piège résolu :** `@patch("ai_gateway.gateway.call_chat_completion")` ne fonctionne pas — il faut `@patch("ai_service.call_chat_completion")`

### Segmentation database.py → db/ (commit 7e2c5f4)

| Avant | Après |
|-------|-------|
| `database.py` 719 lignes (CRITICAL) | `database.py` 162 lignes (facade) |
| — | `db/analytics.py` 115 lignes — tentatives & analytics |
| — | `db/chunks.py` 245 lignes — documents, chunks, maîtrise |
| — | `db/profile.py` 172 lignes — profil utilisateur, rétention |
| — | `db/admin.py` 50 lignes — gestion utilisateurs |

**Backward compatibility totale :** `from database import X` fonctionne pour tous les callers existants.

**Pattern import circulaire :** chaque sous-module fait `import database as _db` au niveau module et accède à `_db.DB_PATH` à l'intérieur des fonctions — le monkey-patch des tests (`database.DB_PATH = tmp`) est respecté car l'attribut est lu à l'heure d'appel.

**Architecture Guard après segmentation :** `database.py` disparaît de la liste CRITICAL.

- `py_compile` : 5/5 OK
- Tests : **184/184 OK**

### Prochaine étape suggérée

Segmenter `adaptive_engine.py` (534 lignes, encore CRITICAL) ou passer à une autre priorité produit.

---

## 2026-05-18 — Segmentation adaptive_engine.py → engine/

**Objectif :** éliminer le dernier fichier CRITICAL identifié par l'Architecture Guard (adaptive_engine.py 534L).

### Résultat (commit 55ade6b)

| Avant | Après |
|-------|-------|
| `adaptive_engine.py` 534 lignes (CRITICAL) | `adaptive_engine.py` 57 lignes (façade) |
| — | `engine/spaced_rep.py` 103 lignes — REVIEW_INTERVALS, _adaptive_interval, classify_mastery |
| — | `engine/question_type.py` 123 lignes — types, biais mastery, rotation, explicabilité |
| — | `engine/profile_metrics.py` 79 lignes — momentum, vélocité, régularité |
| — | `engine/retention.py` 55 lignes — métriques rétention j1/j7/j30 |
| — | `engine/session_plan.py` 142 lignes — priorités, objectifs, build_session_plan |

**Backward compatibility totale :** `from adaptive_engine import X` et `from database import X` (chaîne) continuent de fonctionner pour tous les callers.

**Aucun caller modifié :** `database.py`, `db/profile.py`, `ai_service.py`, `app.py`, `tabs/` inchangés.

**Architecture Guard après segmentation :** aucun fichier CRITICAL restant dans le projet.

- `py_compile` : 6/6 OK (tous les fichiers engine/)
- Post-condition imports : 19 symboles vérifiés depuis `adaptive_engine` + chaîne `database`
- Tests : **205/205 OK**

### Prochaine étape suggérée

TASK-049 — profil utilisateur enrichi, ou audit Architecture Guard pour confirmer zéro CRITICAL.

---

## 2026-05-18 — Phase 15B — Fondation architecture & industrialisation progressive

**Objectif :** créer les premières briques de gouvernance sans over-engineering — 3 modules sur 6 retenus après analyse Conseil, 3 reportés explicitement.

### Modules implémentés (valeur immédiate)

**1. `ai_gateway/` — Point d'entrée unique pour les appels IA**
- `gateway.py` : `call_chat_completion()` — wrapper OpenAI chat completions avec logging automatique des requêtes. Client lazy-init indépendant.
- `request_logger.py` : `log_request()` — appende une ligne JSON dans `logs/ai_requests.jsonl` (timestamp UTC, task_type, duration_ms, ok).
- Migration vers `ai_service.py` : **prochaine étape documentée** — non faite ici pour préserver la stabilité.

**2. `architecture_guard/` — Audit fichiers et gouvernance de taille**
- `rules.py` : seuils WARN=300, CRITICAL=500 lignes — exclusion test_*/seed_*.
- `file_audit.py` : `audit_project()` + `print_audit_report()` — scan des fichiers Python du projet.
- **Résultat immédiat de l'audit :**

| Fichier | Lignes | Niveau |
|---------|-------:|--------|
| `database.py` | 719 | CRITICAL |
| `adaptive_engine.py` | 534 | CRITICAL |
| `document_service.py` | 372 | WARN |
| `ui_helpers.py` | 358 | WARN |

**3. `observability/` — Métriques légères et suivi d'erreurs**
- `metrics.py` : `increment()`, `record_timing()`, `get_summary()`, `flush_to_disk()` — compteurs et moyennes en mémoire + persistance JSON dans `logs/metrics.json`.
- `error_tracker.py` : `track()`, `get_recent()` — deque 100 entrées + persistance JSONL dans `logs/errors.jsonl`.

### Décisions de report (anti over-engineering)

| Module | Décision | Raison |
|--------|----------|--------|
| `flow_router/` | **Reporté** | Aucun flux à gouverner — app synchrone monolithique. À créer quand un pipeline async/batch réel existe. |
| `queue_manager/` | **Reporté** | Aucune queue réelle — un dict en mémoire sans worker n'apporte que de la dette cognitive. À créer quand un worker async est nécessaire. |
| Multi-docs prep | **Reporté** | Abstraction prématurée — les structures émergeront naturellement quand les exigences multi-docs seront spécifiées. |

### Validation

- `py_compile` : 9/9 fichiers OK
- Tests de régression : **184/184 OK** (0 régression)
- Smoke test fonctionnel : `audit_project()`, `increment()`, `record_timing()`, `track()`, `call_chat_completion` import OK

### Prochaine étape

Migration de `ai_service.py` → `ai_gateway.call_chat_completion()` pour les 2 call sites LLM (lignes 198 et 232). Segmentation de `database.py` (719 lignes, CRITICAL) en sous-modules analytics/profile/chunks.

---

## 2026-05-17 — Bilan structurel — Conseil des 5 agents — Note 79/100

**Objectif :** évaluation complète de la structure du projet avant ouverture de Phase 15 — architecture, qualité code, tests, sécurité, robustesse.

**Résultat global : 79/100**

| Dimension | Score | Observations |
|-----------|------:|--------------|
| Architecture | 82 | Modularité exemplaire, ROADMAP Phase 0→17 complète. `database.py` trop gros (710 lignes), ARCHITECTURE.md partiellement obsolète. |
| Qualité code | 81 | Fonctions pures, guards défensifs, corrections minimales, annotations cohérentes. `config.py` orphelin. |
| Revue critique | 74 | Anti-régressions solides. Couverture UI = 0 %, `ai_service.py` non mocké. |
| Tests | 76 | 168 tests, isolation DB parfaite, 0 régression. Monofichier 1697 lignes, pas de tests perf. |
| Sécurité | 83 | bcrypt, hmac, no SQLi, UX-01 corrigé. Rate limiting absent, erreurs brutes exposées. |

**Points forts identifiés :**
- `adaptive_engine.py` = module pur, zéro import projet — contrainte tenue pendant 4 phases.
- Vision industrielle réelle : architecture cible documentée, Phases 11→17 planifiées avec critères de sortie et risques.
- 120 commits — progression incrémentale sans régression.

**Points à adresser pour dépasser 90 :**
- Tests d'intégration `ai_service` avec mock OpenAI.
- Segmenter `database.py` en sous-modules (analytics, profile, chunks).
- Rate limiting LLM par utilisateur.
- Synchroniser ARCHITECTURE.md avec l'état réel du code.

---

## 2026-05-17 — Audit UX pré-Phase 15 — 4 corrections (Commit `36306ca`)

**Objectif :** identifier les erreurs UX, incohérences et flux fragiles non détectés par les tests backend.

**Résultat : 10 problèmes identifiés — 4 corrections — 6 observations documentées.**

**UX-01 (CRITIQUE) — Fuite de données inter-utilisateurs — `app.py` :**
- Cause : logout nettoyait `user_id/username/role` mais pas les clés pédagogiques. L'utilisateur B voyait la question/réponse de l'utilisateur A après login sur le même navigateur.
- Correction : le handler logout efface explicitement toutes les clés pédagogiques (`question`, `source_text_input`, `answer_input`, `result`, `chunk_ids`, `active_document_id`, etc.).

**UX-02 (SÉRIEUX) — `answer_input` non effacé à la génération — `tab_training.py` :**
- Cause : "Générer une question" ne vidait pas `answer_input`. L'ancienne réponse persistait dans la zone texte d'une nouvelle question.
- Correction : `st.session_state["answer_input"] = ""` ajouté dans le bloc génération.

**UX-03 (MODÉRÉ) — État vide manquant — graphe "Évolution des scores" — `tab_dashboard.py` :**
- Cause : `if not df_evol.empty:` sans `else` → titre de section orphelin au-dessus d'un espace vide.
- Correction : `else: st.caption("Pas encore de données d'évolution.")`.

**UX-04 (MODÉRÉ) — Pas de spinner — "Calculer le profil" — `tab_dashboard.py` :**
- Cause : `compute_and_save_learning_profile()` appelé sans feedback visuel — interface figée silencieusement.
- Correction : `with st.spinner("Calcul du profil…"):`.

**Observations documentées (pas de code) :**
- UX-05 : Demo mode voit tous les onglets — intentionnel.
- UX-06 : Mini-timeline newest→oldest (L→R) — cosmétique.
- UX-07 : Erreurs API brutes exposées — acceptable MVP.
- UX-09 : Tab "Formateur" = vue self, pas superviseur multi-apprenants — design documenté.
- UX-10 : Isolation multi-user complète en mode auth confirmée.

**Résultat :** 168 tests. 0 régression. 3 fichiers modifiés.

---

## 2026-05-17 — Snapshot final pré-Phase 15 (Commit `18f83df`)

**Objectif :** photographie stable et restaurable du projet avant ouverture de Phase 15 multi-documents.

**Contenu :** 34 fichiers source — tous modules Python, `tabs/`, `TASKS/`, docs projet (ROADMAP, ARCHITECTURE, PRD, TASK_MASTER), App Factory, `database.db` + `revision.db` (copiés via `sqlite3.backup()` — API safe), `BACKUP_INFO.md` complet.

**Localisation :**
- Dossier : `backups/snapshot_pre_phase15_final_20260517_1928/`
- ZIP : `backups/snapshot_pre_phase15_final_20260517_1928.zip` (174 KB)
- Commit de référence : `36306ca`

**État au snapshot :** Phase 14 complète (TASK-048 → TASK-051) + audit UX intégré. 168 tests. 0 régression.

**Points de vigilance Phase 15 documentés dans BACKUP_INFO.md :**
1. `adaptive_engine.py` = module pur — contrainte à préserver.
2. `attempts.chunk_id` et `chunks.id` — IDs stables, jamais DELETE+INSERT.
3. Guard `if df.empty: return df` dans `classify_mastery()` — ne pas retirer.
4. `pd.isna()` obligatoire pour les valeurs nulles datetime (pandas 2.x).
5. Tout nouveau state pédagogique ajouté en Phase 15 doit figurer dans la liste de nettoyage logout (`app.py`).

---

## 2026-05-17 — Audit anti-régression Phase 15 — 2 bugs corrigés + 11 tests (Commit `0169d9c`)

**Objectif :** inspection complète du code avant Phase 15 — détecter les bugs silencieux non couverts par les 155 tests existants.

**BUG-1 — `get_topic_stats` : avg_score NaN → crash `astype(int)` — `database.py` :**
- Cause : `AVG(NULL)` = NULL en SQLite → pandas NaN → `.astype(int)` lève `IntCastingNaNError`.
- Correction : `AND score IS NOT NULL` ajouté dans le WHERE.

**BUG-2 — `classify_mastery` crash sur DataFrame vide — `adaptive_engine.py` :**
- Cause : `df.apply(func, axis=1)` sur un DataFrame sans colonnes retourne un DataFrame (pas une Series) → `df["col"] = DataFrame` lève `ValueError`.
- Correction : `if df.empty: return df` ajouté en tête de fonction.

**`TestAntiRegressionPhase15` — 11 tests de régression :**
- `test_pipeline_user_without_history`
- `test_chunk_without_attempts_excluded_from_stats`
- `test_attempt_null_score_excluded_from_chunk_stats`
- `test_topic_stats_no_nan_with_null_score` (BUG-1)
- `test_classify_mastery_empty_df_no_crash` (BUG-2)
- `test_classify_mastery_heterogeneous_chunks_all_scalars`
- `test_build_session_plan_priority_score_always_float`
- `test_user_metrics_bounded_0_1`
- `test_user_isolation_full_pipeline`
- `test_classify_mastery_invalid_date_no_crash`
- `test_retention_no_chunk_id_returns_all_none`

**Résultat :** 168 tests. 0 régression.

---

## 2026-05-17 — Fix runtime : classify_mastery crash pandas 2.x NaT (Commit `eaf6e07`)

**Cause :** `_next_review` retournant `None`, pandas 2.x infère le dtype `datetime64[us]` sur la colonne et convertit `None` → `pd.NaT`. `pd.NaT is None` = `False` — le guard original était inopérant. `pd.NaT.date()` retourne `NaT`, qui ne peut pas être soustrait à `datetime.date` → `ValueError` en cascade.

**Corrections dans `adaptive_engine.py` :**
- `_days_until` : remplacement de `if nxt is None` par `if nxt is None or pd.isna(nxt)`, ajout d'un `try/except` global et cast `int()` explicite.
- `_review_status` : guard défensif `if d is None or pd.isna(d)`.

**Test ajouté :**
- `test_days_until_review_scalar_with_null_date` dans `TestClassifyMastery` — reproduit exactement le crash avec un DataFrame mixant dates valides et `None`.

---

## 2026-05-17 — TASK-051 : Métriques de rétention pédagogique J+1 / J+7 / J+30

**Objectif :** mesurer la rétention observable sur 3 fenêtres temporelles — révision lendemain (j1), hebdomadaire (j7), mensuelle (j30).

**adaptive_engine.py — 2 ajouts :**
- `_RETENTION_WINDOWS` (dict 3 entrées) — fenêtres en jours : j1=(0.5, 2.5), j7=(4.0, 10.0), j30=(21.0, 45.0).
- `compute_retention_metrics(rows)` — fonction pure. Reçoit `list[tuple[chunk_id, created_at_iso, score]]`. Groupe par chunk_id, trie par date, analyse les paires consécutives. Si l'écart tombe dans une fenêtre, le score de la révision est collecté. Retourne la moyenne par fenêtre, ou None si aucune paire trouvée. Borné [0.0, 1.0]. Guards : score=None ignoré, date invalide ignorée.

**database.py — 2 changements :**
- Import étendu : `compute_retention_metrics` ajouté.
- `get_retention_metrics(user_id)` — wrapper DB minimal : SELECT (chunk_id, created_at, score) WHERE score IS NOT NULL AND chunk_id IS NOT NULL, puis délègue à `compute_retention_metrics`. Calculé à la volée, non stocké en base.

**test_regression.py — 16 nouveaux tests :**
- `TestComputeRetentionPure` (13 tests) : liste vide, clés toujours présentes, une seule tentative par chunk, j1/j7/j30 détectés, écart hors fenêtre ignoré, moyenne sur plusieurs chunks, deux fenêtres sur une même chaîne de 3 tentatives, bornage, date invalide ignorée, score None ignoré, chunks différents non croisés.
- `TestGetRetentionMetricsDb` (3 tests) : sans historique → tout None, j1 détecté en DB, isolation utilisateur.

**Résultat :** 155 tests. 0 régression. py_compile 3/3 OK.

**Invariants préservés :**
- Aucun changement UX, RAG, auth, ai_service.
- `compute_retention_metrics` : zéro import projet — logique pure, déterministe, explicable.
- Données non stockées : calculées à la volée, pas de colonne supplémentaire en DB.
- Fenêtres non chevauchantes — un même gap ne peut appartenir qu'à une seule fenêtre.

**Phase 14 :** TASK-048 + TASK-049 + TASK-050 + TASK-051 — complètes. Phase 14 terminée.

---

## 2026-05-17 — TASK-050 : Plan de session adaptatif — get_next_session_plan

**Objectif :** liste ordonnée de chunks à réviser avec durée estimée et objectif pédagogique par item.

**adaptive_engine.py — 4 ajouts :**
- `_OBJECTIVES` (dict 12 entrées, 3 mastery × 4 trends) — texte de l'objectif pédagogique par combinaison.
- `_DURATION_BY_MASTERY` — durée estimée : Fragile=8min, En consolidation=6min, Maîtrisé=3min.
- `_compute_priority_score(row)` — score de tri interne (4 composantes : urgence révision, fragilité, tendance, faible historique). Gestion NaN sûre via `pd.isna`.
- `build_session_plan(chunks_df, max_items=5)` — fonction pure recevant un DataFrame enrichi par `classify_mastery()`. Retourne `list[dict]` triée par `priority_score` décroissant, capped à `max_items`.

**database.py — 1 ajout :**
- `get_next_session_plan(user_id, max_items=5)` — wrapper DB minimal : `get_chunk_stats → classify_mastery → build_session_plan`. 4 lignes actives.

**Corrections Conseil (post-implémentation) :**
- `profile` supprimé de `build_session_plan` (dead parameter — YAGNI) et de `get_next_session_plan`.
- 2 tests d'invariants métier ajoutés : `question_piege` absent du biais Fragile, `reformulation` absent du biais Maîtrisé.

**test_regression.py — 21 nouveaux tests :**
- `TestBuildSessionPlanPure` (18 tests) : cas limites (None/empty/colonnes manquantes), structure des items, durée, max_items, tri, invariants biais, NaN pandas, annotations objectif.
- `TestGetNextSessionPlanDb` (3 tests) : sans historique → [], structure avec historique, max_items DB.

**Résultat :** 159 tests + 4 subtests. 0 régression. py_compile 3/3 OK.

**Invariants préservés :**
- Aucun changement UX, RAG, auth, ai_service.
- `build_session_plan` : zéro import projet — testable indépendamment.
- `get_next_session_plan` : wrapper pur, pas de logique de scoring dans database.py.

**Phase 14 restante :** TASK-051 — métriques de rétention J+1/J+7/J+30.

---

## 2026-05-17 — TASK-049 : Enrichissement du profil adaptatif utilisateur

**Objectif :** ajouter trois métriques pures et robustes au moteur adaptatif : momentum, learning_velocity, consistency_score.

**adaptive_engine.py — 3 nouvelles fonctions pures :**
- `compute_momentum(rows, window_days=7)` — avg_score(J-7→J) − avg_score(J-14→J-7). Mesure l'accélération récente. Borné [-1.0, 1.0]. Fallback 0.0 si fenêtre précédente vide.
- `compute_learning_velocity(rows)` — moyenne des deltas avg_score entre jours d'activité consécutifs. Mesure la régularité session à session. Borné [-1.0, 1.0]. Fallback 0.0 si < 2 sessions.
- `compute_consistency_score(rows, window_days=30)` — jours actifs / 30 sur les 30 derniers jours. Mesure la constance de la pratique. Borné [0.0, 1.0]. Fallback 0.0 si fenêtre vide.
- Les trois fonctions acceptent `list[tuple[created_at_str, score]]` — sans dépendance projet, pleinement testables.

**database.py — migration douce + intégration :**
- Import des 3 nouvelles fonctions depuis `adaptive_engine`.
- `init_db()` : 3 migrations `ALTER TABLE user_learning_profile ADD COLUMN ... REAL DEFAULT 0` avec try/except ignorant les colonnes déjà existantes.
- `compute_and_save_learning_profile()` : SELECT étendu à `created_at`, calcul des 3 métriques, ajout dans le dict profil et dans l'INSERT OR REPLACE (11 paramètres → 12).
- `get_learning_profile()` : inchangée — `SELECT *` + `sqlite3.Row` retourne les nouvelles colonnes automatiquement.

**test_regression.py — 20 nouveaux tests :**
- `TestAdaptiveMetricsPure` (15 tests) : momentum (vide, fenêtre unique, positif, négatif, borné), velocity (vide, 1 jour, 2 jours positif/négatif, borné), consistency (vide, 30/30 jours, 15/30, borné, vieilles données ignorées).
- `TestProfileWithNewMetrics` (5 tests) : colonnes DB présentes, 0.0 sans historique, clés dans le dict, persistance via get_learning_profile, consistency > 0 après une tentative.

**Résultat :** 137 tests + 4 subtests. 0 régression. py_compile 3/3 OK.

**Invariants préservés :**
- Aucun changement UX, aucun changement RAG, aucun changement auth.
- `get_learning_profile()` non modifiée — rétrocompatibilité totale.
- Migration douce : base existante mise à jour sans reset ni perte de données.
- Fallback 0.0 systématique si données insuffisantes.

**Phase 14 restante :** TASK-050 (get_next_session_plan) et TASK-051 (métriques rétention J+1/J+7/J+30).

---

## 2026-05-16 — Phase 15A : Consolidation technique minimale (TASK-050A.1–4)

**Objectif :** corriger les mines techniques identifiées par le Conseil lors du checkpoint architectural Phase 14 — zéro changement fonctionnel, zéro changement UX.

**TASK-050A.1 — rag_service DB_PATH (Commit `da36fb9`) :**
- `from database import DB_PATH` → `import database` + `database.DB_PATH`
- Même pattern qu'`auth_service.py`. Les futurs tests avec DB temporaire ne toucheront plus silencieusement `database.db`. Mine désarmée avant TASK-049/050/051.

**TASK-050A.2 — Cosine similarity numpy (Commit `da36fb9`) :**
- `_cosine_similarity` réécrite avec `numpy` (float32). Signature et comportement identiques.
- `numpy` déjà présent via pandas — aucune nouvelle dépendance.
- Gain mesuré : ~100x sur les comparaisons vectorielles (1536 éléments). Impact visible dès 50+ chunks.

**TASK-050A.3 — Tripwires REVIEW_INTERVALS (Commit `2074a76`) :**
- `TestReviewIntervalsCoherence` (9 tests + 4 subtests) ajouté dans `test_regression.py`.
- Vérifie que `REVIEW_INTERVALS` et `_adaptive_interval` restent synchronisés avec les valeurs hardcodées dans `database.get_revision_suggestion` (SQL `'+1 day'`/`'+3 days'`) et `ui_helpers.explain_interval_decision` (dict `_special`/`_default`).
- Messages d'erreur pointent explicitement les deux lignes à mettre à jour si les constantes changent.
- Décision Conseil : ne pas réécrire le SQL en Python (risque O(N)), sécuriser par tests à la place.

**TASK-050A.2 tests — Cosine similarity (Commit `2074a76`) :**
- `TestCosineSimilarity` (4 tests) : vecteurs identiques ≈ 1.0, orthogonaux ≈ 0.0, vecteur nul (a et b) = 0.0.

**TASK-050A.4 — Tests rôles auth (Commit `423276d`) :**
- `test_register_admin_role` et `test_register_formateur_role` ajoutés dans `test_auth_service.py`.
- Valident le round-trip complet : `register_user` → `get_user_by_username` → `verify_password`, pour les rôles `admin` et `formateur`.
- Préparent proprement la future UI admin creation (Phase 15B).

**Résultat final :** 104 tests (+ 4 subtests), 0 régression. 3 fichiers modifiés.

**Invariants préservés :** aucun changement fonctionnel, aucun changement UX, aucun changement `adaptive_engine`, aucun changement auth flow.

**Phase 15A complète.**

---

## 2026-05-16 — Phase 15B : Gouvernance admin minimale (TASK-050B, Commits A–D)

**Objectif :** débloquer la création du premier administrateur et la promotion des utilisateurs — bloqueur opérationnel identifié lors du checkpoint Phase 14.

**Commit A — Backend database + auth_service (Commit `3d5dfaa`) :**
- `database.py` : ajout de `count_admins()`, `get_all_users()` (tri stable admin→formateur→apprenant, puis username ASC via CASE WHEN), `set_user_role()` (UPDATE ciblé, jamais DELETE+INSERT — IDs stables préservés).
- `auth_service.py` : ajout de `_VALID_PROMOTIONS` (frozenset, transitions uniquement montantes), `promote_user()` (re-vérifie rôle admin depuis DB, auto-promotion interdite, transition validée avant UPDATE).
- Sécurité : re-vérification DB (pas session_state) protège contre élévation de privilèges côté client.

**Commit B — Tests (Commit `f7af50f`) :**
- `test_regression.py` : `TestDatabaseAdminFunctions` (6 tests) — count_admins, get_all_users (absence hash, tri admin→formateur→apprenant→username).
- `test_auth_service.py` : 7 tests promote_user — 3 succès (apprenant→formateur, →admin ; formateur→admin), 4 ValueError (auto-promotion, non-admin, transition invalide, cible inconnue).
- Total : 117 tests + 4 subtests. 0 régression.

**Commit C — UI (Commit `d22ebf4`) :**
- `app.py` : `_render_admin_bootstrap()` helper — formulaire création premier admin (6 chars min, confirmation). Détecté via `count_admins()==0`, tab "Premier administrateur" affiché dans les deux flux (demo_mode et login normal) ; disparaît automatiquement dès qu'un admin existe.
- `tabs/tab_trainer.py` : `_render_admin_section()` helper — liste tous les utilisateurs avec selectbox de promotion et bouton "Promouvoir". Visible uniquement si `role == 'admin'`. Appelée avant le return anticipé (admin avec <2 tentatives) et en fin de `render()`.
- 108 insertions, 4 suppressions. 2 fichiers. 0 régression.

**Invariants préservés :**
- Aucun changement `adaptive_engine.py`, `ai_service.py`, `rag_service.py`.
- Aucun changement UX hors périmètre auth/admin.
- `set_user_role` : UPDATE ciblé — IDs stables garantis.
- Pas de suppression utilisateur, pas de rétrogradation, pas de gestion permissions granulaires.

**Résultat final :** Bootstrap admin opérationnel. Promotion admin→formateur et admin→admin disponibles dans l'onglet Formateur. 117 tests passants.

**Phase 15B complète.**

---

## 2026-05-16 — TASK-048 Phase 14 : Extraction adaptive_engine.py (Commits A–C)

**Objectif :** Isoler toute la logique pédagogique pure dans `adaptive_engine.py`, sans import projet, pour éliminer les risques de circular dependency et centraliser les constantes et algorithmes adaptatifs.

**Commit A — Constantes et imports :**
- `adaptive_engine.py` créé avec : `REVIEW_INTERVALS`, `_PEDAGOGY_GROUPS`, `QUESTION_TYPES`, `_MASTERY_BIAS`.
- `database.py` et `ai_service.py` : suppression des définitions locales, import depuis `adaptive_engine`.
- 89/89 tests. Commit `bb51be5`.

**Commit B — `_adaptive_interval` + `classify_mastery` depuis database.py :**
- Deux fonctions déplacées verbatim vers `adaptive_engine.py`.
- Re-export depuis `database.py` via `from adaptive_engine import ...` (backward compat tests inclus).
- Leçon : même les fonctions privées (`_adaptive_interval`) doivent être re-exportées si les tests les importent directement.
- 89/89 tests. Commit `8f4ee98`.

**Commit C — `_choose_question_type` + `explain_type_choice` depuis ai_service.py :**
- Deux fonctions déplacées verbatim vers `adaptive_engine.py`.
- `import random` ajouté à `adaptive_engine.py`.
- Dans `explain_type_choice` : `_PROFILE_TYPES` remplacé par `_PEDAGOGY_GROUPS` (alias local inutile dans le nouveau contexte).
- Re-export depuis `ai_service.py` via import élargi. `_PROFILE_TYPES` alias conservé dans `ai_service` pour `generate_question`.
- `adaptive_engine.py` : zéro import projet maintenu — invariant respecté.
- 89/89 tests. Commit `edf88dd`.

**Résultat final :**
`adaptive_engine.py` contient : 4 constantes + `_adaptive_interval` + `classify_mastery` + `_choose_question_type` + `explain_type_choice`. Aucun import projet. `database.py` et `ai_service.py` importent depuis lui, jamais l'inverse.

**Phase 14 complète.**

---

## 2026-05-16 — Phase 13 : Décision de report — SQLAlchemy / PostgreSQL

**Décision :** Phase 13 (TASK-045/046/047 — SQLAlchemy Core + PostgreSQL + pgvector) reportée jusqu'à ce que PostgreSQL soit réellement nécessaire.

**Avis du Conseil :**
- 25+ sites de requêtes à convertir dans database.py (fichier moteur critique) → risque élevé pour zéro bénéfice fonctionnel immédiat.
- `pd.read_sql_query` + SQLAlchemy text() : comportement pandas version-dépendant.
- `engine.begin()` vs `engine.connect()` : risque de perte de données silencieuse sur écriture.
- `ALTER TABLE` try/except : exception change de classe → init_db non idempotent si mal converti.
- Pooling SQLAlchemy sur SQLite : risque `database is locked` sous Streamlit multi-thread.
- Tests actuels insuffisants pour valider la migration (BLOB roundtrip, transactions, rows mapping).

**Stratégie retenue :** combiner TASK-045 + TASK-046 en une seule migration propre lorsque `DATABASE_URL` PostgreSQL sera configurée — évite deux refactors successifs du fichier le plus critique.

**Philosophie CLAUDE.md :** "clarity over sophistication, robustness over complexity."

**Prochaine phase disponible :** Phase 14 — `adaptive_engine.py`.

---

## 2026-05-16 — TASK-044 : Rôles actifs — onglets conditionnels (Phase 12)

**Milestone :** Phase 12 complète — authentification + rôles opérationnels.

**Actions :**
- `app.py` : bloc `st.tabs` fixe remplacé par bloc conditionnel sur `_show_privileged`.
- `apprenant` (authentifié, role = "apprenant") : 4 onglets — Entraînement, Historique, Dashboard, Moteur IA.
- `formateur` / `admin` : 6 onglets — + Documents, + Formateur.
- Demo mode (non authentifié, `APP_PASSWORD` seul, `demo_active`) : 6 onglets — comportement inchangé.
- `role = None` (session non initialisée) → `not authenticated` = True → tous les onglets → rétro-compat garantie.

**Invariants préservés :**
- Tabs inchangés — aucune modification dans tabs/*.
- Moteur pédagogique intact.
- 89/89 tests passés, py_compile OK.

**Commit :** `31cebaa` — feat: TASK-044 rôles actifs — tabs conditionnels selon role session_state

**Phase 12 complète.** Critères de sortie atteints :
- Comptes utilisateurs avec mot de passe haché (bcrypt) ✅
- user_id non saisissable librement (UUID) ✅
- Mode démo préservé ✅
- 12+ tests unitaires auth_service ✅

**Prochaine phase :** Phase 13 — Base de données scalable (SQLAlchemy Core + PostgreSQL).

---

## 2026-05-16 — TASK-043 fix : app_gated + bootstrap mode démo

**Problème détecté :** APP_PASSWORD posait `authenticated = True`, court-circuitant le gate users. Table users vide → `_demo_mode = True` → double bypass, formulaire TASK-043 jamais affiché.

**Corrections :**
- `app_gated` : clé dédiée au gate APP_PASSWORD. `authenticated` réservé au login users table.
- Bootstrap : bloc auth affiché même en mode démo — onglet "Créer un compte" + onglet "Mode démo" (bouton "Continuer en mode démo" → `demo_active = True`).
- Logout réinitialise aussi `demo_active`.

**Validé en prod :** APP_PASSWORD → formulaire TASK-043 → inscription → sidebar username/logout → déconnexion → retour login. ✅

**Commit :** `c57d6ae` — fix: TASK-043 séparer app_gated/authenticated + bootstrap mode démo

---

## 2026-05-16 — TASK-043 : Login/Register users table dans app.py (Phase 12)

**Milestone :** Phase 12 — authentification réelle opérationnelle via table users.

**Actions :**
- `app.py` uniquement modifié.
- Bloc `APP_PASSWORD` (TASK-036) restauré en premier gate — protège l'app si env var définie, `authenticated = True` après validation.
- Nouveau bloc users-based auth : `_count_users() == 0` → mode démo (accès direct) ; sinon formulaire login/register à deux onglets.
- Login : `verify_password(username, password)` → `session_state["user_id"] = UUID`, `["username"]`, `["role"]`.
- Register : `register_user(username, password)` avec validations locales (username non vide, password ≥ 6 chars, confirm == password).
- Logout : bouton sidebar → `user_id = "default"`, `authenticated = False`, `username/role = None`.
- Sidebar : affiche nom + rôle + bouton logout si connecté via users table ; affiche champ "Identifiant" en mode démo.
- `check_app_password` ré-importé depuis `ui_helpers` (retiré par erreur en première version).

**Invariants préservés :**
- Tabs inchangés — lisent uniquement `session_state["user_id"]`.
- Moteur pédagogique et database.py non modifiés.
- Anciens user_id ("default", "alice"…) compatibles.
- 89/89 tests passés, py_compile OK.

**Coexistence des deux gates :**
- `APP_PASSWORD` set + users vide → password gate (mode démo protégé).
- `APP_PASSWORD` absent + users existants → login/register users table.
- `APP_PASSWORD` set + users existants → password gate prime, users auth bypassé.

**Commit :** `0e2528a` — feat: TASK-043 login/register users table + restauration gate APP_PASSWORD

**Prochaine étape :** TASK-044 — activation des rôles (formateur/admin/apprenant) sur les tabs.

---

## 2026-05-16 — TASK-042 : auth_service.py — fonctions d'authentification (Phase 12)

**Milestone :** Phase 12 — couche auth pure et testable disponible.

**Actions :**
- `auth_service.py` créé : 3 fonctions pures, 0 dépendance Streamlit.
  - `register_user(username, password, role)` → UUID str. Hash bcrypt (gensalt), INSERT avec gestion IntegrityError → ValueError.
  - `get_user_by_username(username)` → dict complet ou None.
  - `verify_password(username, password)` → `{user_id, username, role}` sans exposer le hash, ou None.
- Stratégie NULL hash : `verify_password` retourne None — aucun accès sans mot de passe.
- `import database` (non `from database import DB_PATH`) — permet au patch DB des tests d'être visible.
- `test_auth_service.py` : 12 tests, pattern `_DbTestCase` aligné sur `test_regression.py`.

**Invariants préservés :**
- Aucune modification UX, aucun changement dans app.py ou les tabs.
- Flow `APP_PASSWORD` existant intact.
- 89/89 tests passés, py_compile OK.

**Commit :** `be510d9` — feat: TASK-042 auth_service.py — register/verify/lookup avec bcrypt

**Prochaine étape :** TASK-043 — remplacer le bloc login dans app.py par register/login réel (users table), demo mode si aucun user en DB.

---

## 2026-05-16 — TASK-041 : Table users — migration douce SQLite (Phase 12)

**Milestone :** Phase 12 — socle authentification : table `users` ajoutée sans casser l'existant.

**Actions :**
- `database.py` / `init_db()` : ajout `CREATE TABLE IF NOT EXISTS users` (user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT, role TEXT DEFAULT 'apprenant', created_at TIMESTAMP).
- Migration idempotente : `IF NOT EXISTS` + bloc `ALTER TABLE ... ADD COLUMN` wrappé en try/except — aucun impact sur une DB déjà initialisée.
- `user_id TEXT PRIMARY KEY` : conserve la compatibilité avec `attempts.user_id` et `user_learning_profile.user_id` (valeurs TEXT existantes : "default", "alice", etc.).
- Pas de FK `attempts → users` intentionnellement : évite de bloquer les inserts legacy.

**Invariants préservés :**
- Aucune modification UX, aucune modification des tabs.
- Fallback mode intact (table ignorée si non utilisée).
- 77/77 tests passés, py_compile OK.

**Commit :** `4464fcf` — feat: TASK-041 add users table to init_db (Phase 12)

**Prochaine étape :** TASK-042 — `auth_service.py` : register_user(), verify_password(), get_user_by_username() avec bcrypt.

---

## 2026-05-16 — TASK-040 : Modularisation app.py → tabs/ (Phase 11)

**Milestone :** Phase 11 — critère de sortie atteint : `app.py` < 150 lignes, architecture documentée dans ROADMAP.

**Actions :**
- `app.py` : 1433 lignes → 96 lignes. Routeur pur : imports, init, auth, CSS/header, session state, sidebar, dispatch des 6 onglets.
- `tabs/styles.py` : constantes `APP_CSS` et `APP_HEADER` (strings purs, 0 import Streamlit) — préserve l'invariant de `ui_helpers.py` (aucune dépendance Streamlit).
- `tabs/tab_training.py` (323 lignes) : onglet Entraînement — génération, réponse, correction, explainability, suggestion de révision.
- `tabs/tab_history.py` (79 lignes) : onglet Historique — liste des tentatives, export CSV.
- `tabs/tab_dashboard.py` (428 lignes) : onglet Dashboard — KPIs, cartes section, graphiques, profil, rapport.
- `tabs/tab_documents.py` (117 lignes) : onglet Documents — import, bibliothèque, reindexation.
- `tabs/tab_engine.py` (117 lignes) : onglet Moteur IA — pipeline 7 étapes, 6 types de questions.
- `tabs/tab_trainer.py` (212 lignes) : onglet Formateur — KPIs superviseur, synthèse narrative, couverture corpus.

**Pattern Streamlit :** chaque `render()` est appelé à l'intérieur d'un `with tab_xxx:` — le DeltaGenerator context est propagé automatiquement. Aucun argument `tab` nécessaire.

**Invariants préservés :**
- Comportement UI identique. Session state inchangé. Fallback mode intact.
- `_make_use_callback` définie dans `tab_training.py` et `tab_documents.py` (duplication intentionnelle — 8 lignes, pas d'abstraction prématurée).
- py_compile 8/8 OK. 77/77 tests OK. Commit `05b299d`.

**Phase 11 — COMPLÈTE.** TASK-038 ✅ TASK-039 ✅ TASK-040 ✅

**Prochaine étape :** Phase 12 — authentification réelle (TASK-041 : table `users`).

---

## 2026-05-16 — Audit P1/P2 — Corrections ciblées post-inspection Council

**Contexte :** Inspection complète du projet par le Global Code Council avant TASK-040. Trois anomalies corrigées.

**Corrections :**
- `ui_helpers.py` : `_FILE_MAX_MB` 20 → 10. La limite UI était incohérente avec l'enforcement réel de `document_service.py` (10 Mo). Un fichier de 15 Mo passait la validation UI mais était rejeté en backend — bug UX silencieux.
- `seed_demo_attempts.py` : suppression de `DB_PATH = Path("database.db")` local hardcodé. Remplacement par `from database import DB_PATH`. Si `DB_PATH` est surchargé via env var, le seed utilisait désormais le même chemin que l'application.
- `database.py` `save_attempt` : 6 paramètres `float/str/int = None` → `Optional[float/str/int] = None`. Cohérence complète avec la politique TASK-038.

**Invariants préservés :**
- Aucun changement de comportement métier. Aucune migration SQLite.
- py_compile 4/4 OK. 77/77 tests OK. Commit `b82fb4c`.

**Prochaine étape :** TASK-040 — modularisation `app.py` → `tabs/`.

---

## 2026-05-16 — TASK-039 : Extraction rag_service.py (Phase 11)

**Milestone :** Phase 11 — séparation retrieval vectoriel / persistance SQLite.

**Actions :**
- Création de `rag_service.py` : contient `_cosine_similarity`, `_blob_to_vector`, `search_similar_chunks`. Importe uniquement `DB_PATH` depuis `database.py`. Aucun import circulaire.
- `database.py` : suppression de `import struct` et des 3 fonctions RAG (59 lignes retirées).
- `ai_service.py` : `search_similar_chunks` déplacé de l'import `database` vers `from rag_service import search_similar_chunks`.

**Invariants préservés :**
- Comportement RAG identique — même logique cosinus, même seuil `char_count >= 150`, même tri décroissant.
- Aucune modification de signature publique. Fallback mode inchangé.
- py_compile 5/5 OK. 77/77 tests OK. Commit `94083a5`.

**Prochaine étape :** TASK-040 — modularisation `app.py` → `tabs/`.

---

## 2026-05-16 — TASK-038 : Dettes résiduelles soldées (Phase 11)

**Milestone :** Phase 11 — socle architectural sain, première tâche complète.

**Actions :**
- `ai_service.py` : `from typing import Optional` ajouté ; toutes les annotations `X | None` → `Optional[X]` (7 occurrences : `_client`, `_choose_question_type`, `explain_type_choice`, `generate_question` ×2) ; `_PROFILE_TYPES` supprimé — remplacé par `from database import _PEDAGOGY_GROUPS as _PROFILE_TYPES`.
- `ui_helpers.py` : `str | None` et `dict | None` → `Optional[str]` / `Optional[dict]` dans `explain_question_decision` et `explain_profile_detection` (4 occurrences).
- `database.py` : `dict | None` → `Optional[dict]` dans `get_revision_suggestion`, `get_document_by_id`, `get_learning_profile` (3 occurrences).
- `seed_demo_attempts.py` : `from typing import Optional` ajouté ; `int | None` → `Optional[int]` dans `_get_chunk_id`.
- `config.py` : docstring mis à jour — statut `DOCUMENTATION ONLY — CE FICHIER N'EST PAS IMPORTÉ` explicite, référence consolidation Phase 13 (SQLAlchemy).

**Invariants préservés :**
- Aucun changement logique. Aucune migration SQLite. Aucune modification de signature visible.
- `_PROFILE_TYPES` reste disponible dans `ai_service.py` — même contenu, source unique dans `database.py`.
- py_compile 5/5 OK. 77/77 tests OK. Commit `7f2b525`.

**Prochaine étape :** TASK-039 — extraire `rag_service.py` depuis `database.py`.

---

## 2026-05-16 — Roadmap industrielle Phase 11-17

**Milestone :** Ouverture de la trajectoire vers un produit SaaS B2B complet.

**Actions :**
- `ROADMAP.md` : ajout des Phases 11 à 17 et de la section "Vision produit cible".
- Historique Phase 0-10 préservé intégralement. Phase 10 marquée complète (commit `8b9354a`).
- TASK-038 à TASK-063 définis avec objectifs, critères de sortie, dépendances et risques.

**Phases ajoutées :**
- Phase 11 — Socle architectural sain (TASK-038/039/040)
- Phase 12 — Authentification réelle (TASK-041/042/043/044)
- Phase 13 — Base de données scalable / PostgreSQL (TASK-045/046/047)
- Phase 14 — Moteur pédagogique complet / adaptive_engine.py (TASK-048/049/050/051)
- Phase 15 — Multi-documents et corpus (TASK-052/053/054/055)
- Phase 16 — UX professionnelle finale (TASK-056/057/058/059)
- Phase 17 — Production industrielle / CI/CD (TASK-060/061/062/063)

**Vision produit cible :** SaaS pédagogique B2B — auth réelle multi-rôles,
PostgreSQL + pgvector, moteur adaptatif complet, corpus multi-documents,
dashboard formateur + admin, monitoring, déploiement Docker automatisé.

**Philosophie :** étapes petites et validables, stabilité prioritaire, aucun refactor massif,
tests après chaque tâche, backup démo stable préservé. Commit `1d0c46f`.

**Prochaine étape :** TASK-038 — solder les dettes résiduelles (Phase 11).

---

## 2026-05-16 — Backup demo stable

**Milestone :** Point de sauvegarde définitif avant ouverture Phase 11.

**Actions :**
- Création du dossier `BACKUP_DEMO_STABLE_ai-v2_2026-05-16_17-24` sur le Bureau.
- Copie complète du projet (51 fichiers, 0,5 Mo) — exclusions : `.venv`, `__pycache__`, `.pytest_cache`, `.git`, `node_modules`.
- `database.db` incluse (base SQLite de démonstration avec historique des tentatives).
- `LISEZ_MOI_LANCEMENT_DEMO.md` créé : installation, configuration `.env`, commande Streamlit, description de l'architecture, option Docker.

**État du snapshot :**
- Phase 10 complète — commit `8b9354a`.
- 77/77 tests OK.
- Moteur adaptatif, pipeline RAG, répétition espacée, profil pédagogique, dashboard formateur, auth, CI, Docker — tous opérationnels.

**Usage :** relancer depuis ce backup à tout moment via `pip install -r requirements.txt` + `streamlit run app.py`, indépendamment des évolutions du projet principal.

**Archive ZIP :** `BACKUP_DEMO_STABLE_ai-v2_2026-05-16_17-24.zip` — 0,15 Mo — Bureau (inclut `LANCER_ADDISCO_OPS.bat`).

---

## 2026-05-16 — Fix LANCER_ADDISCO_OPS.bat — syntaxe batch pure

**Cause :** La première version du lanceur utilisait `chcp 65001` et des accents dans les `echo`, provoquant des risques d'affichage corrompu sur certaines configurations Windows CMD.

**Correction :**
- Remplacement complet du fichier par une version batch classique sans accents ni caractères spéciaux.
- `python -m streamlit` à la place de `streamlit` direct (plus robuste selon l'environnement).
- Suppression de `chcp 65001` et `--server.headless false`.
- Backup et ZIP régénérés avec le lanceur corrigé.

**Invariants :** aucun fichier Python modifié — py_compile non requis. Commit `fe98d59`.

---

## 2026-05-16 — Hotfix : annotation str | None → Optional[str] (database.py, document_service.py)

**Cause :** Le hotfix TASK-035 avait corrigé `ui_helpers.py` mais laissé deux occurrences résiduelles de `str | None` (PEP 604) dans les modules engine. Même risque d'incompatibilité Streamlit 1.57 + Python 3.14 (PEP 649) que le bug initial.

**Correction :**
- `database.py` : `from typing import Optional` ajouté ; `str | None` → `Optional[str]` dans `_normalize_topic()` et `get_chunk_mastery()`.
- `document_service.py` : `from typing import Optional` ajouté ; `str | None` → `Optional[str]` dans `_detect_section_title()` et la variable locale `current_section`.

**Invariants :** zéro changement logique — py_compile 2/2 OK, 77/77 tests OK. Commit `297fa56`.

---

## 2026-05-15 — TASK-036 : Authentification légère (Phase 10, clôture)

**Milestone :** Phase 10 — dernier item manquant (authentification).

**Actions :**
- `ui_helpers.py` : `import hmac` + `check_app_password(entered, expected) -> bool` via `hmac.compare_digest` (anti-timing attack, testable sans Streamlit).
- `app.py` : bloc login conditionnel après `st.set_page_config`. Si `APP_PASSWORD` absent ou vide → accès libre (mode démo inchangé). Si défini → écran de login `st.text_input(type="password")` + `st.stop()` jusqu'à validation. Session state `authenticated` persist entre reruns.
- `.env.example` : variable `APP_PASSWORD=` documentée (optionnelle).
- `test_regression.py` : `test_check_app_password` — 4 cas (match, wrong, vide vs secret, vide vs vide).

**Invariants préservés :**
- Sans `APP_PASSWORD` défini : comportement 100 % identique à avant.
- Aucune modification de `database.py`, `ai_service.py`, `document_service.py`.
- 77/77 tests OK, py_compile 3/3 OK. Commit `26ddb8f`.

**Phase 10 — COMPLÈTE.** Tous les items ROADMAP Phase 10 livrés : Docker, logs, exports, monitoring, dashboard formateur, CI, sécurité entrées, multi-utilisateur, authentification.

**Prochaine étape suggérée :** bilan Phase 10 + ouverture Phase 11 (multi-documents, profil utilisateur persistant, ou déploiement cloud).

---

## 2026-05-15 — Hotfix TASK-035 : annotation str | None → Optional[str]

**Cause :** `str | None` (PEP 604) provoque une incompatibilité entre Streamlit 1.57 et le système d'annotations lazy de Python 3.14 (PEP 649). Le module `ui_helpers` se chargeait partiellement, rendant les fonctions annotées invisibles à l'import Streamlit — alors que `python -c` fonctionnait (chemin d'import différent).

**Correction :**
- `ui_helpers.py` : `from typing import Optional` ajouté ; `str | None` → `Optional[str]` dans `validate_doc_title` et `validate_file_size`.
- `__pycache__` supprimé avant revalidation.

**Invariants :** zéro changement logique — 76/76 tests OK, py_compile OK. Commit `9c8ffce`.

---

## 2026-05-15 — TASK-035 : Validation des entrées utilisateur (Sécurité, Phase 10)

**Milestone :** Phase 10 — sécurité.

**Actions :**
- `ui_helpers.py` : +3 fonctions pures (`sanitize_user_id`, `validate_doc_title`, `validate_file_size`) + constantes (`_USER_ID_MAX_LEN=50`, `_DOC_TITLE_MAX_LEN=200`, `_FILE_MAX_MB=20`).
- `app.py` :
  - Guard 1 — `user_id` : `sanitize_user_id()` appliqué avant le rendu du widget (strip + max 50 car. + fallback `"default"`).
  - Guard 2 — titre document : `validate_doc_title()` remplace le `if not doc_title.strip()` existant (ajoute limite 200 caractères).
  - Guard 3 — taille fichier : `validate_file_size()` bloque les fichiers > 20 Mo avant tout appel à `ingest_document()`.
- `test_regression.py` : +3 tests (`test_sanitize_user_id`, `test_validate_doc_title`, `test_validate_file_size`) dans `TestUiHelpers`.

**Invariants préservés :**
- Aucune modification de `database.py`, `ai_service.py`, `document_service.py`
- Comportement inchangé pour toute entrée valide
- Logique de validation 100 % pure (testable sans Streamlit)
- 76/76 tests OK, py_compile 3/3 OK

**Prochaine étape suggérée :** authentification simple (Phase 10) ou clôture Phase 10.

---

## 2026-05-15 — TASK-034 : CI GitHub Actions (Phase 10)

**Milestone :** Phase 10 — tests automatisés.

**Actions :**
- `.github/workflows/ci.yml` (nouveau) : workflow CI déclenché sur `push` et `pull_request` vers `main`. 5 étapes : Checkout (v4), Setup Python 3.11 (v5, cache pip), Install dependencies, Compile Python (boucle bash + guard `if [ -f ]` sur 5 fichiers critiques), Run tests (`python -m unittest test_regression.py -v`).
- `README.md` : +section "CI GitHub Actions" (rôle, pipeline, objectif).
- Aucun fichier Python modifié.

**Invariants préservés :**
- Aucune modification de logique métier, UI, engine
- Aucun secret GitHub requis (tests SQLite en mémoire, pas d'appel OpenAI)
- Rollback trivial : supprimer `.github/workflows/ci.yml`
- YAML sans tabulation — indentation espaces uniquement
- py_compile 5/5 OK, 73/73 tests OK

**Prochaine étape suggérée :** validation entrées utilisateur (sécurité, Phase 10) ou authentification simple.

---

## 2026-05-15 — TASK-033 : Dashboard formateur (Phase 10)

**Milestone :** Phase 10 — dashboard formateur.

**Actions :**
- `app.py` : +onglet `"Formateur"` dans `st.tabs()`. Bloc `with tab_formateur:` (~120 lignes) en fin de fichier.
  - **F1 KPIs** : Tentatives, Score moyen (coloré), Jours d'étude, Temps moyen/réponse (ou Sections testées si < 3 mesures)
  - **F2 Synthèse narrative** : blocs HTML `#f8fafc` avec dot coloré (🟢/🟡/🔴/🔵) — régularité, niveau global, format le plus réussi, section prioritaire, temps de réponse. Langage non-technique.
  - **F3 Efficacité par type de question** : cartes `st.container(border=True)` + `st.progress()` par `pedagogy_type` — tri par score décroissant, sans graphique brut.
  - **F4 Couverture du corpus** : une carte par document avec barre de progression (sections testées / total) + compteurs fragile/consolidation/maîtrisé.
- Aucune modification de `database.py`, `ai_service.py`, `document_service.py`, `ui_helpers.py`.
- Données exclusivement issues des fonctions existantes : `get_attempts()`, `get_chunk_stats()`, `classify_mastery()`, `get_documents()`.

**Invariants préservés :**
- Dashboard apprenant existant (`tab_dashboard`) non modifié
- Aucun nouveau graphique Plotly — cartes avec `st.progress()` uniquement
- 73/73 tests OK, py_compile 1/1 OK

**Prochaine étape suggérée :** CI GitHub Actions ou authentification simple (Phase 10).

---

## 2026-05-15 — TASK-032 : Bannière de statut système (Phase 10)

**Milestone :** Phase 10 — monitoring léger.

**Actions :**
- `app.py` : +`import os`, +`DB_PATH` dans les imports database. Bloc sidebar étendu avec 3 indicateurs : `✅/❌ Base · opérationnelle/introuvable` (via `DB_PATH.exists()`), `✅/⚠️ OpenAI · connecté/mode fallback` (via `os.getenv("OPENAI_API_KEY")`), `📄 N document(s) chargé(s)` (via `len(get_documents())`).

**Invariants préservés :**
- Aucune modification engine (`database.py`, `ai_service.py`, `document_service.py`)
- Lecture seule — aucune écriture en base, aucun appel API
- 73/73 tests OK, py_compile 1/1 OK

**Prochaine étape suggérée :** CI GitHub Actions (`.github/workflows/ci.yml`) ou dashboard formateur (Phase 10).

---

## 2026-05-15 — TASK-031 : Export CSV de l'historique (Phase 10)

**Milestone :** Phase 10 — exports.

**Actions :**
- `app.py` : bouton `⬇ Exporter l'historique (.csv)` dans l'onglet Historique, entre les métriques et le divider. Colonnes exportées : `created_at`, `question`, `user_answer`, `expected_answer`, `score`, `error_type`, `topic`, `pedagogy_type`, `response_time_seconds`. Encoding `utf-8-sig` (BOM, compatible Excel). Conditionnel — masqué si historique vide.
- `test_regression.py` : +1 test `test_export_columns_present` dans `TestDatabaseAttempts` — vérifie que toutes les colonnes d'export sont présentes dans le DataFrame retourné par `get_attempts()`.

**Invariants préservés :**
- Aucune modification engine (`database.py`, `ai_service.py`, `document_service.py`)
- Lecture seule — aucune écriture en base
- 73/73 tests OK, py_compile 2/2 OK

**Prochaine étape suggérée :** health check / bannière de statut API+DB au démarrage (Phase 10).

---

## 2026-05-15 — TASK-030 : Logging structuré (Phase 10)

**Milestone :** Phase 10 — industrialisation continue.

**Actions :**
- `logger.py` (nouveau) : `setup_logging()` — RotatingFileHandler vers `logs/app.log` (5 MB, 3 backups), StreamHandler stdout, format `timestamp | LEVEL | module | message`
- `ai_service.py` : `+import logging`, `+logger = getLogger(__name__)`, WARNING sur fallback RAG, INFO sur type de question choisi (type/mastery/doc/user), WARNING sur JSON decode error dans `correct_answer()`
- `database.py` : `+import logging`, `+logger = getLogger(__name__)`, INFO sur `init_db()` (chemin DB), INFO sur `save_document()` (id/title/source)
- `app.py` : `+from logger import setup_logging`, `setup_logging()` appelé au démarrage du module
- `.dockerignore` : `+logs/` pour exclure les logs de l'image Docker
- `document_service.py` : déjà équipé d'un logging complet — non modifié

**Invariants préservés :**
- `document_service.py` non touché (logging déjà présent)
- Aucune modification de la logique métier ni des prompts
- Fallback mode inchangé
- 72/72 tests OK, py_compile 4/4 OK

**Prochaine étape suggérée :** health-check endpoint (Phase 10) ou nettoyage de la dette technique config.py.

---

## 2026-05-15 — TASK-029 : Dockerisation + Configuration externalisée (Phase 10)

**Milestone :** Phase 10 — début de l'industrialisation.

**Actions :**
- `Dockerfile` : image `python:3.11-slim`, WORKDIR `/app`, install dépendances, `mkdir -p /app/data`, port 8501, headless mode
- `docker-compose.yml` : service `app`, port `8501:8501`, `env_file .env`, `DB_PATH=/app/data/database.db`, volume nommé `synpz_data`
- `.dockerignore` : exclut `.env`, `database.db`, `__pycache__/`, `.git/`, `*.log`
- `config.py` : référence centralisée des 7 constantes principales (non importé — refactoring Phase 10+)
- `database.py` : +`import os`, `DB_PATH = Path(os.getenv("DB_PATH", "database.db"))` — fallback `database.db` inchangé
- `requirements.txt` : versions freezées (`openai==2.34.0`, `pandas==3.0.2`, `plotly==6.7.0`, `pypdf==6.11.0`, `python-dotenv==1.2.2`, `streamlit==1.57.0`)
- `README.md` : section "Déploiement Docker" avec `docker compose up --build` et gestion du volume

**Commandes Docker :**
```bash
cp .env.example .env   # remplir OPENAI_API_KEY
docker compose up --build
# → http://localhost:8501
docker compose down     # arrêt (volume préservé)
docker compose down -v  # arrêt + suppression base
```

**Invariants préservés :**
- Comportement local inchangé (`DB_PATH` fallback `database.db`)
- Aucune modification de signature dans les modules existants
- 72/72 tests OK · py_compile 2/2 OK

**Prochaine étape logique :** TASK-030 — Logging structuré (`logging` Python sur ingestion, génération, correction, embeddings)

---

## 2026-05-15 — TASK-028 : Memory & Decision Explainability Layer (Phase 9.5)

**Milestone :** Phase 9.5 — rendre les décisions du moteur pédagogique lisibles par l'utilisateur.

**Actions :**
- `ui_helpers.py` : +4 fonctions pures d'explainability (aucune dépendance Streamlit) :
  - `explain_question_decision(question_type, mastery_class, trend, review_status, dominant_error, profile_pedagogy) → list[tuple]` — signaux cognitifs de sélection de question (028a)
  - `explain_interval_decision(mastery_class, trend) → str` — miroir narratif de `_adaptive_interval()` (028b)
  - `explain_priority_decision(row) → list[str]` — raisonnement algorithmique de la priorité de révision (028c)
  - `explain_profile_detection(profile) → str` — explication du profil pédagogique dominant (028d)
- `ai_service.py` : +1 fonction additive `explain_type_choice(used_types, mastery_class, profile_pedagogy, chosen_type) → str` — miroir narratif de `_choose_question_type()`, aucune modification du moteur (028e)
- `app.py` : imports enrichis, 2 nouvelles clés session_state (`question_type_reason`, `question_profile_pedagogy`), expander "Pourquoi cette question ?" restructuré avec signaux HTML, priority card avec raisons algorithmiques et intervalle adaptatif, section cards avec caption intervalle, Zone 7 profil avec explication de détection
- `test_regression.py` : +28 tests — `TestExplainFunctions` (23 tests couvrant les 4 fonctions pures) et `TestExplainTypeChoice` (5 tests)

**Résultats :** 72/72 tests OK · py_compile 4/4 OK · `database.py` non modifié · 0 migration SQLite

**Invariants préservés :**
- Aucune modification de signature de `_choose_question_type()` ni `generate_question()`
- Fallback silencieux sur toutes les nouvelles fonctions (try/except non bloquant dans app.py)
- `explain_interval_decision()` est un miroir indépendant de `_adaptive_interval()` — synchronisation par convention, pas par import
- 44 tests existants non régressés

**Prochaine étape logique :** Phase 10 — Industrialisation (authentification, multi-user complet, Docker, tests automatisés CI)

---

## 2026-05-14 — TASK-027 : Intervalles de révision adaptatifs (Phase 9)

**Milestone :** Phase 9 — répétition espacée modulée par la tendance récente de l'apprenant.

**Actions :**
- `database.py` : ajout de `_adaptive_interval(mastery_class, trend) -> int` (fonction pure). Branchement dans `classify_mastery._next_review()` à la place de `REVIEW_INTERVALS.get(...)`.
- `test_regression.py` : +4 tests `TestClassifyMastery` (44/44 OK).

**Table des intervalles adaptatifs :**
| Classe | Trend | Intervalle |
|--------|-------|-----------|
| Fragile | Amélioration | 2j |
| Fragile | Stable/N/A/Dégradation | 1j |
| En consolidation | Amélioration | 5j |
| En consolidation | Dégradation | 2j |
| En consolidation | Stable/N/A | 3j |
| Maîtrisé | (tout) | 7j |

**Limitation connue :** `get_revision_suggestion()` ORDER BY conserve les intervalles base (1j/3j inline SQL). La modulation par trend s'applique uniquement à `next_review` dans le Dashboard. Gap acceptable.

**Invariants préservés :**
- `_adaptive_interval` retourne toujours un entier ≥ 1.
- Maîtrisé non modulé (déjà maîtrisé, pas de raison de réduire l'intervalle).
- py_compile 2/2 OK. 44/44 tests OK.

**Prochaine étape :**
- TASK-028 : à définir selon roadmap Phase 9 (affichage `next_review` adaptatif dans suggestion Entraînement) ou Phase 10.

---

## 2026-05-14 — TASK-026 : Isolation per-user dans get_chunk_question_history()

**Milestone :** Phase 8 — isolation multi-user complète sur toutes les fonctions engine.

**Actions :**
- `database.py` : `get_chunk_question_history(chunk_id, limit, user_id="default")` — ajout paramètre + `AND user_id = ?` dans la requête SQL.
- `ai_service.py` : appel mis à jour → `get_chunk_question_history(chunk_ids[0], limit=5, user_id=user_id)`.
- `test_regression.py` : +1 test `test_chunk_history_user_isolation` (40/40 OK). Paramètre `question` ajouté à `_add_attempt`.

**Limitation fermée :** TASK-019 avait volontairement laissé `get_chunk_question_history` sans filtre user_id. Le bloc "éviter les doublons" passé au LLM est maintenant strictement per-user.

**Invariants préservés :**
- Rétrocompatibilité totale : `user_id="default"` par défaut. Aucun appelant existant cassé.
- py_compile 3/3 OK. 40/40 tests OK.

**Prochaine étape :**
- TASK-027 : à définir selon roadmap Phase 9 (révision espacée) ou Phase 10 (production readiness).

---

## 2026-05-14 — TASK-025 : Mise à jour automatique du profil après chaque tentative

**Milestone :** Phase 8 — profil pédagogique toujours synchronisé avec l'historique réel.

**Actions :**
- `app.py` : appel `compute_and_save_learning_profile(st.session_state["user_id"])` dans le bloc post-correction, immédiatement après `save_attempt()`. Wrappé dans `try/except` silencieux — non-bloquant, fallback transparent.

**Invariants préservés :**
- Aucune régression moteur. py_compile OK. 39/39 tests OK.
- Si `compute_and_save_learning_profile` lève une exception → silencieux, correction affichée normalement.
- Le Dashboard peut afficher le profil sans recalcul manuel (bouton "Recalculer" reste disponible pour forcer).

**Prochaine étape :**
- TASK-026 : à définir selon roadmap Phase 8 / Phase 10.

---

## 2026-05-14 — TASK-024 : Profil pédagogique intégré dans generate_question()

**Milestone :** Phase 8 — adaptation cognitive per-user complète dans le moteur.

**Actions :**
- `ai_service.py` : import `get_learning_profile`. Ajout `_PROFILE_TYPES` (mapping `preferred_pedagogy` → types). Update `_choose_question_type(used_types, mastery_class, profile_types)` — biais profil comme niveau 3 (tie-breaker après rotation et mastery). Update `generate_question(source_text, document_id, user_id)` — passage `user_id` à `get_chunk_mastery` / `get_chunk_question_history`, lecture `get_learning_profile(user_id)`.
- `app.py` : `generate_question()` reçoit `user_id=st.session_state["user_id"]`.
- `test_regression.py` : +6 tests `TestChooseQuestionType` (39/39 OK).

**Hiérarchie des biais dans `_choose_question_type` :**
1. Rotation équitable (type le moins posé sur ce chunk)
2. Biais mastery (Fragile → reformulation/consequence ; Maîtrisé → piège/pratique)
3. Biais profil (preferred_pedagogy → types associés) — tie-breaker uniquement

**Invariants préservés :**
- `profile_types=None` → comportement identique à avant TASK-024.
- Profil absent (None) → pas d'erreur, fallback transparent.
- `correct_answer()` non modifié.
- py_compile 3/3 OK. 39/39 tests OK.

**Prochaine étape :**
- TASK-025 : Mise à jour automatique du profil après chaque tentative — appel `compute_and_save_learning_profile()` dans le flux post-correction de `app.py`.

---

## 2026-05-14 — TASK-023 : Tests de non-régression automatisés

**Milestone :** Phase 10 — robustesse. Premier filet de sécurité automatisé.

**Actions :**
- Création `test_regression.py` (stdlib `unittest`, aucun pytest requis).
- 33 tests en 6 classes, exécution en 0.24 s, zéro accès `database.db` ni API OpenAI.
- DB temporaire via `tempfile.NamedTemporaryFile` + monkey-patch `database.DB_PATH` → isolation totale.

**Invariants critiques couverts :**
- Isolation `user_id` (TASK-019) : user A ne voit pas les données de user B.
- Classification Fragile / En consolidation / Maîtrisé (seuils 0.6 / 0.8).
- Tendance Amélioration / Dégradation / Stable.
- Profil pédagogique : calcul, persistance, isolation utilisateur, `fragile_topics`.
- Ordre chronologique `get_score_evolution` (fix test : timestamps explicites en SQL).
- Bug `_ERROR_LABELS` résolu : clés mortes `"memory"` / `"attention"` absentes.
- Colonnes `next_review`, `days_until_review`, `review_status` présentes après `classify_mastery`.
- Limite 5 recommandations dans `_build_recommendations`.

**2 corrections de tests découvertes :**
- `_normalize_topic` applique `.capitalize()` → "Procédure A" → "Procédure a" (comportement correct, test corrigé).
- Inserts simultanés = timestamps identiques → ordre non déterministe corrigé par timestamps SQL explicites.

**Prochaine étape :**
- TASK-024 : Intégration du profil pédagogique dans la génération de questions — passer `user_id` à `generate_question()` pour enrichir le choix de type selon `preferred_pedagogy`.

---

## 2026-05-14 — TASK-022 : Extraction ui_helpers.py — réduction responsabilités app.py

**Milestone :** Architecture — séparation logique UI pure / orchestration Streamlit.

**Actions :**
- Création `ui_helpers.py` : `_ERROR_LABELS`, `_truncate_label`, `_kpi_card`, `_mastery_state`, `_build_recommendations`, `_build_report`. Aucune dépendance Streamlit.
- Suppression des 5 définitions locales dans `app.py` (−110 lignes de définitions).
- Import `from ui_helpers import (...)` en tête de `app.py`. Tous les call sites inchangés.
- **Fix bug** : `_ERROR_LABELS` dupliqué supprimé (keys `'memory'`/`'attention'`/etc. morts depuis commit TASK-019 — écrasés par la seconde définition à l'exécution).

**Résultats validation :**
- AST : 5/5 fonctions absentes de `app.py`. 0 définition locale de `_ERROR_LABELS`.
- Tests fonctionnels `ui_helpers.py` : 7/7 OK.
- py_compile : `ui_helpers.py` OK + `app.py` OK.

**Invariants préservés :**
- `database.py`, `ai_service.py`, `document_service.py` non modifiés.
- Comportement identique pour l'utilisateur final.

**Prochaine étape :**
- TASK-023 : Tests de non-régression automatisés sur `database.py` + `ui_helpers.py` (Phase 10 — robustesse).

---

## 2026-05-14 — TASK-021 : Profil d'apprentissage dans le Dashboard

**Milestone :** Exposition UI du profil pédagogique (TASK-020 rendu visible).

**Actions :**
- Import `compute_and_save_learning_profile` + `get_learning_profile` dans `app.py`.
- Ajout Zone 7 dans l'onglet Dashboard (insertion entre Zone 5 analyse et Zone 6 export) :
  - 4 KPI cards `_kpi_card()` : Analytique / Procédural / Narratif / Analogique — couleur selon score (vert ≥ 80 %, ambre ≥ 60 %, rouge < 60 %, gris = aucune donnée)
  - Ligne résumé : Style dominant + Score global
  - Caption notions fragiles (si existantes)
  - Bouton "Calculer le profil" (premier calcul) / "Recalculer le profil" + `st.rerun()`

**Décisions :**
- Insertion non intrusive : aucune modification des Zones 1-6 existantes.
- Profil calculé à la demande (pas automatique) : l'utilisateur contrôle la mise à jour.
- Données de seed demo : profil affiche Procédural dominant, Analytique 72 %, Analogique 37 %.

**Invariants préservés :**
- `database.py`, `ai_service.py`, `document_service.py` non modifiés.
- py_compile 2/2 OK. AST check imports OK.

**Prochaine étape :**
- TASK-022 : Réduction des responsabilités de `app.py` — extraction d'un helper `ui_helpers.py` (fonctions HTML/render) ou début de `adaptive_engine.py`.

---

## 2026-05-14 — TASK-020 : Table user_learning_profile — profil pédagogique utilisateur

**Milestone :** Fondation Phase 8 — profils pédagogiques par utilisateur.

**Actions :**
- Ajout `import json` dans `database.py`.
- Ajout `CREATE TABLE IF NOT EXISTS user_learning_profile` dans `init_db()` : colonnes `user_id` (PK), `preferred_pedagogy`, `logical_score`, `procedural_score`, `narrative_score`, `analogy_score`, `average_score`, `fragile_topics` (JSON), `updated_at`.
- Ajout `_PEDAGOGY_GROUPS` : mapping `question_type → groupe pédagogique` (logical/procedural/narrative/analogy).
- Ajout `get_learning_profile(user_id)` → `dict | None`.
- Ajout `compute_and_save_learning_profile(user_id)` → `dict` (INSERT OR REPLACE depuis `attempts`).

**Résultats validation (données seed demo) :**
- `preferred_pedagogy`: `'procedural'` (cas_pratique + consequence, avg 0.746)
- `logical_score`: 0.72 | `narrative_score`: 0.65 | `analogy_score`: 0.367
- `average_score`: 0.649 | `fragile_topics`: 3 notions < 60 %
- 4/4 assertions OK. py_compile 2/2 OK.

**Décisions :**
- Migration douce : `CREATE TABLE IF NOT EXISTS` — aucun impact sur base existante.
- `seed_demo_attempts.py` compatible sans modification (`user_id='default'` par défaut).
- `ai_service.py`, `app.py` non modifiés.

**Invariants préservés :**
- Moteur RAG inchangé. Fallback texte brut inchangé. Pipeline SQLite inchangé.

**Prochaine étape :**
- TASK-021 : Exposition du profil dans l'UI — bloc "Profil pédagogique" dans l'onglet Dashboard (lecture seule, recalcul au clic).

---

## 2026-05-14 — TASK-019 : Filtrage user_id — fondation multi-utilisateur

**Milestone :** Préparation multi-utilisateur minimale (Phase 10).

**Actions :**
- Ajout paramètre `user_id: str = "default"` sur 8 fonctions dans `database.py` : `save_attempt`, `get_attempts`, `get_score_evolution`, `get_error_frequency`, `get_topic_stats`, `get_chunk_stats`, `get_chunk_mastery`, `get_revision_suggestion`.
- Toutes les requêtes SQL filtrées par `AND user_id = ?`. Sous-requêtes corrélées dans `get_chunk_stats()` également filtrées.
- `app.py` : init `session_state["user_id"] = "default"` + `st.sidebar.text_input(key="user_id")`.
- 10 points d'appel dans `app.py` mis à jour.
- `get_chunk_question_history` inchangée (appelée depuis `ai_service.py` — moteur protégé).

**Décisions :**
- `user_id="default"` comme valeur par défaut : rétrocompatibilité totale, aucune migration de données nécessaire.
- Sidebar text_input : testable sans authentication, non intrusif dans le flux principal.
- Moteur `ai_service.py` non touché : la question history reste cross-user pour l'instant (rotation chunk).

**Invariants préservés :**
- `ai_service.py`, `document_service.py` non modifiés.
- Fallback texte brut inchangé.
- Pipeline RAG inchangé.
- py_compile 2/2 OK. AST check 10/10 call sites OK.

**Prochaine étape :**
- TASK-020 : Table `user_learning_profile` (migration douce, `database.py` uniquement).

Format par entrée :
- Date
- Tâche / milestone
- Actions réalisées
- Décisions prises
- Problèmes rencontrés
- Prochaine étape

---

## 2026-05-12 — Intégration App Factory

**Milestone :** Fusion organisationnelle App Factory + AI-V2.

**Actions :**
- Ajout de `task.mjs` (App Factory v2.2) à la racine.
- Ajout de `taskrc.schema.json` à la racine.
- Création de `.taskrc.json` adapté Python/Streamlit (py_compile comme review minimale).
- Création de `DEVLOG.md` (ce fichier).
- Ajout section "APP FACTORY + DEVLOG POLICY" dans `CLAUDE.md`.

**Décisions :**
- Stack de review minimaliste : `py_compile` uniquement (pas de mypy/ruff — non installés).
- Aucune modification du code métier existant.
- App Factory sert uniquement de couche de pilotage, pas de refonte.

**Invariants préservés :**
- `app.py`, `ai_service.py`, `database.py`, `document_service.py` non modifiés.
- Pipeline RAG inchangé.
- Structure SQLite inchangée.
- Fallback texte brut inchangé.

**Prochaine étape :**
- Continuer sur les priorités existantes : tracking pédagogique, stabilisation RAG.

---

## 2026-05-12 — TASK-002 : Analytics pédagogiques par chunk

**Milestone :** Exploitation de `attempts.chunk_id` (TASK-001) pour produire des analytics de progression par chunk source.

**Actions :**
- Ajout de `get_chunk_stats()` dans `database.py` : requête SQL joingnant `attempts → chunks → documents`, filtrée sur `chunk_id IS NOT NULL`, groupée par chunk, avec sous-requête corrélée pour l'erreur dominante.
- Ajout d'une section "Analytics par chunk" dans l'onglet Dashboard de `app.py` : tableau `st.dataframe` (Document, Section, Score moyen, Tentatives, Niveau, Erreur dominante) + liste des chunks fragiles (< 60 %).
- Import de `get_chunk_stats` dans `app.py`.

**Décisions :**
- Pas de graphique pour l'instant (scope validé) : tableau uniquement.
- Pas de filtre par document pour l'instant.
- Fallback `COALESCE(section_title, 'Chunk #' || chunk_index)` : aucune dépendance à `section_title`.
- Les 4 sections Dashboard existantes sont intactes.
- Section conditionnelle : si aucune tentative RAG, un message d'info s'affiche sans crash.

**Invariants préservés :**
- `ai_service.py` non modifié.
- `document_service.py` non modifié.
- Pipeline RAG inchangé.
- Système embeddings inchangé.
- Fallback texte brut inchangé.
- Schéma SQLite inchangé (aucune migration).

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- `git status` → 2 fichiers modifiés uniquement.

**Prochaine étape :**
- TASK-003 : score de maîtrise par chunk (classification Fragile / En consolidation / Maîtrisé + tendance).

---

## 2026-05-12 — TASK-003 : Score de maîtrise par chunk

**Milestone :** Transformation des analytics bruts (TASK-002) en indicateur pédagogique exploitable.

**Actions :**
- Ajout d'une sous-requête corrélée `last_score` dans `get_chunk_stats()` (database.py) : dernière tentative scorée par chunk, triée par `created_at DESC`.
- Ajout de `classify_mastery(df)` dans `database.py` : helper Python pur enrichissant le DataFrame avec `mastery_class` (Fragile / En consolidation / Maîtrisé) et `trend` (Amélioration / Stable / Dégradation / N/A).
- Remplacement de la section "Analytics par chunk" dans `app.py` : tableau enrichi (Maîtrise + Tendance) + liste de révision prioritaire (Fragile → En consolidation → caption Maîtrisé).
- Import de `classify_mastery` dans `app.py`.

**Règles de classification :**
- Maîtrisé : avg_score ≥ 0.8 ET attempts_count ≥ 3
- Fragile : avg_score < 0.6 (quel que soit le nombre de tentatives)
- En consolidation : tout le reste

**Règles de tendance :**
- N/A si une seule tentative
- Amélioration : last_score > avg_score + 0.1
- Dégradation : last_score < avg_score − 0.1
- Stable : écart ≤ 0.1

**Invariants préservés :**
- `ai_service.py`, `document_service.py` non modifiés.
- Pipeline RAG inchangé. Embeddings inchangés. Fallback inchangé.
- Schéma SQLite inchangé (aucune migration).
- Les 4 sections Dashboard existantes intactes.

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Streamlit headless port 8502 → démarrage sans erreur
- `git status` → 2 fichiers modifiés uniquement

**Prochaine étape :**
- TASK-004 : suggestion de révision dans l'onglet Entraînement (fermeture de la boucle pédagogique).

---

## 2026-05-12 — TASK-004 : Suggestion de révision dans l'onglet Entraînement

**Milestone :** Fermeture de la boucle pédagogique — passer de l'observation (Dashboard) à l'action directe (Entraînement).

**Actions :**
- Ajout de `get_revision_suggestion()` dans `database.py` : requête SQL autonome, JOIN attempts→chunks→documents, HAVING exclut les chunks Maîtrisés, ORDER BY priorité Fragile → ancienneté → score faible, LIMIT 1, retourne dict ou None.
- Ajout de `from datetime import datetime` dans `app.py`.
- Ajout de `get_revision_suggestion` dans les imports database de `app.py`.
- Ajout du bloc "Révision suggérée" dans l'onglet Entraînement (avant la zone de texte) : section, document, score, tentatives, ancienneté, bouton "Réviser ce chunk →" via `_make_use_callback`.

**Règles de priorité :**
1. Fragile (avg_score < 0.6) avant En consolidation
2. Tentative la plus ancienne (MAX(created_at) ASC)
3. Score le plus faible (AVG(score) ASC)

**Invariants préservés :**
- Bloc conditionnel : absent si aucun chunk éligible (aucune tentative RAG ou tout maîtrisé).
- `ai_service.py`, `document_service.py` non modifiés.
- Pipeline RAG, embeddings, fallback inchangés.
- Schéma SQLite inchangé.
- Onglet Entraînement existant intact sous le bloc.

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Streamlit headless port 8503 → démarrage sans erreur
- `git status` → 2 fichiers modifiés uniquement

**Prochaine étape :**
- TASK-005 : variation pédagogique dans la génération de questions.

---

## 2026-05-12 — TASK-005 : Variation pédagogique dans la génération de questions

**Milestone :** Résoudre la répétition de questions identiques en introduisant 6 types de questions et une rotation par historique de chunk.

**Actions :**
- Ajout de `get_chunk_question_history(chunk_id, limit)` dans `database.py` : lit `pedagogy_type` comme `question_type` sur les dernières tentatives d'un chunk (colonne existante, aucune migration).
- Ajout dans `ai_service.py` : `import random`, `QUESTION_TYPES` (6 types), `_TYPE_PROMPTS` (dict clé→instruction LLM), `_choose_question_type(used_types)` (rotation équitable, aléatoire en cas d'égalité).
- Modification de `generate_question()` : lookup historique sur `chunk_ids[0]` après retrieval RAG, choix du type par rotation, prompt enrichi avec l'instruction du type + anti-doublon (2 dernières questions du chunk), retour `tuple[str, list[int], str]` (+question_type).
- Mise à jour `app.py` : session_state `question_type` initialisé, dépaquetage 3-tuple, `pedagogy_type=question_type` passé à `save_attempt()`.

**Types de questions implémentés :**
1. question_directe, 2. cas_pratique, 3. vrai_faux, 4. question_piege, 5. reformulation, 6. consequence

**Invariants préservés :**
- Fallback texte brut intact : si chunk_ids=[], type aléatoire, pas de lookup DB.
- Pipeline RAG inchangé. Embeddings inchangés.
- Aucune nouvelle dépendance (random = stdlib).
- Aucune migration SQLite (pedagogy_type existait déjà, était toujours NULL).
- `correct_answer()` non modifié.

**Validation :**
- `py_compile database.py / ai_service.py / app.py` → OK (3/3)
- `_choose_question_type([])` → type valide ✓
- `_choose_question_type(["question_directe"]*4)` → rotation correcte ✓
- `_choose_question_type([tous sauf consequence])` → consequence ✓
- `get_chunk_question_history(99999)` → [] ✓
- Streamlit headless port 8504 → démarrage sans erreur ✓

**Prochaine étape :**
- TASK-006 : répétition espacée légère.

---

## 2026-05-12 — TASK-006 : Répétition espacée légère

**Milestone :** Ajouter une dimension temporelle au moteur pédagogique — chaque chunk a désormais une date de prochaine révision calculée dynamiquement.

**Actions :**
- Ajout `from datetime import datetime, timedelta` dans `database.py`.
- Ajout constante `REVIEW_INTERVALS` (Fragile=1j, En consolidation=3j, Maîtrisé=7j) à la racine de `database.py` avec note de synchronisation avec le SQL.
- `get_chunk_stats()` : ajout `MAX(a.created_at) AS last_attempt_date` dans le SELECT.
- `classify_mastery(df)` : ajout de 3 colonnes calculées en Python pur : `next_review` (datetime), `days_until_review` (int), `review_status` (En retard / Aujourd'hui / Dans N jour(s) / —).
- `get_revision_suggestion()` : ORDER BY mis à jour — chunks en retard de révision priorisés via `datetime(MAX(created_at), '+N days') <= datetime('now')` en SQLite inline.
- `app.py` Dashboard "Analytics par chunk" : colonnes `Statut révision` et `Prochaine révision` ajoutées au tableau.
- `app.py` "Priorités de révision" : indicateur "⚠ Révision en retard" sur les lignes en retard.

**Règles de calcul :**
- next_review = last_attempt_date + REVIEW_INTERVALS[mastery_class]
- days_until_review = (next_review.date() - today).days
- Négatif = en retard, 0 = aujourd'hui, positif = dans N jours

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts. Fallback intact.
- Toutes les fonctions TASK-001 à TASK-005 non modifiées dans leur comportement.
- `classify_mastery()` retourne toujours `mastery_class` et `trend` (colonnes existantes inchangées).

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Tests helpers : Fragile 2j ago → En retard ✓ | Fragile 1j ago → Aujourd'hui ✓ | Consolidation 1j ago → Dans 2 jours ✓ | Consolidation 4j ago → En retard ✓ | Maîtrisé 6j ago → Dans 1 jour ✓ | last_attempt_date=None → pas de crash ✓
- Streamlit headless port 8505 → démarrage sans erreur ✓
- git status → 2 fichiers modifiés uniquement ✓

**Prochaine étape :**
- TASK-007 : contenu de démo préchargé, seed idempotente au démarrage.

---

## 2026-05-12 — TASK-007 : Contenu de démo préchargé

**Milestone :** L'application n'est plus vide au premier lancement — un document de démonstration SNCF est inséré automatiquement et de façon idempotente.

**Actions :**
- Ajout de `has_documents() -> bool` dans `database.py` : COUNT(*) sur documents, O(1).
- Ajout import `has_documents` dans `document_service.py`.
- Ajout de `_DEMO_TITLE`, `_DEMO_TEXT` (~3 200 chars, 4 sections : accueil, perturbations, PMR, traçabilité) et `seed_demo_document()` dans `document_service.py`.
- `seed_demo_document()` : guard `has_documents()` → idempotente, appel `ingest_document()` avec try/except non bloquant, embeddings tentés si API key présente sinon NULL.
- Ajout import `seed_demo_document` dans `app.py` + appel après `init_db()`.

**Contenu du document de démo :**
Procédure fictive "Accueil et orientation des voyageurs en gare" — 4 sections pédagogiquement riches activant les 6 types de questions (délais, priorités, conditions d'exclusion, traçabilité, PMR). 4 chunks créés au découpage.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts.
- Seed sans effet si un document existe déjà (idempotente).
- Startup non bloquant : si seed échoue → logger.warning, app démarre quand même.
- Toutes les fonctions TASK-001 à TASK-006 non modifiées.

**Validation :**
- `py_compile database.py / document_service.py / app.py` → OK (3/3)
- `has_documents()` base vide → False ✓
- `has_documents()` après seed → True ✓
- Idempotence (2 appels) → 1 document en base ✓
- Chunks créés → 4 ✓
- Streamlit headless port 8506 → démarrage sans erreur ✓
- git status → 3 fichiers code modifiés uniquement ✓

**Prochaine étape :**
- TASK-008 : dashboard reformaté pour utilisateur final (labels lisibles, masquage champs techniques).

---

## 2026-05-12 — TASK-008 : Dashboard reformaté pour utilisateur final

**Milestone :** Supprimer tous les termes techniques visibles par un utilisateur final lors d'une démonstration SNCF.

**Actions :**
- `database.py` : remplacement de `'Chunk #' || c.chunk_index` par `'Section ' || (c.chunk_index + 1)` dans `get_chunk_stats()` et `get_revision_suggestion()`. Les sections s'affichent désormais "Section 1", "Section 2"… (1-indexé).
- `app.py` : ajout de `active_document_title` dans les clés session_state initialisées.
- `app.py` : `_make_use_callback` reçoit un paramètre `doc_title` et le stocke dans `active_document_title`.
- `app.py` Entraînement : caption `"Source : document importé (ID X)"` → `"Source : {titre du document}"`.
- `app.py` Dashboard : titre `"Analytics par chunk"` → `"Progression par section"`.
- `app.py` Documents — label expander : `"chunk"` → `"section"`.
- `app.py` Documents — métrique : `"Chunks"` → `"Sections"`.
- `app.py` Documents — bouton reindex : `"chunk(s) manquant(s)"` → `"section(s) manquante(s)"`.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance.
- Clé `section_label` inchangée dans les dicts retournés — seule la valeur change.
- RAG intact. Embeddings intacts. Fallback intact.
- Toutes les fonctions TASK-001 à TASK-007 non modifiées dans leur comportement.

**Validation :**
- `py_compile database.py` → OK
- `py_compile app.py` → OK
- Streamlit headless port 8507 → démarrage sans erreur

**Prochaine étape :**
- TASK-009 : détection automatique de section_title dans le chunker.

---

## 2026-05-12 — TASK-009 : Détection automatique de section_title dans le chunker

**Milestone :** Peupler la colonne `section_title` des chunks pour les documents ayant une structure numérotée ou markdown, sans migration SQLite ni nouvelle dépendance.

**Actions :**
- Ajout de la constante `_SECTION_RE` dans `document_service.py` : regex détectant les titres numérotés (`1. Titre`, `2) Titre`) et markdown (`## Titre`), avec limite de 120 chars anti-faux-positifs.
- Ajout du helper `_detect_section_title(para) -> str | None` : pure function, retourne le paragraphe s'il est un titre, None sinon.
- Modification de `_create_chunks()` : ajout de `current_section: str | None = None` ; `flush()` utilise `current_section` comme `section_title` ; boucle principale détecte les titres (flush + reset overlap + nouveau buffer) ; chemin hard-split hérite aussi de `current_section`.

**Comportement :**
- Document avec sections numérotées → `section_title` peuplé, titre inclus dans le chunk pour la qualité RAG.
- Document sans structure → `section_title = None` pour tous les chunks, fallback "Section N+1" inchangé (aucune régression).
- Chemin hard-split (paragraphe > 1000 chars) → hérite du `current_section` actif.

**Non fait intentionnellement :**
- Pas de réinitialisation de la base → chunks existants (dont le document de démo) conservent `section_title=NULL`. Seuls les nouveaux imports bénéficieront des vrais titres.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts. Fallback intact.
- `ingest_document()`, `reindex_document()`, pipeline complet non modifiés.

**Validation :**
- `py_compile document_service.py` → OK
- 8/8 tests OK : détection numérotée, markdown, trop long, paragraphe ordinaire, sections peuplées, sans structure, 4 sections démo, hard-split.
- Streamlit headless port 8508 → démarrage sans erreur.
- git status → 1 fichier code modifié uniquement.

**Prochaine étape :**
- TASK-010 : guide de démo + README utilisateur.

---

## 2026-05-12 — TASK-010 : Guide de démo + README utilisateur

**Milestone :** Rendre le projet présentable à un jury SNCF et installable par un tiers sans accompagnement.

**Actions :**
- `README.md` réécrit intégralement : description réelle du projet, prérequis, installation, configuration API key + fallback explicité, lancement, architecture réelle (5 fichiers), stack technique, commande de réinitialisation de la base.
- `DEMO.md` créé : scénario 7 étapes ordonnées (Documents → Entraînement → correction → Dashboard → suggestion → boucle fermée → fallback optionnel), actions claires + script de parole jury, tableau récapitulatif des points clés, conseil de préparation préalable.

**Invariants préservés :**
- Aucune modification de code. Aucun changement de schéma. Pipeline intact.

**Prochaine étape :**
- À définir selon priorités : reset démo avec vrais titres de section, amélioration RAG, ou nouvelle fonctionnalité pédagogique.

---

## 2026-05-12 — TASK-011 : Adaptation pédagogique par niveau de maîtrise

**Milestone :** Le moteur de questions adapte le type pédagogique au niveau de maîtrise de la section, pas seulement à l'historique de rotation.

**Actions :**
- Ajout de `get_chunk_mastery(chunk_id) -> str | None` dans `database.py` : requête `AVG(score), COUNT(*)` ciblée, retourne Fragile / En consolidation / Maîtrisé ou None. Mêmes règles que `classify_mastery()`.
- Ajout de `_MASTERY_BIAS` dans `ai_service.py` : dict Fragile → [reformulation, consequence, cas_pratique] / Maîtrisé → [question_piege, cas_pratique, consequence].
- Modification de `_choose_question_type(used_types, mastery_class=None)` : le biais est appliqué sur les candidats équitables (intersection). Si le biais ne recoupe aucun candidat équitable, rotation standard — aucune régression possible.
- Modification de `generate_question()` : lookup `get_chunk_mastery(chunk_ids[0])` après retrieval RAG, passé à `_choose_question_type`. Protégé par try/except — non bloquant.
- Import de `get_chunk_mastery` ajouté dans `ai_service.py`.

**Comportement sur la démo :**
- Section Posture (Fragile) : reformulation, consequence, cas_pratique favorisés.
- Sections Perturbations / PMR (En consolidation) : rotation équitable inchangée.
- Section Traçabilité (Maîtrisé) : question_piege, cas_pratique, consequence favorisés.
- Fallback texte brut (chunk_ids=[]) : mastery=None → rotation équitable inchangée.

**Invariants préservés :**
- Aucune migration SQLite. Aucune nouvelle dépendance. RAG intact. Embeddings intacts. Fallback intact.
- Signature de `generate_question()` inchangée (tuple[str, list[int], str]).
- `correct_answer()` non modifié. `app.py` non modifié.

**Validation :**
- `py_compile database.py / ai_service.py` → OK
- 9/9 tests OK : biais Fragile/Maîtrisé, saturation → fallback, En consolidation libre, get_chunk_mastery (None / Fragile / Maîtrisé).
- Streamlit headless port 8511 → démarrage sans erreur.
- git status → 2 fichiers code modifiés uniquement.

**Prochaine étape :**
- À définir.

---

## 2026-05-12 — TASK-012 : Sélecteur de document inline dans l'onglet Entraînement

**Milestone :** FRONTEND/UX — éliminer la navigation entre onglets pour sélectionner un document.

**Actions :**
- Ajout d'un `st.selectbox` "Document de travail" dans l'onglet Entraînement, avant la zone de texte source. Options : "— Texte libre (sans RAG)" + liste des documents importés.
- Sur changement de sélection : charge `cleaned_text` + met à jour `active_document_id`, `active_document_title`, `source_text_input` en session_state, réinitialise question et résultat, appelle `st.rerun()`.
- Le sélecteur se pré-positionne sur le document actif (lecture de `active_document_id`). Si le document actif est changé via la suggestion de révision (`_make_use_callback`), le sélecteur se resynchronise au prochain rerun.
- Correction du libellé `"Réviser ce chunk →"` → `"Réviser cette section →"` (oubli TASK-008).

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Aucune modification du moteur critique. RAG, embeddings, scoring, répétition espacée intacts.
- Onglet Documents inchangé. `_make_use_callback` inchangé.
- Si aucun document en base : sélecteur masqué, comportement identique à l'existant.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8512 → démarrage sans erreur.
- git status → 1 fichier modifié uniquement.

**Prochaine étape :**
- À définir.

---

## 2026-05-12 — TASK-013 : Export du rapport de progression

**Milestone :** FRONTEND/UX — générer et télécharger un rapport texte structuré depuis le Dashboard.

**Actions :**
- Ajout de `_build_report(df_all, df_topics, df_chunks) -> str` dans `app.py` : rapport texte brut 60 colonnes avec synthèse globale, maîtrise par section et priorités de révision.
- Ajout d'un `st.download_button` à la fin du bloc Dashboard (df_chunks non vide) : génère `rapport_progression_YYYYMMDD.txt` encodé UTF-8.
- Correction `"Tous les chunks sont maîtrisés"` → `"Toutes les sections sont maîtrisées"`.
- Correction caption `"chunk maîtrisé"` → `"section maîtrisée"` (accord féminin).
- Format choisi : texte brut structuré (robustesse, zéro dépendance, compatibilité maximale).

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Aucune modification du moteur critique. RAG, embeddings, scoring, répétition espacée intacts.
- `_build_report()` est un formateur de présentation pur — aucun accès DB direct.
- Bouton visible seulement si df_chunks non vide (données RAG disponibles).

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8509 → démarrage sans erreur (HTTP 200).

**Prochaine étape :**
- À définir.

---

## 2026-05-12 — TASK-014 : Dashboard pédagogique visuel moderne

**Milestone :** FRONTEND/UX — refonte visuelle complète du Dashboard pour démonstration jury.

**Actions :**
- Ajout `import pandas as pd` (nécessaire pour `pd.concat` dans les cartes section).
- Zone 1 — KPIs enrichis : remplacement "Meilleure notion / Notion fragile" par "Sections maîtrisées X/N" et "Révisions en retard N".
- Zone 2 — Card révision prioritaire : `st.container(border=True)` mettant en avant la section la plus urgente (Fragile → En consolidation), immédiatement visible en haut du Dashboard.
- Zone 3 — Cartes de section : remplacement du dataframe 9 colonnes + liste st.error/warning par des cartes visuelles avec badge couleur (🔴/🟡/🟢), `st.progress()` (barre de score), tentatives et statut révision.
- Zone 4 — Graphiques conservés : évolution des scores, score par notion, types d'erreurs. Supprimés : "Notions fragiles" (redondant) et "Tentatives par notion" (faible valeur).
- Zone 5 — Bloc IA adaptative : `st.info()` texte fixe explicitant le mécanisme de biais pédagogique au jury.
- Zone 6 — Export : bouton de téléchargement conservé.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Aucune modification du moteur critique. Aucune nouvelle requête DB. Données réutilisées depuis `df_all`, `df_topics`, `df_chunks`.
- `classify_mastery()` déplacée avant les métriques (reorder, pas de changement logique).

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8511 → démarrage sans erreur (HTTP 200).

**Prochaine étape :**
- À définir.

---

## 2026-05-13 — TASK-015 : Mode démo guidée / Storytelling produit

**Milestone :** FRONTEND/UX — transformer le MVP technique en démonstration produit convaincante pour un décideur non-tech.

**Actions :**
- Import de `get_chunk_mastery` dans `app.py` (lecture seule, moteur inchangé).
- Header HTML : titre + tagline + banner 7 pills pipeline (Document → RAG → Question → Réponse → Correction → Mémoire → Révision prioritaire).
- Ajout de `question_mastery` dans session_state initialisé.
- 5ème onglet `tab_engine` "Moteur IA".
- Dicts `_TYPE_EXPLANATIONS` (6 types → explication pédagogique) et `_MASTERY_BIAS_LABELS` (3 niveaux → label lisible).
- Expander "Pourquoi cette question ?" dans l'onglet Entraînement : type, explication pédagogique, biais de maîtrise.
- Caption mémoire post-correction : rappel du biais actif.
- Explication "Pourquoi prioritaire ?" dans la card prioritaire du Dashboard.
- Onglet Moteur IA : pipeline 7 étapes, 6 types de questions, répétition espacée, adaptation cognitive.
- Lookup `get_chunk_mastery(chunk_ids[0])` au moment de la génération de question.

**Fichiers modifiés :** `app.py` uniquement. `ai_service.py`, `database.py`, `document_service.py` non modifiés.

**Invariants préservés :**
- Moteur critique intact. Fallback texte brut intact. Pipeline RAG intact.
- `get_chunk_mastery` déjà présent dans `database.py` (TASK-011) — aucune modification.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8515 → OK

**Commit :** `479d0c0`

---

## 2026-05-13 — TASK-016 : UX Premium / Densification visuelle / Finition produit

**Milestone :** FRONTEND/UX — éliminer la sensation prototype Streamlit brut, poser les bases d'un dashboard IA métier premium.

**Actions :**
- CSS global injecté après `st.set_page_config` : padding `block-container` 1rem, `hr` fins `#e2e8f0`, alerts compacts, tabs `font-weight 600`, metric labels `text-transform uppercase font-size 11px`, containers `border-radius 8px`, captions `font-size 12px`.
- Header HTML refait : titre bold-900 + tagline + 7 pipeline pills avec séparateurs `›`.
- Helper `_kpi_card(icon, label, value, accent) -> str` : fond `#f8fafc`, border, radius 10px, icône 22px, valeur 26px bold-800, label 11px uppercase.
- Dashboard KPI : 4 `_kpi_card()` en colonnes avec accents couleur (vert maîtrise, rouge retard).
- Onglet Moteur IA : pipeline en grille HTML 2 colonnes (7 étapes), 6 types en grille 3 colonnes, répétition espacée + adaptation cognitive en 2 colonnes `st.columns`.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Moteur critique intact. Session state intact. Toute logique existante conservée.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8525 → OK

**Commit :** `dd70b0b`

---

## 2026-05-13 — TASK-017 : Branding premium / Identité produit / Profondeur visuelle — SYNPZ OPS

**Milestone :** BRANDING — faire passer SYNPZ OPS du registre bon MVP Streamlit à véritable produit IA métier identifiable.

**Actions :**
- `page_title` → "SYNPZ OPS", `page_icon` → 🧠.
- CSS enrichi : `.stApp {background-color:#f5f6fa}`, cards `box-shadow 0 1px 3px rgba(0,0,0,.08)`, expanders `border #e2e8f0 background #fff`, bloc info `border-left 3px solid #4f46e5`.
- Header HTML reconstruit : barre accent indigo `4px #4f46e5` à gauche, "SYNPZ OPS" bold-800 36px, badge "Adaptive Learning Intelligence" fond `#eef2ff` texte `#4f46e5`, pills pipeline blanches ombragées, dernière pill fond `#4f46e5` texte blanc.
- `_kpi_card()` upgradé : fond blanc, `box-shadow 0 2px 8px rgba(0,0,0,.07)`, valeur 30px letter-spacing `.02em`, label 10px spacing `.08em`.
- Dashboard : subheader styled HTML uppercase tracking, titres sections 12px uppercase.
- Graphiques compactés : line chart 210px, bar charts `max(200, n*44)`.
- Palette cohérente : `#16a34a` vert, `#d97706` orange, `#dc2626` rouge, `#6366f1` violet erreurs.
- Zone analyse moteur condensée en 1 ligne `st.caption`.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur).

**Invariants préservés :**
- Moteur critique intact. Aucune nouvelle dépendance. Fallback intact.

**Décision :** Nom produit "SYNPZ OPS" adopté définitivement. Palette indigo `#4f46e5` comme accent primaire.

**Validation :**
- `py_compile app.py` → OK
- Streamlit headless port 8535 → OK

**Commit :** `5baef8e`

---

## 2026-05-13 — TASK-018 : Intelligence pédagogique adaptative / Expérience utilisateur cognitive — SYNPZ OPS

**Milestone :** FRONTEND/UX — rendre l'intelligence du moteur adaptative explicite et lisible dans chaque zone de l'interface.

**Actions :**
- `_mastery_state(row) -> tuple[str, str, str]` : 8 états dynamiques combinant `mastery_class` + `trend` + `days_until_review`. Retourne (icône, label, couleur) pour chaque chunk. Exemple : "Maîtrisé + Amélioration" → 🏆 vert foncé ; "Fragile + Dégradation + retard" → 🔥 rouge.
- `_build_recommendations(df_chunks, df_errors) -> list[tuple[str,str]]` : moteur de recommandations, max 5 items, 4 types (urgent/warning/success/info) selon : chunks en retard, chunks Fragile, erreur dominante, performance globale, sections maîtrisées.
- `df_errors = get_error_frequency()` remonté en tête de bloc Dashboard (avant les métriques) pour alimenter les recommandations.
- Expander "Pourquoi cette question ?" enrichi : trend (📈/📉/—), review_status (⏰ si retard, 📅 sinon), dominant_error (🔍 si présent).
- Dashboard restructuré : KPI → recommandations → priority card → section cards avec `_mastery_state()` + erreur dominante → évolution scores → analytics 2-col → mini-timeline → analyse dynamique → export.
- Mini-timeline : 8 derniers `attempts` (score desc created_at) affichés comme pills colorées (vert ≥0.8, orange ≥0.6, rouge <0.6) + label "N%" en HTML inline.
- Analyse pédagogique dynamique : 4 profils (excellent ≥0.8 avg, consolidation ≥0.6, fragile <0.6 avec historique, démarrage sans données) → texte adaptatif dans `st.info`.

**Fichiers modifiés :** `app.py` uniquement (FRONTEND/UX pur). Correction du doublon `df_errors` (assignation redondante supprimée dans Zone 4c).

**Invariants préservés :**
- Moteur critique (`database.py`, `ai_service.py`, `document_service.py`) non modifié.
- Toutes les données exploitées via `classify_mastery()` existant — aucune nouvelle requête DB.
- Fallback intact. Pipeline RAG intact. Session state intact.

**Validation :**
- `py_compile app.py` → OK
- Streamlit → OK

**Commit :** `4cd3868`

**Prochaine étape :**
- À définir selon priorités.

---
