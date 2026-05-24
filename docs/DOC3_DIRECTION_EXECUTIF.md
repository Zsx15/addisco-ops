# ADDISCO OPS — Note de présentation
## À destination de la direction / du sponsor exécutif

**Guilhem [NOM] — ASCT — Mai 2026**
*Support de 5 slides — Version texte*

---

---

# SLIDE 1 — LE PROBLÈME MÉTIER

## "Nos agents connaissent les procédures. Mais les maîtrisent-ils vraiment ?"

---

**La réalité terrain :**

La formation aux procédures repose principalement sur des supports statiques : des documents à lire, des formations en présentiel, des contrôles ponctuels.

Ce modèle a une limite connue :
**on mémorise pour le contrôle. On oublie dans les semaines qui suivent.**

Les erreurs de procédure ne viennent pas toujours d'un manque de motivation.
Elles viennent souvent d'une **assimilation incomplète** que les outils actuels ne détectent pas.

---

**La question :**

> Existe-t-il une façon de personnaliser l'apprentissage des procédures — de s'adapter au niveau réel de chaque agent, d'identifier ses lacunes, et de programmer les révisions au bon moment ?

---

**Ce que ça représente comme enjeu :**
- Réduction des erreurs procédurales
- Montée en compétence plus rapide des nouvelles recrues
- Traçabilité de la maîtrise par agent et par notion
- Formation continue sans mobilisation permanente de formateurs

---

---

# SLIDE 2 — L'HYPOTHÈSE IA

## "Et si l'IA pouvait transformer n'importe quel document en tuteur personnalisé ?"

---

**L'idée de départ :**

Les modèles d'IA actuels sont capables de :
- lire et comprendre le sens d'un document (pas juste ses mots)
- générer des questions pertinentes sur ce contenu
- évaluer une réponse et expliquer ce qui manque
- s'adapter au niveau de chaque utilisateur

Ces capacités, combinées, permettent de construire quelque chose de nouveau :
**un système qui transforme un document de procédure en exercice interactif, adaptatif et traçable.**

---

**La différence avec un quiz classique :**

| Quiz classique | Système adaptatif |
|---------------|------------------|
| Questions identiques pour tous | Questions adaptées au niveau de chaque agent |
| Résultat binaire (juste / faux) | Identification du type d'erreur |
| Pas de mémoire | Mémorisation des lacunes, révision programmée |
| Statique | Évolue avec l'utilisateur |

---

**Ce que j'ai voulu tester :**
> Cette hypothèse est-elle techniquement réalisable, à coût raisonnable, pour un cas d'usage métier réel ?

---

---

# SLIDE 3 — LE POC DÉVELOPPÉ

## "J'ai construit un prototype pour tester cette hypothèse — de façon autonome, structurée, sur plusieurs mois."

---

**Ce qui a été construit :**

ADDISCO OPS est une application web fonctionnelle qui permet à un formateur d'importer un document de procédure, et à un apprenant de s'entraîner dessus de façon adaptative.

**Ce que le prototype fait réellement :**
- Import de documents PDF, Word, texte
- Génération de questions variées sur le contenu réel du document (pas des questions génériques)
- Correction pédagogique avec identification du type d'erreur
- Adaptation des questions selon les résultats passés de l'apprenant
- Programmation automatique des révisions selon le niveau de maîtrise
- Tableau de bord formateur et administrateur
- Déploiement possible sur n'importe quel serveur

**Comment j'ai procédé :**

En coordonnant des outils d'IA (Claude, ChatGPT) dans une logique de chef de projet :
définir les besoins, valider les livrables, comprendre les choix techniques, documenter chaque décision.
19 phases progressives sur 3 semaines de sprint intensif (~80 heures), avec une philosophie simple :
> avancer par petits bouts, consolider, vérifier, puis évoluer.

**Ce que ce POC n'est pas :**
Un produit prêt à déployer. Une architecture de production. Un travail d'équipe technique.
C'est une **démonstration de faisabilité et un support de montée en compétence.**

**Un exemple de décision technique assumée :**
Un module de visualisation des compétences (graphe de dépendances pédagogiques, inspiré de la taxonomie de Bloom) a été conçu et fonctionne en arrière-plan. Il n'est pas encore affiché : avec peu de données d'entraînement, les indicateurs n'auraient pas été fiables. Ce type de fonctionnalité devient pertinent à partir d'un volume réel d'utilisation — c'est une décision de priorisation, pas une limite technique.

---

---

# SLIDE 4 — CE QUE CELA DÉMONTRE

## "Ce projet n'est pas la finalité. C'est la démonstration d'un potentiel de transition."

---

**Ce que cette démarche révèle — en termes de compétences :**

| Compétence démontrée | Ce que ça signifie concrètement |
|---------------------|--------------------------------|
| Identification d'un besoin métier | Je pars du terrain, pas de la technologie |
| Structuration en phases / MVP | Je sais décomposer un problème complexe |
| Documentation rigoureuse | Je produis ce qu'une équipe peut reprendre |
| Compréhension des limites | Je ne survends pas — je suis réaliste |
| Apprentissage autonome et rapide | Je suis parti de zéro sur des sujets complexes |
| Gestion de la dette technique | Je sais identifier les risques et les nommer |
| Vision produit | Je pense à l'utilisateur final, pas au code |
| Posture d'amélioration continue | Je remets en question mes propres choix |

