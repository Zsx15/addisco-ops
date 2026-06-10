# ADDISCO OPS — Présentation 10 minutes
## Forces et faiblesses du projet

---

## Structure de la présentation

| Bloc | Durée |
|------|-------|
| 1. Mise en contexte | 1 min |
| 2. Ce que fait le produit | 1 min |
| 3. Forces (6 points) | 4 min |
| 4. Faiblesses / axes d'amélioration (6 points) | 2 min |
| 5. Vision et prochaines étapes | 1 min |
| 6. Questions | 1 min |

---

## 1. Mise en contexte (1 min)

**Ce projet, c'est quoi ?**

ADDISCO OPS est un moteur de révision pédagogique adaptatif basé sur l'IA.
Il permet à n'importe quelle organisation d'importer ses documents métier,
et de former ses collaborateurs par des sessions de révision pilotées par l'intelligence artificielle.

**Contexte personnel :**
Projet développé seul, de zéro, en l'espace de 20 phases incrémentales.
Portfolio de reconversion IT. Aujourd'hui : en production sur Railway.

---

## 2. Ce que fait le produit (1 min)

**Pipeline en 4 étapes :**

1. **Import** — PDF, TXT, DOCX importés et découpés en chunks sémantiques
2. **RAG** — chaque question est générée à partir des passages les plus pertinents (embeddings OpenAI)
3. **Correction IA** — la réponse est évaluée par le LLM avec score, explication et type d'erreur
4. **Adaptation** — le moteur ajuste la difficulté, le style pédagogique et l'intervalle de révision

**Rôles disponibles :** apprenant / formateur / admin

---

## 3. FORCES (4 min — ~40 sec par point)

---

### Force 1 — Architecture modulaire et maintenable

Le projet a été construit en **20 phases incrémentales sans jamais casser le MVP**.

```
app.py (routeur < 150 lignes)
tabs/          → 6 onglets isolés
engine/        → moteur pédagogique pur (zéro import projet)
db/            → couche données segmentée (7 modules)
ai_gateway/    → abstraction OpenAI découplée
auth_service   → authentification indépendante
```

Chaque module est testable, remplaçable, explicable.
La dette technique a été soldée à chaque phase avant d'avancer.

**Ce que ça démontre :** discipline d'ingénierie, vision long terme, capacité à refactorer sans régression.

---

### Force 2 — Moteur pédagogique adaptatif réel

Le moteur n'est pas un générateur de questions statique.
Il observe le comportement de l'utilisateur et s'adapte en temps réel.

#### Répétition espacée (`engine/spaced_rep.py`)

Chaque chunk est classé dans 3 états et l'intervalle de révision est modulé par la tendance :

| État | Condition | Intervalle de base |
|------|-----------|-------------------|
| Fragile | score moyen < 0.60 | J+1 (J+2 si tendance Amélioration) |
| En consolidation | 0.60 ≤ score < 0.80 | J+3 (J+5 si Amélioration, J+2 si Dégradation) |
| Maîtrisé | score ≥ 0.80 **ET** ≥ 5 tentatives | J+7 |

La tendance (Amélioration / Stable / Dégradation) est calculée sur le delta entre le dernier score et la moyenne historique.

#### Difficulté adaptative (`engine/adaptive_difficulty.py`)

Le type de question est sélectionné en 5 étapes priorisées :

1. **Correction d'erreur dominante** — si une même erreur apparaît ≥ 2 fois, le type correctif est prioritaire (ex : `oubli_etape` → `cas_pratique`)
2. **Cible de difficulté** — calculée depuis le score récent + niveau Bloom + état de maîtrise
3. **Rotation équitable** — le type le moins utilisé sur ce chunk est privilégié
4. **Filtre par bucket** — easy / medium / hard (ex : `question_piege` est réservé au hard)
5. **Tie-breaker profil** — le style pédagogique préféré débloque en cas d'égalité

Règle dure : score récent < 0.40 → always easy, quelle que soit la maîtrise. Niveaux Bloom 0-1 jamais en hard.

#### Graphe de compétences Bloom (`engine/skill_graph.py`)

10 skills sur 5 niveaux avec dépendances déclaratives :

```
Lvl 0 — memorisation_faits, identification_concepts
Lvl 1 — comprehension_procedure
Lvl 2 — application_regles, analyse_causale, synthese_reformulation
Lvl 3 — conformite_reglementaire, resolution_problemes
Lvl 4 — prise_decision, evaluation_critique
```

