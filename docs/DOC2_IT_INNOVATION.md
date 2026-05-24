# ADDISCO OPS — Dossier de présentation projet
## À destination des équipes IT / Innovation / Transformation digitale

**Guilhem [NOM] — ASCT SNCF — POC personnel — Mai 2026**

> Ce document présente la démarche, les choix et les apprentissages d'un projet personnel
> conduit par un profil terrain, sans formation technique préalable, dans une logique
> d'expérimentation et de montée en compétence. Il ne prétend pas à l'exhaustivité technique.
> Il cherche à montrer une capacité de structuration, de compréhension et de pilotage.

---

## 1. Contexte métier et problématique

En tant qu'ASCT, je suis confronté régulièrement à la question de la formation aux procédures :
des documents denses, des règles nombreuses, des exceptions à mémoriser, une réalité terrain
qui nécessite une réelle assimilation — pas juste une lecture.

Le constat est simple : **les outils de formation actuels ne s'adaptent pas au niveau réel de l'apprenant.**
Tout le monde reçoit le même contenu, au même rythme. Les erreurs récurrentes ne sont pas identifiées individuellement. La mémorisation à long terme n'est pas soutenue.

Ce n'est pas un problème technologique en soi. C'est un problème de méthode pédagogique, que la technologie peut maintenant adresser différemment.

**Question de départ :**
> Un système IA peut-il transformer un document de procédure en outil d'apprentissage interactif, adaptatif et mesurable ?

---

## 2. Hypothèse de départ