---

**Ce que mon profil représente de rare :**

La plupart des profils IT ne connaissent pas le terrain.
La plupart des profils terrain ne parlent pas le langage des projets numériques.

Je suis dans la position de comprendre les deux — et d'avoir prouvé que je peux apprendre ce qui me manque.

**Ce que je ne suis pas :**
- Un développeur
- Un expert IA
- Un "visionnaire" qui veut tout révolutionner

**Ce que je suis :**
- Un profil terrain avec une compréhension concrète des enjeux numériques
- Quelqu'un qui structure, documente et pilote une démarche complexe
- Un candidat à la transition, pas à la révolution

---

---

# SLIDE 5 — CE QUE JE SOUHAITE MAINTENANT

## "Je ne demande pas un poste. Je demande une conversation."

---

**Ma demande est simple :**

Trois choses, dans l'ordre :

**1. Échanger avec la FAN — Fabrique de l'Adoption Numérique**
La mission de la FAN — acculturation au numérique, déploiement des usages IA, transformation des besoins terrain en valeur mesurable — est exactement ce qu'ADDISCO OPS adresse à petite échelle. Je veux comprendre comment ce type de profil peut contribuer à leurs projets en cours.

**2. Continuer à monter en compétence**
Je suis prêt à suivre des formations, à prendre des missions en appui, à contribuer sur des projets existants dans un rôle d'apprentissage actif.

**3. Contribuer à des projets de transformation**
Pas en solo. En équipe. Avec des personnes qui savent ce que je ne sais pas encore.

---

**Les fonctions vers lesquelles je me projette :**
- **Référent adoption numérique / coordinateur FAN** — cible prioritaire, connexion directe avec ADDISCO OPS et la mission d'acculturation terrain
- **Coordinateur de projets de transformation digitale** — faire le lien entre besoins métier et équipes IT
- **MOA / AMOA** — cible à moyen terme, après montée en compétence sur les méthodes IT formelles

---

**Ce que je propose :**
- Une démonstration live du prototype (30 minutes)
- Une présentation de la démarche projet complète
- Un échange sur les projets en cours et les besoins identifiés

---

> Je ne prétends pas avoir toutes les réponses.
> Je prétends avoir montré que je sais chercher, structurer, apprendre et livrer.
> C'est ce que je mets à disposition.

---

*Guilhem [NOM] — ASCT — [Établissement] — Mai 2026*
*Contact : marcelino.guilhem@gmail.com*

**Démonstration en ligne :** https://addisco-ops-production.up.railway.app
*Identifiant : `demo` — Mot de passe : `Demo2026!`*

---

---

# NOTES DE POSTURE ORALE
## Conseils pour la présentation de ce support

**Pour la slide 1 (Le problème) :**
Ne commence pas par toi. Commence par le problème.
Si tu connais des chiffres sur les erreurs procédurales ou sur les coûts de formation — cite-les.
Demande à l'auditoire : "Est-ce que ce constat vous parle ?"
Le but est que ton interlocuteur se reconnaisse dans le problème avant même que tu parles de ta solution.

**Pour la slide 2 (L'hypothèse) :**
N'entre pas dans la technique. Reste au niveau de l'idée.
Si on te demande comment ça marche techniquement, réponds :
> "Je peux vous montrer en détail si vous souhaitez aller plus loin — là je voulais d'abord partager l'idée de fond."

**Pour la slide 3 (Le POC) :**
Sois transparent sur le fait que tu as utilisé l'IA pour construire.
Dis-le clairement, avant qu'on te le demande :
> "J'ai coordonné des outils d'IA — Claude et ChatGPT — pour construire ce prototype.
> Je n'ai pas de formation de développeur. Ce que j'ai fait, c'est piloter la démarche :
> définir les besoins, valider les résultats, documenter les choix, comprendre les limites."
Cette honnêteté est un atout. Elle montre que tu comprends tes propres limites.

**Pour la slide 4 (Ce que ça démontre) :**
Ne te survends pas. Laisse le tableau parler.
Si ton interlocuteur semble dubitatif, pose une question :
> "Quelles compétences vous semblent prioritaires pour les projets sur lesquels vous travaillez ?"
Ça oriente la conversation vers ses besoins réels.

**Pour la slide 5 (Ce que je souhaite) :**
Ne finis pas par "voilà, voilà". Finis par une question ouverte :
> "Est-ce que vous avez des projets en cours où ce type de profil pourrait être utile ?"
ou
> "Qu'est-ce qui vous a le plus surpris dans ce que vous venez de voir ?"

**À éviter en toutes circonstances :**
- "Je suis passionné par l'IA" (trop entendu, trop vague)
- "Je veux révolutionner la formation" (trop grand, peu crédible)
- "Je peux tout faire" (personne ne te croira)
- Répondre longuement à une question technique (si tu ne sais pas, dis-le simplement)

**Ton positionnement en une phrase si on t'en demande une :**
> "Je suis quelqu'un du terrain qui a compris comment fonctionne un projet numérique
> en en construisant un — et qui cherche maintenant à mettre cette compréhension
> au service de projets réels, en équipe."