Le moteur sait quels prérequis bloquent un skill, calcule l'ordre de session optimal par tri topologique, et détecte les chaînes de blocage transitives.

#### Profil apprenant (`engine/profile_metrics.py`)

3 métriques calculées en continu :
- **Momentum** — delta de score moyen entre les 7 derniers jours et les 7 jours précédents (accélération)
- **Learning velocity** — delta moyen de score inter-sessions jour par jour
- **Consistency score** — jours actifs / 30 jours (régularité)

#### Mémoire des erreurs + Curriculum Engine

Le moteur détecte des patterns d'erreurs persistants (`critique`, `chronique`, `récent`) et mappe chacun sur un skill cible et un type de question correctif.

Le Curriculum Engine (`engine/curriculum_engine.py`) construit une queue pédagogique ordonnée par score de priorité depuis 3 sources simultanées : patterns d'erreurs, maîtrise Bloom, et révision espacée due.

**Calibration rigoureuse :**
6 seuils moteur validés par un harness de calibration isolé (DB temporaire, pas de side-effect).
Exemple : MASTERY_MIN_ATTEMPTS calibré à 5 après simulation de 500 sessions.

---

### Force 3 — Pipeline RAG instrumenté et auditable

Le pipeline de retrieval sémantique est **observé en temps réel**.

- Latence par appel LLM loggée en JSONL
- Coût estimé par requête
- Taux de fallback tracké
- Dashboard admin : 8 KPIs + 8 graphiques Plotly (tendances 24h / 7j)
- CLI analytique avec verdict OK / WARNING / CRITICAL

**Fallback défensif :**
Si l'API OpenAI est indisponible → mode texte brut automatique, sans crash.
Si le RAG échoue → génération depuis le contexte brut.

---

### Force 4 — Production readiness réelle

Le projet n'est pas un prototype local.
Il est **déployé et accessible en ligne** (Railway).

**Stack production :**
- Docker (`python:3.12-slim`, healthcheck, volume `/app/data`)
- CI/CD GitHub Actions (py_compile 100 fichiers, pytest 262 tests)
- Sentry LoggingIntegration (monitoring erreurs prod)
- Rate limiting sliding window par utilisateur
- Authentification bcrypt, rôles multi-niveaux
- Rapport HTML/PDF exportable (7 sections, CSS inline)

**Score auditor interne : 99/100**
(audit automatisé 10 sections, ~1 300 lignes, verdict GO SAFE)

---

### Force 5 — Corpus multi-documents et recherche sémantique

L'utilisateur ne travaille plus sur un seul document.
Il construit un **corpus nommé** avec plusieurs sources.

- Import PDF, TXT, DOCX
- Catégorisation par domaine métier
- Entraînement cross-documents sur tout le corpus
- Recherche sémantique sur l'ensemble des chunks autorisés
- Filtrage analytics par corpus (backward compatible)

---

### Force 6 — Feedback utilisateur et session tracking

Le système collecte du feedback réel pour améliorer le produit.

- Feedback qualitatif par question (pertinent / non pertinent)
- Feedback session en 2 étapes (score subjectif + raison)
- Session tracking complet : tables `learning_sessions` + `session_events`
- Heatmap d'activité 8 semaines, évolution score, insights storytelling
- Seed POC freezé pour la présentation (données démo reproductibles)

---

## 4. FAIBLESSES (2 min)

---

### Faiblesse 1 — SQLite en production

**Le problème :**
SQLite ne supporte pas la concurrence multi-utilisateurs.
Au-delà de ~10 utilisateurs simultanés, des locks peuvent apparaître.
La recherche vectorielle est faite en Python pur (numpy cosinus), pas par un moteur dédié.

**Ce qui est prévu :**
Phase 13 (différée) : migration SQLAlchemy + PostgreSQL + pgvector.
Le code est déjà conçu pour cette migration : signatures de fonctions stables, `DATABASE_URL` prêt.

**Impact actuel :** nul en démo et en usage individuel. Bloquant uniquement à l'échelle SaaS.

---

### Faiblesse 2 — Curriculum Engine : construit mais pas encore câblé

**Le problème :**
`engine/curriculum_engine.py` est la pièce la plus sophistiquée du moteur.
Il calcule une queue pédagogique ordonnée par priorité depuis les patterns d'erreurs,
la maîtrise Bloom et les révisions dues. Mais il est explicitement marqué **"Phase 1 : OBSERVATION ONLY"** dans le code.

