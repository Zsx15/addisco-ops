\# TASK MASTER — AI Révision Métier



\## Rôle



Ce fichier définit :

\- la gouvernance du projet ;

\- les règles de développement ;

\- le workflow Claude Code ;

\- les contraintes d’architecture ;

\- les validations obligatoires ;

\- la stratégie d’évolution du projet.



Le projet doit rester :

\- modulaire ;

\- stable ;

\- explicable ;

\- incrémental ;

\- maintenable.



\---



\# Philosophie globale



Le projet évolue :

\- par petites étapes ;

\- avec validation continue ;

\- sans casser le MVP ;

\- avec dette technique minimale.



Priorité absolue :

préserver la stabilité et la compréhension humaine du projet.



\---



\# Workflow obligatoire Claude Code



\## 1. Analyse



Avant toute modification :

\- lire les fichiers concernés ;

\- comprendre le pipeline actuel ;

\- identifier les dépendances ;

\- identifier les impacts potentiels.



\---



\## 2. Planification



Toujours proposer avant modifier :

\- les fichiers concernés ;

\- les modifications prévues ;

\- les risques potentiels ;

\- les tests nécessaires.



Aucune modification importante sans validation explicite.



\---



\## 3. Implémentation



Règles :

\- limiter le nombre de fichiers modifiés ;

\- éviter les changements massifs ;

\- préserver la rétrocompatibilité ;

\- préserver les fallbacks existants ;

\- éviter les dépendances inutiles.



\---



\## 4. Vérifications obligatoires



Toujours tester :

\- imports Python ;

\- py\_compile ;

\- lancement Streamlit ;

\- fallback texte brut ;

\- retrieval ;

\- compatibilité SQLite ;

\- non-régression pipeline.



\---



\## 5. Résumé final



Après chaque modification :

\- résumer les fichiers modifiés ;

\- expliquer la logique ajoutée ;

\- préciser les impacts ;

\- préciser les risques restants ;

\- recommander la prochaine étape logique.



\---



\## 6. Git



Chaque évolution importante doit être :

\- commitée ;

\- descriptive ;

\- isolée ;

\- réversible.



Format commits :

\- feat:

\- fix:

\- docs:

\- refactor:

\- qa:



\---



\# Règles absolues



\## Ne jamais casser le MVP



Le projet doit toujours :

\- rester lançable ;

\- rester démontrable ;

\- conserver un mode fonctionnel minimal.



\---



\## Ne jamais casser le fallback



Si :

\- embeddings ;

\- retrieval ;

\- API ;

\- RAG ;



échouent :



le système doit revenir automatiquement au mode texte brut.



\---



\## Préserver les IDs stables



Éviter :

\- DELETE + INSERT.



Privilégier :

\- UPDATE ciblés.



Les relations futures :

\- attempts.chunk\_id

\- mémoire pédagogique

\- analytics



dépendront de cette stabilité.



\---



\## Ne jamais supprimer sans validation



Interdiction sans accord explicite :

\- suppression DB ;

\- suppression embeddings ;

\- suppression historique ;

\- suppression documents ;

\- reset massif.



\---



\# Architecture actuelle



\## Pipeline documentaire



Document

→ extraction texte

→ chunking

→ embeddings

→ stockage SQLite.



\---



\## Pipeline retrieval



Question

→ embedding requête

→ recherche sémantique

→ top-k chunks

→ contexte enrichi.



\---



\## Pipeline IA



Contexte

→ génération question

→ réponse utilisateur

→ correction

→ scoring

→ historique.



\---



\# Architecture future



\## Phase 1 — RAG documentaire

✔ déjà en place



Fonctions :

\- retrieval ;

\- embeddings ;

\- génération contextualisée ;

\- reindexation.



\---



\## Phase 2 — Tracking pédagogique



Objectif :

lier les erreurs utilisateur aux chunks source.



Prochaine priorité :

attempts.chunk\_id



\---



\## Phase 3 — Mémoire pédagogique



Objectifs :

\- error\_patterns ;

\- notions faibles ;

\- stabilité mémoire ;

\- répétition espacée.



\---



\## Phase 4 — Adaptation cognitive



Objectifs :

\- difficulté adaptative ;

\- reformulations intelligentes ;

\- profils apprentissage ;

\- adaptation pédagogique.



\---



\# Politique technique



\## Priorité actuelle



Stabiliser :

\- gouvernance ;

\- RAG ;

\- tracking pédagogique ;

\- structure projet.



\---



\## Non prioritaires actuellement



Ne pas implémenter maintenant :

\- multi-agent complexe ;

\- Kubernetes ;

\- vector DB externe ;

\- fine tuning ;

\- orchestration autonome massive ;

\- sur-ingénierie.



SQLite + numpy restent suffisants pour le MVP actuel.



\---



\# Politique documentation



Chaque fichier possède un rôle précis :



\## CLAUDE.md

Règles runtime Claude Code.



\## BRD.md

Vision business et métier.



\## PRD.md

Fonctionnalités produit.



\## ARCHITECTURE.md

Pipelines techniques.



\## RAG\_SPEC.md

Embeddings et retrieval.



\## TASK\_MASTER.md

Gouvernance développement.



\---



\# Vision long terme



Le projet vise à devenir :

\- une plateforme pédagogique IA ;

\- un moteur de révision adaptatif ;

\- une mémoire métier intelligente ;

\- un système de consolidation cognitive basé sur les erreurs et l’apprentissage utilisateur.

