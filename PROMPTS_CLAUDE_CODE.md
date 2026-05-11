# PROMPTS PRÊTS À COPIER DANS CLAUDE CODE

## 1. Prompt de démarrage absolu

```text
Lis les fichiers suivants comme contexte projet :
- CLAUDE.md
- README.md
- ROADMAP.md
- ARCHITECTURE.md
- TASKS.md

Analyse ensuite le projet actuel.

Important :
- ne modifie aucun fichier ;
- ne crée aucun fichier ;
- ne lance aucun refactor ;
- donne uniquement ton analyse.

Je veux :
1. résumé de l’architecture actuelle ;
2. fichiers importants ;
3. dépendances détectées ;
4. fonctionnalités déjà présentes ;
5. problèmes ou risques ;
6. écart avec la roadmap ;
7. prochaine tâche recommandée ;
8. plan d’action précis pour la tâche suivante.
```

## 2. Prompt pour implémenter une tâche

```text
Implémente uniquement la tâche suivante : [NOM DE LA TÂCHE].

Contraintes :
- respecte CLAUDE.md ;
- ne modifie que les fichiers nécessaires ;
- conserve les fonctionnalités existantes ;
- explique chaque modification ;
- donne la commande de test ;
- indique les risques restants.
```

## 3. Prompt de refactor sécurisé

```text
Refactorise cette partie du projet de manière minimale.

Objectifs :
- améliorer la lisibilité ;
- séparer les responsabilités ;
- ne pas changer le comportement ;
- ne pas casser l’application.

Avant de modifier :
1. liste les fichiers concernés ;
2. explique le plan ;
3. attends validation.
```

## 4. Prompt de correction de bug

```text
Voici l’erreur rencontrée :

[COLLER ERREUR]

Analyse sans modifier.
Donne :
1. cause probable ;
2. fichier concerné ;
3. correction proposée ;
4. test à effectuer ;
5. risques éventuels.
```

## 5. Prompt pour RAG

```text
Je veux ajouter une première version RAG.

Objectif :
- découper les documents en chunks ;
- générer des embeddings ;
- rechercher les chunks pertinents ;
- utiliser ces chunks pour générer questions et corrections.

Avant de coder :
1. propose une architecture simple ;
2. recommande une base vectorielle pour prototype ;
3. liste les fichiers à créer ;
4. propose un plan étape par étape ;
5. attends validation.
```

## 6. Prompt apprentissage adaptatif

```text
Je veux ajouter un moteur d’apprentissage adaptatif simple.

Objectif :
- suivre les erreurs ;
- suivre les modes pédagogiques ;
- détecter les formes d’explication efficaces ;
- adapter la prochaine reformulation.

Ne fais pas de diagnostic médical.
Le système doit seulement mesurer l’efficacité pédagogique.

Avant de coder :
1. propose les données à stocker ;
2. propose les règles heuristiques ;
3. propose la structure du module adaptive_engine.py ;
4. attends validation.
```

## 7. Prompt de revue qualité

```text
Fais une revue qualité du projet.

Vérifie :
- lisibilité ;
- duplication ;
- sécurité ;
- gestion des erreurs ;
- cohérence architecture ;
- dette technique ;
- prochaines améliorations.

Ne modifie aucun fichier.
```