Concrètement : `select_next_learning_step()` calcule bien la meilleure étape suivante,
mais `generate_question()` n'est pas encore câblé dessus pour choisir le chunk.
Le curriculum arbitrage est non-bloquant — il influence, mais ne pilote pas encore la sélection.

**Ce qui est prévu :**
Brancher le Curriculum Engine dans le pipeline de génération = Phase V4.
Toute l'infrastructure est prête, il manque uniquement l'intégration finale.

**Impact actuel :** l'adaptation fonctionne via les heuristiques de maîtrise/biais.
La queue curriculum existe en parallèle comme signal enrichi, pas encore comme décideur.

---

### Faiblesse 3 — Répétition espacée : intervalles fixes, pas de courbe d'oubli

**Le problème :**
Les intervalles de révision sont fixes par classe de maîtrise (J+1 / J+3 / J+7).
Il n'y a pas de courbe d'oubli calculée (modèle Ebbinghaus / SM-2).
Un système Anki complet peut espacer jusqu'à 6 mois — ici le maximum est 7 jours.

**Pourquoi ce choix :**
Priorité à la stabilité et à la calibration des seuils (validée par harness).
Un modèle SM-2 complet nécessite un historique long pour être fiable.

**Ce qui est prévu :**
Enrichir `engine/spaced_rep.py` avec un modèle de rétention dynamique une fois les données utilisateurs réelles collectées (Phase Railway).

---

### Faiblesse 4 — Dépendance forte à OpenAI

**Le problème :**
Toutes les embeddings et les générations passent par l'API OpenAI.
Coût variable, latence réseau, indisponibilité possible.

**Atténuation existante :**
- Fallback automatique si l'API échoue
- Rate limiting pour limiter les coûts
- Logs JSONL pour auditer les coûts réels

**Ce qui manque :**
Option LLM local (Ollama, Mistral local) pour un mode offline réel ou sans coût API.

---

### Faiblesse 3 — Frontend Streamlit : flexibilité UX limitée

**Le problème :**
Streamlit est rapide à prototyper mais impose des contraintes fortes :
pas de routing URL propre, rechargements de page sur chaque interaction,
animations limitées, customisation CSS partielle.

**Pourquoi ce choix :**
Streamlit a permis de construire rapidement un produit démontrable complet.
La priorité était le moteur pédagogique, pas le framework frontend.

**Ce qui est prévu :**
Une version V4 du projet envisage une migration partielle vers un frontend découplé.

---

### Faiblesse 4 — Bus factor = 1

**Le problème :**
Le projet est développé seul. Toute la connaissance est centralisée.

**Atténuation :**
- Documentation rigoureuse : ARCHITECTURE.md, ROADMAP.md, DEVLOG.md, TASK_MASTER.md
- 262 tests automatisés
- Commits atomiques et descriptifs
- Architecture modulaire facilite l'onboarding

---

## 5. Vision et prochaines étapes (1 min)

**Ce que devient ADDISCO OPS :**

Un SaaS pédagogique B2B permettant à toute organisation de créer
un corpus documentaire intelligent et de former ses collaborateurs
par révision adaptative basée sur l'IA.

**Prochaines étapes concrètes :**

1. Migration PostgreSQL + pgvector (Phase 13 différée — prête à démarrer)
2. Frontend découplé React ou FastAPI + React (V4)
3. Tests utilisateurs réels — collecte feedback via Railway
4. Modèle économique : licence SaaS par organisation / par apprenant actif

---

## 6. Message clé à retenir

> ADDISCO OPS n'est pas un exercice de style.
> C'est un produit fonctionnel, déployé, testé, calibré et documenté —
> construit seul, phase par phase, avec une discipline d'ingénierie professionnelle.
>
> Les faiblesses identifiées sont connues, documentées, et ont des plans de résolution.
> Ce n'est pas un projet terminé — c'est une base industrielle sérieuse.

---

## Données chiffrées à citer en présentation

| Métrique | Valeur |
|----------|--------|
| Phases complètes | 20/20 |
| Tests automatisés | 262 |
| Score auditor | 99/100 |
| Seuils moteur calibrés | 6/6 |
| Skills Bloom dans le graphe | 10 (5 niveaux) |
| Types de questions | 6 |
| Métriques profil apprenant | 3 (momentum, velocity, consistency) |
| États de maîtrise | 3 (Fragile / En consolidation / Maîtrisé) |
| Formats d'import | 3 (PDF, TXT, DOCX) |
| Rôles utilisateurs | 3 (apprenant / formateur / admin) |
| Modules principaux | 12+ |
| Déploiement | Railway (live) |
| CI/CD | GitHub Actions |
