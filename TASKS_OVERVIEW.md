# TASKS — Ordre d’exécution pour Claude Code

## Mode d’emploi

Claude Code doit traiter les tâches une par une.
Ne pas passer à la suivante sans validation.

---

## Tâche 1 — Analyse initiale

Instruction :
Analyser le projet actuel sans modifier aucun fichier.

Résultat attendu :
- fichiers détectés ;
- architecture actuelle ;
- dépendances ;
- risques ;
- bugs potentiels ;
- prochaine étape recommandée.

---

## Tâche 2 — Créer une structure propre

Instruction :
Proposer une structure modulaire simple pour séparer interface, IA et base de données.

Fichiers probables :
- app.py
- ai_service.py
- database.py

Ne rien coder avant validation.

---

## Tâche 3 — Refactor minimal

Instruction :
Refactoriser uniquement ce qui est nécessaire pour séparer :
- appels IA ;
- base SQLite ;
- interface Streamlit.

Critère :
L’application doit fonctionner exactement comme avant.

---

## Tâche 4 — Améliorer la base de données

Ajouter à l’historique :
- type d’erreur ;
- notion ;
- temps de réponse ;
- pédagogie utilisée.

---

## Tâche 5 — Ajouter statistiques simples

Afficher :
- nombre de tentatives ;
- score moyen ;
- erreurs fréquentes ;
- notions fragiles.

---

## Tâche 6 — Ajouter typologie d’erreurs

Faire classer par l’IA :
- oubli d’étape ;
- confusion ;
- réponse vague ;
- erreur d’ordre ;
- mauvaise exception ;
- hors sujet.

---

## Tâche 7 — Ajouter moteur adaptatif simple

Créer `adaptive_engine.py`.

Premières règles :
- si score faible plusieurs fois → explication plus courte ;
- si échec sur procédure → mode étape par étape ;
- si réussite après analogie → favoriser analogies ;
- si erreur de priorité → rappeler hiérarchie des actions.

---

## Tâche 8 — Ajouter modes pédagogiques

Modes :
- logique ;
- procédural ;
- narratif ;
- analogique ;
- synthétique.

L’utilisateur peut choisir un mode.
Le système peut aussi en recommander un.

---

## Tâche 9 — Import PDF/DOCX

Ajouter :
- upload fichier ;
- extraction texte ;
- affichage aperçu ;
- stockage document.

---

## Tâche 10 — Découpage simple

Ajouter :
- découpage par paragraphes ;
- suppression espaces inutiles ;
- stockage chunks.

---

## Tâche 11 — Embeddings prototype

Ajouter embeddings avec solution simple :
- Chroma ou Qdrant local ;
- fonction `embed_text`;
- fonction `search_chunks`.

---

## Tâche 12 — RAG simple

Modifier génération de questions :
- récupérer chunks pertinents ;
- générer question depuis ces chunks ;
- citer le contexte utilisé.

---

## Tâche 13 — RAG correction

Modifier correction :
- retrouver contexte source ;
- corriger selon le document ;
- éviter les réponses inventées.

---

## Tâche 14 — Répétition espacée simple

Créer :
- prochaine date de révision ;
- priorité selon score ;
- priorité selon fréquence d’erreur.

---

## Tâche 15 — Dashboard

Afficher :
- progression ;
- erreurs ;
- thèmes fragiles ;
- pédagogies efficaces.

---

## Tâche 16 — Préparation industrialisation

Ajouter :
- Dockerfile ;
- tests ;
- logs ;
- documentation ;
- sécurité minimale.