Si un système peut :
1. comprendre le contenu d'un document (pas juste le lire — en saisir le sens)
2. générer des questions pertinentes sur ce contenu
3. évaluer les réponses de façon pédagogique (identifier le type d'erreur, pas juste dire "faux")
4. mémoriser les résultats et adapter les questions suivantes
5. programmer les révisions au bon moment

...alors on dispose d'un tuteur personnalisé, disponible en permanence, applicable à n'importe quel document métier.

Cette hypothèse est la colonne vertébrale du projet.

---

## 3. Vision du projet

**Ce que le projet n'est PAS :**
- Un produit fini prêt à déployer en production
- Un système développé par une équipe technique
- Une solution qui prétend remplacer la formation humaine

**Ce que le projet EST :**
- Un POC (Proof of Concept) — une démonstration de faisabilité
- Un prototype fonctionnel permettant de tester l'hypothèse de départ
- Un support d'apprentissage personnel sur les enjeux techniques et produit

**Périmètre du POC :**
- Import de documents (PDF, Word, texte)
- Génération de questions adaptatives sur le contenu
- Correction pédagogique avec identification du type d'erreur
- Suivi de la progression par utilisateur
- Tableau de bord formateur / administrateur
- Déploiement local et containerisé (Docker)

---

## 4. Méthodologie MVP

La méthode que j'ai appliquée est proche de ce qu'on appelle le développement incrémental ou la logique MVP :

**Principe :** construire le minimum qui permet de valider une hypothèse, avant d'ajouter de la complexité.

**Application concrète :**

| Phase | Ce qui a été construit | Ce qui a été validé |
|-------|----------------------|---------------------|
| 1-3 | Prototype basique (texte → question → correction) | L'IA peut générer et corriger des questions pertinentes |
| 4-7 | Import de documents réels + recherche dans le contenu | Le système trouve les passages pertinents dans un PDF |
| 8-9 | Moteur adaptatif selon le niveau de l'utilisateur | Le système ajuste les questions selon les résultats passés |
| 10-12 | Multi-utilisateurs, authentification, rôles | Le système est utilisable par plusieurs personnes avec des accès différents |
| 13-16 | Analytics, tableaux de bord, rapports | Les données d'apprentissage sont exploitables |
| 17-18 | Déploiement, monitoring, simulation | Le système est déployable et observable |
| 19 | Corpus multi-documents, suivi de sessions | L'utilisateur peut travailler sur un ensemble de documents |

À chaque phase : un objectif défini, un livrable attendu, une validation avant de passer à la suivante.
Ce n'est pas du perfectionnisme. C'est de la réduction du risque.

**Outil de pilotage :**
J'ai maintenu une roadmap vivante, un journal de développement (DEVLOG), et une documentation d'architecture mise à jour à chaque évolution significative.

---

## 5. Architecture simplifiée

Je ne prétends pas avoir conçu une architecture de niveau production.
Voici ce que j'ai compris et mis en place :

```
Utilisateur (navigateur web)
       ↓
Application (interface Streamlit — Python)
       ↓              ↓              ↓
Gestion des      Logique IA     Base de données
utilisateurs     (moteur)         (SQLite)
(auth, rôles)
       ↓
API OpenAI (génération, embeddings)
```

**Principes qui ont guidé les choix :**
- **Séparation des responsabilités** : chaque module a un rôle précis (authentification, IA, données, interface)
- **Stabilité avant évolution** : ne modifier que ce qui est nécessaire, sans refactoring massif non justifié
- **Réversibilité** : chaque choix important documenté avec la possibilité de revenir en arrière
- **Fallback** : si l'API externe tombe, l'application ne plante pas

**Limites assumées de cette architecture :**
- SQLite n'est pas adapté à de nombreux utilisateurs simultanés — PostgreSQL serait nécessaire en production
- La recherche dans les documents charge tout en mémoire — une base vectorielle dédiée serait nécessaire au-delà d'une cinquantaine de documents
- L'interface Streamlit n'est pas une interface de production grand public

Ces limites sont connues, documentées, et ne constituent pas des imprévus — elles font partie de la réalité d'un MVP.

---

## 6. Pipeline documentaire — comment l'IA "comprend" un document

C'est le cœur technique du projet, et le point qui nécessite le plus d'explication.

**Le problème à résoudre :**
Un document de 50 pages ne peut pas être envoyé entier à un modèle IA. Il faut le découper intelligemment.

**La solution mise en place (RAG — Retrieval-Augmented Generation) :**

```
Étape 1 — Découpage
Le document est découpé en sections logiques (~500 caractères chacune).
Chaque section garde son titre et son contexte.

Étape 2 — Transformation en vecteurs
Chaque section est transformée en une représentation mathématique de son sens
(un vecteur de 1 536 nombres) via l'API OpenAI.
Deux textes similaires auront des vecteurs similaires.

Étape 3 — Stockage
Ces vecteurs sont stockés en base de données avec le texte associé.

Étape 4 — Recherche
Quand l'utilisateur demande une question, le système cherche les sections
du document les plus proches du sujet demandé.
La question est alors générée à partir de ces sections précises.
```

**Ce que ça apporte :**
La question posée est ancrée dans le document réel, pas inventée par l'IA de façon générique.
C'est la différence entre un chatbot qui "hallucine" et un système qui s'appuie sur une source précise.

---

## 7. Moteur adaptatif — comment le système s'adapte à l'utilisateur

**Le problème à résoudre :**
Ne pas poser la même question deux fois. Ne pas poser une question trop difficile à quelqu'un qui vient de rater trois fois la même notion. Programmer les révisions au bon moment.

**Ce qui a été mis en place :**

**Classification de maîtrise (par section de document)**

| Niveau | Condition | Ce que le moteur fait |
|--------|-----------|----------------------|
| Fragile | Score moyen < 60% | Révision prioritaire, questions de base |
| En consolidation | Score 60-80% | Questions variées pour ancrer les acquis |
| Maîtrisé | Score > 80% ET ≥ 5 tentatives | Questions de challenge, révision espacée |

Ces seuils ont été calibrés par simulation — pas choisis arbitrairement.

**Répétition espacée**
Après chaque tentative, le système calcule le prochain moment optimal de révision :
- Section fragile → révision dans 1-2 jours
- En consolidation → 3-5 jours
- Maîtrisé → 7 jours

**Adaptation du type de question**
6 types de questions (directe, cas pratique, vrai/faux, piège, reformulation, conséquence).
Le moteur choisit selon le niveau de maîtrise et l'historique de l'utilisateur.

---

## 8. Analytics et supervision

Un système sans données de pilotage est un système aveugle.

**Ce qui est mesuré et visible :**

*Pour l'apprenant :*
- Score moyen par notion
- Progression dans le temps
- Sections fragiles prioritaires
- Prochain moment de révision conseillé

*Pour le formateur :*
- Progression par utilisateur
- Notions les plus difficiles dans l'équipe
- Temps de réponse moyen
- Types d'erreurs récurrentes

*Pour l'administrateur :*
- Usage de l'application
- Coût des appels IA (mesuré au centime)
- Taux de réussite des appels API
- Alertes système

Cette logique de supervision n'est pas accessoire. C'est ce qui transforme un outil en système pilotable.

---

## 9. QA et observabilité

Deux questions que j'ai appris à me poser systématiquement :
- "Comment je sais que ça marche ?"
- "Comment je saurai si ça arrête de marcher ?"

**Ce qui a été mis en place :**

*Vérification syntaxique* : contrôle automatique que tous les fichiers Python sont valides à chaque modification.

*Tests de régression* : des "garde-fous" qui échouent automatiquement si quelqu'un modifie par erreur un paramètre critique du moteur (les seuils de maîtrise, les intervalles de révision).

*Tests unitaires* : vérification des fonctions d'authentification.

*Simulation contrôlée* : un harness de test qui simule des séquences d'apprentissage sur une base de données temporaire, pour valider que le moteur se comporte comme attendu sans affecter les vraies données.

*Logs* : chaque appel à l'API IA est enregistré avec sa durée, son coût estimé, son résultat.

*Monitoring* : intégration d'un outil de surveillance d'erreurs en production (Sentry).

Je ne prétends pas avoir une couverture de tests complète — c'est une limite connue. Mais j'ai compris pourquoi les tests existent et j'ai intégré cette logique dans ma façon de travailler.

---

## 10. Dette technique identifiée

Un des apprentissages les plus importants de ce projet est la notion de dette technique :
les choix pragmatiques faits pour avancer vite, qui créent des fragilités à corriger plus tard.

J'ai appris à **identifier, documenter et assumer** cette dette plutôt que de la cacher :

| Dette identifiée | Impact | Correction prévue |
|-----------------|--------|------------------|
| Pas de protection anti-force brute sur le login | Risque sécurité si déployé | Rate limiting sur l'authentification |
| Recherche vectorielle en mémoire vive | Limite à ~50 documents | Base vectorielle dédiée (pgvector) |
| Une fonction interne utilise une API Python dépréciée | Alerte en Python 3.12+ | Migration en 10 lignes |
| Docstrings non mises à jour après évolution | Confusion pour un lecteur | Mise à jour documentation |
| Graphe de compétences Bloom (skill_graph.py) construit mais non branché à l'UI | Visualisation des dépendances pédagogiques absente | Branchement conditionné à un volume suffisant de données réelles (~500+ tentatives) — en dessous, les métriques par skill ne sont pas statistiquement exploitables |

La capacité à identifier et nommer ses propres dettes techniques est, à mon sens, un signe de maturité dans la gestion d'un projet numérique.

---

## 11. Limites du MVP — ce que ce prototype n'est pas

Je tiens à être explicite sur ce point, car c'est ce qui donne de la crédibilité au reste.

**Ce que ce POC ne peut pas faire :**
- Passer à l'échelle avec des centaines d'utilisateurs simultanés (architecture de base de données non adaptée)
- Fonctionner sans clé API OpenAI (dépendance externe)
- Garantir la qualité pédagogique des questions pour tous les types de documents
- Être déployé en production sans audit de sécurité complet

**Ce que cela implique pour une industrialisation :**
- Remplacement de la base de données SQLite par PostgreSQL
- Introduction d'un système de cache et d'une base vectorielle dédiée
- Tests de charge et audit sécurité
- Revue par une équipe technique qualifiée
- Validation pédagogique par des experts formation

**Pourquoi c'est important à dire :**
Un POC qui prétend être prêt pour la production n'est pas crédible.
Un POC qui identifie clairement ses limites et le chemin vers l'industrialisation est un outil de décision utile.

---

## 12. Apprentissage et progression personnelle

Ce que je retiens de ce projet en termes de compréhension des enjeux IT :

**Sur la conception produit :**
La différence entre ce que l'utilisateur demande, ce dont il a besoin, et ce qui est techniquement faisable. La valeur d'un MVP pour tester une hypothèse avant d'investir massivement.

**Sur la gestion de projet numérique :**
L'importance d'une roadmap vivante. La valeur des critères de sortie de phase. Le coût réel d'une dette technique ignorée. La nécessité de documenter pour maintenir.

**Sur l'IA appliquée :**
Ce qu'un LLM peut faire et ne peut pas faire. Ce que signifie "ancrer" une réponse IA dans une source documentaire. Les coûts, les latences, les risques de dépendance à un fournisseur externe.

**Sur la qualité logicielle :**
Ce que sont les tests, pourquoi ils existent, comment un système peut s'auto-surveiller.

---

## 13. Perspectives possibles

Ce POC a une valeur démonstrative. Il n'est pas, en l'état, un produit déployable.

**Ce qu'il pourrait devenir avec les bonnes ressources :**
- Un outil interne de formation aux procédures, adapté au contexte ferroviaire
- Un module complémentaire à des outils de formation existants
- Un terrain d'expérimentation pour des équipes IT souhaitant tester des approches RAG sur des documents métier réels

**Ce que je cherche :**
Pas à imposer ce projet. Pas à être le seul à en décider l'avenir.

Je cherche des échanges avec des équipes IT / innovation pour :
- comprendre comment ce type d'approche s'intègre (ou non) dans les projets existants
- identifier ce qui serait utile et ce qui serait inutile dans un contexte réel
- apprendre des personnes qui travaillent sur ces sujets au quotidien
- contribuer, en fonction de mes compétences actuelles et en développement

---

*Guilhem [NOM] — ASCT SNCF — Mai 2026*

**Démonstration en ligne :** https://addisco-ops-production.up.railway.app
*Identifiant : `demo` — Mot de passe : `Demo2026!`*
