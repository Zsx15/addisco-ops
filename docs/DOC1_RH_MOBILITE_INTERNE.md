# DOSSIER DE MOBILITÉ INTERNE
## Vers une fonction IT / Innovation / Transformation digitale

**Guilhem [NOM] — ASCT — [Établissement / Pôle actuel]**
*Document confidentiel — Mobilité interne*

---

## 1. Contexte professionnel actuel

Je suis ASCT (Agent Service Commercial Trains) à la SNCF depuis [X] ans.
Mon quotidien est opérationnel : service client à bord, application des procédures, gestion des incidents, sécurité voyageurs.

Ce rôle m'a donné une compréhension concrète et pragmatique de ce que signifie travailler dans un environnement réglementé, sous contrainte, avec des procédures qui évoluent régulièrement et des utilisateurs (les équipes) qui doivent les assimiler rapidement.

Ce n'est pas un contexte facile à apprendre : les règles sont nombreuses, les exceptions existent, et la mémorisation passive ne suffit pas pour être réellement opérationnel.

---

## 2. Identification d'un besoin métier

En observant mon environnement professionnel, j'ai identifié un problème récurrent : **la formation aux procédures reste un exercice passif.**

Les agents reçoivent des supports, les lisent, passent un contrôle, puis oublient progressivement les détails techniques dans les semaines qui suivent — en particulier les exceptions, les cas particuliers, les conditions d'application.

Ce n'est pas un problème de motivation ou d'intelligence. C'est un problème de méthode : on apprend mieux en faisant, en étant questionné, en se trompant et en comprenant pourquoi.

Cette observation m'a amené à me poser une question simple :
> "Est-ce qu'il existerait une façon d'utiliser l'IA pour transformer un document de procédure en exercice interactif d'apprentissage ?"

---

## 3. Pourquoi l'IA et l'innovation m'ont intéressé

Je ne suis pas parti d'une fascination technologique abstraite.
Je suis parti d'un besoin concret que j'avais identifié sur le terrain.

L'IA m'a intéressé parce qu'elle offrait, pour la première fois, la possibilité de traiter un document de texte, d'en extraire le sens, de poser des questions pertinentes sur son contenu et de corriger une réponse de façon pédagogique — sans nécessiter une équipe de spécialistes pour chaque document.

Ce n'est pas de la magie. Mais c'est un changement d'échelle réel pour la formation professionnelle.

---

## 4. Démarche d'apprentissage autonome

Je n'avais aucune formation technique en informatique au départ.

J'ai commencé par comprendre les concepts de base : comment fonctionne une API, ce qu'est un modèle de langage, ce que signifie "entraîner" un système versus "interroger" un système. J'ai utilisé des ressources publiques, des documentations techniques, et des outils d'IA conversationnelle (Claude, ChatGPT) pour m'aider à progresser.

Ce que j'ai appris à cette étape :
- La différence entre un LLM (grand modèle de langage) et une base de données traditionnelle
- Ce que signifie "contexte" dans un prompt IA
- Comment structurer une requête pour obtenir un résultat exploitable
- Les limites fondamentales de l'IA générative (hallucinations, coût, latence)

Cette phase d'apprentissage a duré plusieurs semaines. J'ai pris des notes, posé des questions, recommencé quand je ne comprenais pas.

---

## 5. Construction progressive du POC

Une fois les bases comprises, j'ai décidé de construire un prototype fonctionnel pour tester mon hypothèse.

J'ai utilisé une approche que j'ai ensuite découvert s'appeler **MVP** (Minimum Viable Product) :
construire la version la plus simple possible qui permette de valider l'idée, avant d'aller plus loin.

**Comment j'ai procédé :**
J'ai coordonné des outils d'IA (Claude Code, ChatGPT) comme un chef de projet coordonne des prestataires : en définissant les besoins, en validant chaque livrable, en posant des questions sur les choix techniques, en refusant ce qui ne correspondait pas à ce que je voulais.

Le projet a évolué en **19 phases documentées**, chacune avec :
- un objectif clair
- un livrable précis
- un critère de validation
- une note dans un journal de développement (DEVLOG)

Ce que j'ai construit au fil des phases :
- Phase 1-3 : prototype basique (texte → question → correction)
- Phase 4-7 : import de documents réels (PDF, Word), recherche sémantique dans le contenu
- Phase 8-9 : moteur d'adaptation selon le niveau de l'utilisateur
- Phase 10-12 : authentification, multi-utilisateurs, rôles (apprenant / formateur / admin)
- Phase 13-16 : analytics, tableaux de bord, rapports pédagogiques
- Phase 17-18 : déploiement Docker, monitoring, simulation et calibration du moteur
- Phase 19 : corpus multi-documents, suivi de sessions, feedback utilisateur

