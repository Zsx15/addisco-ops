# ADDISCO OPS — Présentation Candidature
## Document à destination des équipes RH et management

---

## Qui je suis — le point de départ honnête

Je viens du terrain. Pas d'école d'ingénieur, pas de bac+5 en informatique.
Mais j'ai décidé de construire quelque chose de concret plutôt que de me contenter d'une formation : un vrai produit, fonctionnel, déployable, que n'importe qui peut utiliser aujourd'hui.

Ce document explique ce que j'ai construit, pourquoi, et ce que ça dit de ce que je suis capable de faire.

---

## Le projet en une phrase

**ADDISCO OPS est une application web d'entraînement professionnel qui utilise l'intelligence artificielle pour s'adapter automatiquement au niveau et aux lacunes de chaque utilisateur.**

---

## Le problème que ça résout

Dans les entreprises, la formation repose encore largement sur des cours figés : tout le monde reçoit le même contenu, au même rythme, que l'on soit débutant ou confirmé. Résultat : les uns s'ennuient, les autres décrochent.

ADDISCO OPS part d'un principe simple : chaque personne oublie différemment et apprend différemment. L'outil s'y adapte.

---

## Comment ça marche — sans jargon

**Étape 1 — On importe les documents de l'entreprise**
Un formateur importe une procédure, un règlement, un manuel technique (PDF, Word, texte). L'application découpe ce document en sections et comprend leur contenu.

**Étape 2 — L'application génère des questions**
Plutôt que de lire passivement, l'utilisateur répond à des questions. L'IA lit le document et crée des questions variées : questions directes, cas pratiques, vrais/faux, questions pièges, reformulations. Elle évite de poser deux fois la même question.

**Étape 3 — La réponse est corrigée intelligemment**
L'IA évalue la réponse, donne un score de 0 à 100 %, explique ce qui manque, identifie le type d'erreur (oubli d'étape, confusion de notion, réponse vague…).

**Étape 4 — Le système se souvient et s'adapte**
À chaque session, l'application mémorise ce que l'utilisateur maîtrise et ce qu'il oublie. Elle programme automatiquement les révisions aux moments les plus efficaces (répétition espacée). Elle change le type de questions si l'utilisateur bloque.

**Étape 5 — Le formateur suit la progression**
Un tableau de bord permet de voir qui progresse, qui stagne, quelles notions posent problème dans l'équipe.

---

## Ce qui rend ce projet crédible techniquement

Je ne liste pas des mots-clés pour impressionner. Je liste ce que le projet fait réellement.

**Authentification sécurisée**
Les mots de passe sont chiffrés (bcrypt). Trois niveaux d'accès : apprenant, formateur, administrateur. Chaque niveau voit uniquement ce qui le concerne.

**Intelligence artificielle réelle, pas simulée**
Le projet utilise GPT-4o-mini d'OpenAI pour générer les questions et corriger les réponses, et un modèle d'embeddings (text-embedding-3-small) pour comprendre le sens des documents — pas juste les mots exacts.

**Si l'IA ne répond pas, l'appli continue de fonctionner**
Un mécanisme de secours (fallback) garantit qu'une panne de l'API OpenAI ne plante pas l'application.

**Déployable n'importe où**
L'application est conteneurisée avec Docker. Elle peut être lancée sur un serveur en une commande, sur Railway, AWS, ou n'importe quel hébergeur cloud.

**Coût maîtrisé**
Chaque appel à l'IA est mesuré et facturé au centime. Le rapport de simulation montre un coût de $0,000045 pour 45 appels, soit moins d'un centime pour une heure de formation intensive.

---

## Ce que j'ai appris en construisant ce projet

Ce projet a été développé en **20 phases documentées**, sur plusieurs mois.

Chaque phase a un objectif, un livrable, un critère de réussite. J'ai appris à planifier, à tester, à revenir en arrière quand quelque chose ne fonctionnait pas, et à documenter mes décisions pour pouvoir les expliquer.

J'ai appris à :
- Lire une documentation technique en anglais et en appliquer les concepts
- Identifier les risques d'une modification avant de la faire
- Tester ce que j'ai construit au lieu d'espérer que ça marche
- Faire évoluer un projet sans casser ce qui existait déjà

---

## Ce que ce projet dit de ma façon de travailler

**Je finis ce que je commence.**
20 phases. Plus de 36 tâches majeures répertoriées et soldées. Un DEVLOG (journal de développement) tenu à jour.

**Je comprends les contraintes avant de coder.**
Avant chaque modification, je lisais la documentation d'architecture. J'ai évité plusieurs désastres grâce à ça.

**Je pense à l'utilisateur final.**
L'application a un mode démo, un mode présentation (pour les réunions), des messages d'erreur clairs, un dashboard apprenant, un dashboard formateur, un dashboard admin. Ce n'est pas juste du code qui tourne : c'est un produit.

**Je n'ai pas peur de l'inconnu.**
J'ai affronté des sujets que je ne connaissais pas (algorithmes de répétition espacée, embeddings vectoriels, authentification bcrypt, Docker, CI/CD). Je les ai appris parce que le projet en avait besoin.

---

## Ce que je cherche

Un poste de **développeur junior Python / développeur IA** dans une équipe qui travaille sur des projets à impact réel.

Je ne cherche pas à être autonome immédiatement sur tout — je cherche à contribuer vite sur ce que je maîtrise (Python, IA, SQLite, Docker) tout en apprenant ce que je ne connais pas encore (travail en équipe à grande échelle, conventions d'une codebase partagée, code review en binôme).

Je ne prétends pas tout savoir. Je prétends savoir apprendre vite, travailler sérieusement, et ne pas lâcher.

---

## Mon ancrage terrain — ce que l'école ne donne pas

Mon expérience terrain n'est pas une parenthèse à effacer. C'est ce qui m'a donné l'idée de ce projet et ce qui me permet de comprendre le problème que je résous.

Sur le terrain, j'ai vu ce que c'est d'arriver sur un poste avec un manuel de 80 pages et 2 semaines pour être opérationnel. J'ai vu des équipes apprendre par cœur sans vraiment comprendre, et oublier en 3 semaines ce qu'elles avaient mis 2 semaines à mémoriser.

ADDISCO OPS vient de là. Pas d'un cours d'informatique. D'une observation réelle d'un problème réel.

Ce double ancrage — technique et métier — est rare pour un profil junior. Il me permet de poser des questions différentes : pas juste "comment coder ça" mais "pourquoi ça doit fonctionner comme ça".

---

## Pour aller plus loin

- **Démonstration live disponible** — l'application tourne, je peux la montrer à distance ou en présentiel en 5 minutes
- **Code source consultable** — github.com ou envoi direct sur demande
- **Documentation technique complète** — ARCHITECTURE.md, ROADMAP.md, DEVLOG.md disponibles
- **Rapport de simulation inclus** — résultats du moteur sur 20 sessions de test avec métriques complètes

---

*Guilhem — Mai 2026*