À chaque phase, l'objectif était : **ne pas avancer sans avoir validé ce qui précède.**

---

## 6. Difficultés rencontrées

Je ne présente pas ce projet comme un parcours sans embûches.

**Difficultés techniques :**
- Comprendre pourquoi la recherche dans les documents ne donnait pas les bons résultats (problème d'embedding, résolu après plusieurs itérations)
- Gérer les erreurs silencieuses dans la base de données (comportement non visible à l'écran mais présent dans les logs)
- Comprendre la différence entre "le code tourne" et "le comportement est correct"

**Difficultés méthodologiques :**
- Résister à la tentation d'ajouter des fonctionnalités avant d'avoir stabilisé les existantes
- Apprendre à écrire des tests pour valider que quelque chose fonctionne réellement
- Accepter de revenir en arrière et de réécrire une partie plutôt que de "patcher par-dessus"

**Difficultés conceptuelles :**
- Comprendre que la qualité d'un modèle IA dépend autant de la façon dont on lui pose les questions que du modèle lui-même
- Comprendre que "disponible" ne signifie pas "fiable en production"

---

## 7. Remise en question et ajustements

Plusieurs fois au cours du projet, j'ai pris des décisions qui ont dû être revisitées.

**Exemple 1 :** J'avais initialement prévu de migrer vers une base de données PostgreSQL (plus adaptée à la production). Après analyse, j'ai décidé de différer cette migration : le prototype ne justifiait pas encore cette complexité. J'ai documenté cette décision plutôt que de la cacher.

**Exemple 2 :** J'avais sous-estimé l'importance des tests automatisés. En milieu de projet, j'ai introduit des mécanismes de vérification systématique — pas parce que quelqu'un me l'avait imposé, mais parce que j'avais vu que sans eux, chaque modification risquait de casser quelque chose ailleurs.

**Exemple 3 :** Le moteur adaptatif avait des seuils arbitraires au départ. J'ai construit un harness de simulation pour les calibrer empiriquement — c'est-à-dire les tester sur des données simulées et ajuster jusqu'à obtenir un comportement cohérent.

**Exemple 4 :** J'ai conçu un moteur de graphe de compétences (inspiré de la taxonomie de Bloom) permettant de visualiser les dépendances pédagogiques entre notions — par exemple, qu'on ne peut pas travailler "résolution de problèmes" sans avoir d'abord consolidé "compréhension de la procédure". Ce module existe et fonctionne, mais j'ai délibérément choisi de ne pas le brancher à l'interface : avec peu de données d'entraînement, les métriques affichées n'auraient pas été significatives et auraient pu induire en erreur. Ce sera utile à partir du moment où un volume suffisant de sessions réelles sera disponible.

Ce que j'ai compris : **se remettre en question n'est pas un signe d'échec. C'est une compétence.**

---

## 8. Ce que j'ai appris

**Sur la technologie :**
- Ce que sont vraiment l'IA, les embeddings, le RAG, un pipeline de données
- Comment fonctionne l'authentification sécurisée, le déploiement Docker, la CI/CD
- Ce que signifie "dette technique" et pourquoi elle se gère, pas s'ignore
- La différence entre un MVP et un produit fini

**Sur la gestion de projet :**
- L'importance de définir un critère de sortie avant de commencer une phase
- Ce qu'est une roadmap vivante : un outil de pilotage, pas un contrat figé
- Comment documenter ses décisions pour pouvoir les expliquer et les faire évoluer
- La valeur d'un journal de développement tenu à jour (DEVLOG)

**Sur moi-même :**
- Je suis capable d'apprendre seul des sujets complexes si je les aborde méthodiquement
- Je préfère comprendre avant de faire plutôt que de copier-coller sans savoir
- J'ai une capacité naturelle à décomposer un problème en sous-problèmes traitables
- Je sais remettre en question mes propres décisions sans que ce soit un blocage

---

## 9. Compétences transférables

Ce projet a développé et révélé des compétences directement transférables vers des fonctions IT / innovation :

| Compétence développée | Comment elle se manifeste |
|----------------------|--------------------------|
| **Analyse du besoin utilisateur** | Identification du problème terrain avant toute solution |
| **Logique MVP / incrémental** | 19 phases avec validation à chaque étape |
| **Gestion de projet numérique** | Roadmap, DEVLOG, critères de sortie, dépendances |
| **Compréhension technique** | Architecture, pipeline, base de données, IA — sans être développeur |
| **Documentation structurée** | ARCHITECTURE.md, ROADMAP.md, CLAUDE.md — lisibles par une équipe |
| **Gestion des risques** | Identification des dettes techniques, décisions documentées |
| **Orientation produit** | Prise en compte des rôles utilisateurs (apprenant, formateur, admin) |
| **Analytics / supervision** | Tableaux de bord, métriques, observabilité du système |
| **Communication transverse** | Capacité à expliquer des concepts techniques à des non-techniciens |

---

## 10. Ce que cette démarche révèle de mon potentiel

Ce projet révèle quelque chose que mon quotidien d'ASCT n'exprime pas facilement : **ma capacité à piloter une démarche complexe de façon autonome et structurée.**

En dehors de mes horaires de travail, sur du temps personnel, j'ai :
- identifié un problème métier réel
- formulé une hypothèse
- construit une solution progressive
- rencontré des obstacles et les ai surmontés
- documenté chaque décision
- réévalué mes choix quand la situation le demandait
- abouti à un prototype fonctionnel et démontrable

Ce n'est pas ce qu'on attend d'un ASCT. C'est ce qu'on attend d'un profil innovation / transformation.

---

## 11. Pourquoi je souhaite évoluer vers des fonctions IT / innovation

Je ne souhaite pas quitter mon métier parce qu'il ne me plaît plus.
Je souhaite évoluer parce que je sais maintenant que je peux apporter quelque chose de différent.

Ma connaissance du terrain — les procédures, les contraintes opérationnelles, la réalité des agents, les limites des outils actuels — est une ressource rare dans les équipes IT et innovation.

La plupart des projets numériques échouent non pas parce que la technologie est mauvaise, mais parce que les équipes qui la conçoivent ne comprennent pas vraiment les besoins du terrain. Je suis dans la position rare de comprendre les deux.

Je ne cherche pas à devenir développeur. Je cherche à contribuer là où cette double compréhension crée de la valeur.

La structure qui correspond le mieux à ce que j'ai construit et à ce que je veux apporter est la **Fabrique de l'Adoption Numérique (FAN)** — l'entité e.SNCF Solutions basée à Lyon dont la mission est d'accélérer l'adoption du numérique dans les équipes du Groupe, notamment via l'acculturation à l'IA générative et le déploiement des usages terrain. ADDISCO OPS est, dans sa logique, un prototype de ce que la FAN cherche à faire à grande échelle.

Au-delà de la FAN, les fonctions qui correspondent à mon profil :
- **Référent adoption numérique** : accompagner les équipes opérationnelles dans la prise en main des outils numériques, identifier les freins terrain
- **Coordinateur de projets de transformation** : faire le lien entre les besoins métier et les équipes IT, avec une ancre terrain solide
- **MOA / AMOA** : traduire les besoins terrain en spécifications — cible à moyen terme, après une montée en compétence sur les méthodes IT formelles

---

## 12. Projection professionnelle dans l'entreprise

Je me projette dans des fonctions qui permettent de faire le lien entre le terrain et le numérique.

**À court terme (0-6 mois) :**
Rejoindre une structure d'adoption numérique — en priorité la FAN (Fabrique de l'Adoption Numérique, Lyon) — en tant que référent ou coordinateur. Comprendre les projets en cours, contribuer sur des missions d'acculturation ou de déploiement d'usages IA auprès des équipes terrain.

**À moyen terme (6-18 mois) :**
Prise en charge de missions de coordination sur des projets de transformation numérique. Montée en compétence sur les méthodes IT formelles (Agile, gestion de backlog, rédaction de specs fonctionnelles).

**À long terme :**
Évoluer vers un rôle MOA / chef de projet numérique, en capitalisant sur la double compréhension opérationnelle et technique acquise et sur l'expérience terrain des projets de transformation.

---

**Ce que je demande :**
Un échange avec [la direction de la mobilité / les équipes RH] et si possible avec les équipes IT / innovation pour présenter ce projet, comprendre comment mes compétences pourraient être utiles, et envisager ensemble une trajectoire réaliste.

Je ne prétends pas être prêt immédiatement pour tout. Je prétends être prêt à apprendre vite, à contribuer rapidement, et à apporter un regard que peu de profils techniques ont.

---

*Document préparé dans le cadre d'une démarche de mobilité interne — Mai 2026*
*Guilhem [NOM] — ASCT — [Établissement]*

**Démonstration en ligne :** https://addisco-ops-production.up.railway.app
*Identifiant : `demo` — Mot de passe : `Demo2026!`*
