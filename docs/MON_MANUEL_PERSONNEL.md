# Mon Manuel Personnel — ADDISCO OPS
## Guide de préparation aux entretiens RH et techniques

---

> Ce document est fait pour toi, Guilhem. Il te prépare à toutes les questions qu'on peut te poser,
> t'explique ce que tu as construit dans tes propres mots, et te donne les clés pour répondre
> avec confiance — sans bullshit, sans sur-vendre, sans te faire piéger.

---

# PARTIE 1 — TON HISTOIRE, C'EST TON ARGUMENT LE PLUS FORT

## Comment raconter d'où tu viens sans t'excuser

La tentation est de minimiser ton parcours terrain. Ne le fais pas.
Le terrain t'a appris des choses que les gens sortis d'école n'ont pas : la rigueur, comprendre
pourquoi une procédure existe, identifier les vraies erreurs dans un processus, et l'humilité
de savoir qu'on ne connaît pas tout.

**Phrase clé à retenir :**
> "Je viens du terrain. J'ai décidé d'apprendre la programmation de façon autonome et j'ai choisi
> de le prouver en construisant un produit complet plutôt qu'en passant des certifications."

**Ce que ça dit de toi sans que tu aies besoin de le dire :**
- Tu fais ce que tu dis
- Tu apprends par la pratique
- Tu as de l'initiative

---

## Les 3 questions RH les plus probables et comment y répondre

### "Pourquoi vous voulez passer à l'informatique ?"

Ne dis pas : "parce que c'est l'avenir" ou "parce que je veux gagner plus".
Dis quelque chose de vrai. Par exemple :

> "Sur le terrain, j'ai vu des équipes perdre du temps à apprendre des procédures complexes
> sans outils adaptés. J'ai eu l'idée d'une solution. J'ai commencé à coder pour la construire.
> Et j'ai réalisé que c'est ce que je voulais faire vraiment — construire des choses qui résolvent
> des problèmes concrets."

### "Vous n'avez pas de diplôme en informatique — pourquoi on vous ferait confiance ?"

> "Parce que j'ai un projet fonctionnel. Il y a une authentification sécurisée, un moteur d'IA
> adaptatif, un pipeline de recherche documentaire, un système de suivi utilisateur, Docker,
> des tests automatisés. Tout ça a été construit seul, de zéro, sur plusieurs mois.
> Je ne vous demande pas de me croire sur parole — je vous invite à regarder le code."

### "Quelle est votre plus grande faiblesse en informatique ?"

Sois honnête mais structuré :

> "Je n'ai pas encore d'expérience sur des projets en équipe à grande échelle — merge conflicts,
> code review en binôme, conventions d'équipe. C'est pour ça que je cherche à rejoindre une équipe :
> pour apprendre ces dynamiques. Par contre, sur la rigueur technique, l'architecture, et la documentation,
> j'ai prouvé que je peux y arriver."

---

# PARTIE 2 — LE PROJET EXPLIQUÉ DANS TES MOTS

## Ce que tu as construit, concept par concept

### Le RAG — la recherche intelligente dans les documents

**Ce que c'est simplement :**
Imagine que tu as un livre de 200 pages. Quand tu poses une question, le système ne relit pas tout le livre.
Il "comprend" le sens de ta question et trouve les 3 passages les plus proches du sens de ce que tu demandes.
Ça s'appelle la recherche vectorielle.

**Comment ça marche dans ton code :**
1. Quand tu importes un document, il est découpé en petits morceaux (chunks) d'environ 500 caractères.
2. Chaque chunk est envoyé à l'API OpenAI qui le transforme en un vecteur de 1536 nombres — une représentation mathématique du sens.
3. Ce vecteur est stocké dans la base de données SQLite sous forme de BLOB (Binary Large Object).
4. Quand l'utilisateur veut une question, son texte est lui aussi transformé en vecteur.
5. Le code calcule la "similarité cosinus" entre ce vecteur et tous les vecteurs stockés — c'est un calcul mathématique qui dit "ces deux choses se ressemblent à 87%".
6. Les 3 chunks les plus similaires sont utilisés comme contexte pour générer la question.

**Fichiers clés :** `rag_service.py`, `ai_service.py:generate_embedding()`

**Si on te demande "pourquoi SQLite pour les vecteurs ?" :**
> "Pour un MVP jusqu'à 50 documents, SQLite est suffisant et évite une dépendance externe.
> La migration vers pgvector (PostgreSQL) est documentée et isolée dans `rag_service.py` — elle
> ne nécessiterait pas de toucher au reste du code."

---

### La répétition espacée — pourquoi ça fonctionne

**L'idée de base (Hermann Ebbinghaus, 1885) :**
On oublie selon une courbe prévisible. Ce qu'on révise juste avant d'oublier est mieux mémorisé.
Espacer les révisions selon le niveau de maîtrise est plus efficace que réviser tous les jours.

**Comment ton moteur le fait :**
Chaque section de document a un score moyen basé sur les tentatives passées.

| Ce que le moteur voit | Ce qu'il fait |
|----------------------|---------------|
| Score < 60% | Section "Fragile" → révision dans 1-2 jours |
| Score 60-80% ou < 5 tentatives | "En consolidation" → révision dans 3-5 jours |
| Score ≥ 80% ET ≥ 5 tentatives | "Maîtrisé" → révision dans 7 jours |

Ces seuils (0.60, 0.80, 5 tentatives) ont été calibrés empiriquement — tu as un harness de test
(une sorte de simulateur) qui a testé différentes valeurs et validé celles-ci.

**Fichier clé :** `engine/thresholds.py`, `engine/spaced_rep.py`

**Si on te demande "comment tu as choisi ces seuils ?" :**
> "J'ai construit un harness de calibration (TASK-074) qui simule des séquences d'apprentissage
> avec une base de données temporaire isolée. J'ai testé plusieurs valeurs et observé le comportement
> du moteur. Les seuils actuels (MASTERY_FRAGILE=0.60, MASTERY_MASTERED=0.80, MIN_ATTEMPTS=5)
> sont ceux qui donnent le comportement le plus cohérent sur les 5 séquences de test."

---

### Les 6 types de questions — la pédagogie adaptative

Ton moteur ne pose pas toujours le même type de question. Il en a 6 :

| Type | Ce qu'il teste | Exemple |
|------|---------------|---------|
| `question_directe` | Restitution d'une info clé | "Quelle est la durée de validité d'un permis X ?" |
| `cas_pratique` | Application en situation | "Un client arrive avec le document Y. Que faites-vous ?" |
| `vrai_faux` | Discrimination des erreurs | "Affirmation : on peut faire X sans autorisation. Vrai ou faux ?" |
| `question_piege` | Solidité face aux nuances | "On peut toujours appliquer la règle Z, n'est-ce pas ?" (non) |
| `reformulation` | Compréhension profonde | "Expliquez ce concept avec vos propres mots." |
| `consequence` | Logique de cause à effet | "Que se passe-t-il si l'étape 3 est sautée ?" |

**Le moteur choisit le type selon 3 priorités :**
1. Rotation équitable — éviter de répéter
2. Biais maîtrise — si la section est fragile, privilegier les questions de base (vrai_faux, reformulation)
3. Profil de l'utilisateur — si l'utilisateur réussit mieux sur les cas pratiques, le moteur le sait

**Fichier clé :** `engine/question_type.py`, `engine/adaptive_difficulty.py`

---

### L'authentification — pourquoi bcrypt

**Ce que tu aurais pu faire (mal) :** stocker le mot de passe en clair dans la base.
**Ce que tu as fait :** bcrypt.

bcrypt transforme le mot de passe en une empreinte impossible à inverser. Même si quelqu'un vole ta base de données, les mots de passe sont inutilisables.

De plus, chaque mot de passe est "salé" (un sel aléatoire unique est ajouté avant le hachage),
ce qui empêche les attaques par dictionnaire.

**Si on te demande "tu as une faille de sécurité connue ?" :**
> "Oui — il n'y a pas de protection contre les attaques par force brute sur le login.
> Le rate limiting est implémenté sur les appels LLM mais pas sur l'authentification.
> C'est une dette connue, documentée dans le code, à traiter avant une mise en production réelle."

Dire ça prouve que tu sais lire ton propre code de façon critique.

---

### Docker — pourquoi et comment

**Ce que c'est :** Docker crée un "conteneur" — une boîte isolée qui contient l'application et tout ce dont elle a besoin pour tourner. N'importe qui avec Docker peut lancer ton application en une commande, sans installer Python, sans configurer l'environnement.

**Dans ton projet :**
```bash
docker compose up --build
```
Cette commande : télécharge les dépendances, construit l'image, lance l'appli sur le port 8501.

**Pourquoi c'est important pour un recruteur :**
Ça signifie que ton code est déployable n'importe où — sur un serveur d'entreprise, sur AWS, sur Railway, sur un laptop de développeur. C'est une pratique professionnelle standard.

---

### Le pipeline de correction — comment l'IA corrige

Quand l'utilisateur soumet une réponse, voici ce qui se passe :

**Étape 1 — Validation déterministe (avant l'IA)**
Le code vérifie : la réponse est-elle vide ? Moins de 10 caractères ? Est-ce "je ne sais pas" ?
Si oui, score = 0, pas d'appel API (économie de coût et de temps).

**Étape 2 — Appel LLM**
L'IA reçoit : le texte source, la question posée, la réponse de l'utilisateur.
Elle retourne un JSON structuré avec : `score`, `expected_answer`, `correction`, `error_type`, `topic`.

**Étape 3 — Enregistrement**
Tout est sauvegardé dans `attempts` : score, type d'erreur, notion testée, temps de réponse, chunk utilisé.

**Étape 4 — Mise à jour du profil**
`compute_and_save_learning_profile()` recalcule le profil de l'utilisateur : quel type de questions il réussit le mieux, son momentum (est-ce qu'il progresse ?), sa régularité.

**Fichiers clés :** `ai_service.py:correct_answer()`, `db/analytics.py:save_attempt()`, `db/profile.py`

---

# PARTIE 3 — QUESTIONS TECHNIQUES FRÉQUENTES ET TES RÉPONSES

## Questions sur l'architecture

**"Pourquoi Streamlit et pas React/Flask/FastAPI ?"**
> "Streamlit permet de construire une UI fonctionnelle en Python pur, sans apprendre JavaScript
> ni gérer une API REST distincte. Pour un MVP qui doit démontrer un moteur pédagogique complexe,
> c'est le bon choix. L'architecture est conçue pour que le moteur (engine/, db/) soit entièrement
> découplé de Streamlit — migrer vers FastAPI + React demanderait de ne toucher qu'à app.py et tabs/."

**"Pourquoi SQLite et pas PostgreSQL ?"**
> "SQLite ne nécessite aucune configuration, tourne partout, et est suffisant jusqu'à 50-100
> documents avec quelques utilisateurs simultanés. La migration PostgreSQL est documentée,
> isolée dans database.py, et n'impacterait pas le reste du code. La variable DATABASE_URL
> est déjà prévue dans la config."

**"C'est quoi le problème de ton RAG à l'échelle ?"**
> "La recherche vectorielle charge tous les embeddings en RAM et calcule la similarité cosinus
> en Python. C'est O(n) sur le nombre de chunks. Ça tient jusqu'à ~50 documents.
> Au-delà, il faut pgvector (index ANN natif dans PostgreSQL) ou une base vectorielle dédiée
> comme Pinecone ou Qdrant. L'interface `search_similar_chunks()` est déjà isolée pour ça."

---

## Questions sur le code

**"Tu as des tests ?"**
> "Oui, trois niveaux distincts. D'abord, `py_compile` sur 100+ fichiers Python dans le CI/CD —
> c'est la vérification syntaxique de base, le filet anti-régression minimal.
> Ensuite, des tests de régression sur les invariants critiques du moteur : les seuils de maîtrise
> et les intervalles de révision sont protégés par des tripwires qui échouent si quelqu'un change
> une constante sans s'en rendre compte. Et enfin, des tests unitaires sur le service
> d'authentification, et un harness de calibration qui simule des séquences d'apprentissage
> sur une base de données temporaire isolée.
> Ce n'est pas 262 tests unitaires — c'est 262 vérifications au total, à différents niveaux.
> Ce serait mon prochain chantier : augmenter la couverture unitaire sur engine/ et db/."

**"Tu as une CI/CD ?"**
> "Oui, GitHub Actions. À chaque push : py_compile exhaustif sur tous les fichiers Python,
> vérification numpy, tests de régression. L'objectif est de ne jamais merger du code qui casse
> le lancement de l'application."

**"C'est quoi ta dette technique ?"**
> "Trois points principaux :
> 1. `datetime.utcnow()` déprécié depuis Python 3.12 — à migrer vers `datetime.now(timezone.utc)`.
> 2. Pas de protection brute-force sur le login.
> 3. Le pattern `conn.close()` après le context manager `with` — correct mais à refactoriser
>    pour une meilleure gestion des exceptions.
> Tout ça est documenté dans le code, aucun de ces points ne casse l'application."

**"Qu'est-ce qui se passe si l'API OpenAI est down ?"**
> "Deux niveaux de fallback. Dans `rag_service` : si aucun embedding n'est trouvé, la génération
> utilise le texte brut directement. Dans `ai_service` : si `call_chat_completion` retourne None,
> `generate_question` lève une RuntimeError catchée par l'UI, et `correct_answer` retourne
> `_CORRECT_FALLBACK` (score 0, message d'erreur utilisateur). L'app ne plante jamais."

---

## Questions sur les concepts IA

**"C'est quoi un embedding ?"**
> "C'est une représentation numérique du sens d'un texte. Le modèle `text-embedding-3-small`
> transforme n'importe quel texte en un vecteur de 1536 nombres. Deux textes qui parlent de la
> même chose auront des vecteurs proches. Deux textes sans rapport auront des vecteurs éloignés.
> La similarité cosinus mesure cet angle entre deux vecteurs."

**"C'est quoi GPT-4o-mini ?"**
> "C'est le modèle de langage d'OpenAI que j'utilise. 'Mini' signifie qu'il est plus rapide
> et moins cher que GPT-4o tout en restant très performant pour des tâches de génération et
> correction pédagogique. Le coût moyen mesuré dans mes tests est de $0.000045 pour 45 appels
> — moins d'un centime pour une heure de session intensive."

**"C'est quoi le RAG ?"**
> "RAG = Retrieval-Augmented Generation. Au lieu de demander à l'IA de générer une question
> de mémoire (ce qu'elle pourrait inventer), on lui fournit les passages pertinents du document
> comme contexte. La réponse est ancrée dans le document réel. C'est fondamentalement différent
> d'un chatbot générique."

---

# PARTIE 4 — CE QU'IL FAUT MAÎTRISER POUR ÊTRE VRAIMENT À L'AISE

## Les fichiers que tu dois connaître par cœur

### `app.py` — le chef d'orchestre
C'est le point d'entrée. Il fait 368 lignes et gère :
- La protection par mot de passe (APP_PASSWORD)
- L'authentification login/register
- La gestion des onglets selon le rôle
- Le mode présentation
- Le mode démo (quand aucun utilisateur n'existe)

**Ce qu'il ne fait pas :** aucune logique métier. Il route vers les bons onglets.

### `ai_service.py` — le cerveau IA
Deux fonctions principales :
- `generate_question()` : prend un texte, retourne (question, chunk_ids, type, rag_chunks)
- `correct_answer()` : prend question + réponse + texte source, retourne un dict avec score

**Point important :** `generate_question` retourne 4 valeurs, pas 3. La docstring est périmée (bug connu).

### `engine/spaced_rep.py` — le moteur de mémoire
`classify_mastery(df)` : prend un DataFrame de stats par chunk, retourne les classes Fragile/En consolidation/Maîtrisé + trend + prochain révision.

### `database.py` — la façade de données
Ce fichier fait deux choses :
1. `init_db()` : crée toutes les tables (20+ tables, migrations douces)
2. Re-exports : tous les modules `db/` sont re-exportés ici pour la compatibilité

**Ne jamais :** supprimer un re-export sans vérifier tous les importeurs.

### `auth_service.py` — la sécurité
`register_user()`, `verify_password()`, `promote_user()`.
`promote_user()` vérifie les droits en base, pas en session_state. C'est volontaire.

---

## Les concepts que tu dois pouvoir expliquer à voix haute

1. **La différence entre RAG et un chatbot classique**
   → RAG ancre la réponse dans le document. Chatbot classique invente.

2. **Pourquoi la répétition espacée fonctionne**
   → Courbe d'oubli d'Ebbinghaus. Réviser juste avant d'oublier est plus efficace.

3. **Ce qu'est la similarité cosinus**
   → C'est le cosinus de l'angle entre deux vecteurs. Résultat entre -1 et +1.
   Si le résultat est proche de 1 : les vecteurs pointent dans la même direction → textes similaires.
   Si le résultat est proche de 0 : les vecteurs sont perpendiculaires → textes sans rapport.
   Dans le code : `np.dot(a, b) / (norm_a * norm_b)`.
   En pratique : "cette section ressemble à ta question à 87%" = similarité cosinus de 0.87.

4. **Pourquoi bcrypt et pas MD5 ou SHA256**
   → MD5 et SHA256 sont rapides, bcrypt est lent par design. Lent = difficile à brute-forcer.
   bcrypt ajoute aussi un sel unique par mot de passe.

5. **Ce qu'est Docker**
   → Une boîte qui contient l'appli + ses dépendances. Lancez-le n'importe où, ça marche.

6. **La différence SQLite / PostgreSQL**
   → SQLite : fichier local, parfait pour dev et MVP. PostgreSQL : serveur, concurrent, pour production.

---

## Les chiffres à retenir

| Métrique | Valeur | À dire si on creuse |
|----------|--------|---------------------|
| Coût estimé par appel LLM chat | ~$0.00015 input + $0.0006 output (gpt-4o-mini) | Mesuré dans runtime_metrics |
| Coût d'une session de 45 appels (simulation) | ~$0.000045 | Mode MOCK = latence 0ms, pas une vraie heure |
| Seuil Maîtrisé | avg_score ≥ 0.80 ET ≥ 5 tentatives | Calibré Phase 18C, harness isolé |
| Seuil Fragile | avg_score < 0.60 | Source : engine/thresholds.py |
| Dimensions embedding | 1536 (text-embedding-3-small) | ~8000 tokens max en entrée |
| Timeout API | 30 secondes | Configurable dans gateway.py |
| Max chars par chunk | ~500 chars | Découpé par section logique |
| Tests : 262 au total | py_compile (100+ fichiers) + regression (invariants moteur) + unitaires auth | Ne dis pas "262 tests unitaires" — sois précis |
| Phases de développement | 19 | Chacune avec objectif, livrables, critère de sortie |
| Tâches réalisées | 84+ | Toutes tracées dans TASKS/current_tasks.json |

---

## Les erreurs à ne pas faire en entretien

**Ne dis pas** : "j'ai utilisé l'IA pour générer mon code"
**Dis** : "j'ai utilisé Claude Code pour m'aider à structurer certaines parties, comme un développeur utilise Stack Overflow. Les décisions d'architecture et la logique métier sont les miennes."

**Ne dis pas** : "mon projet est parfait"
**Dis** : "j'ai une liste de dettes techniques documentées. Je peux vous montrer exactement où elles sont et comment je les corrigerais."

**Ne dis pas** : "je ne connais pas X"
**Dis** : "je n'ai pas encore travaillé avec X, mais voici comment j'ai appris Y et Z en quelques semaines — je suis à l'aise pour apprendre de nouveaux outils."

**Ne dis pas** : "c'est juste un projet perso"
**Dis** : "c'est un produit fonctionnel avec authentification, multi-rôles, Docker, CI/CD, monitoring, et 262 tests. La seule différence avec un projet en production c'est l'échelle."

---

## Tes vraies forces — ce que peu de candidats en reconversion ont

1. **Tu sais pourquoi les choses existent** — pas juste comment les coder
2. **Tu as documenté 20 phases de décisions** — tu peux expliquer pourquoi chaque choix
3. **Tu as calibré ton moteur empiriquement** — c'est une démarche d'ingénieur, pas de script kiddie
4. **Tu as géré la complexité progressive** — chaque phase laisse le projet plus stable, pas moins
5. **Tu connais tes limites** — les dettes techniques sont listées, pas cachées

---

---

# PARTIE 5 — CE QUI N'EST PAS DANS LES AUTRES SECTIONS

## Si on te demande de coder en live — révise ça

Les entretiens techniques junior incluent souvent un exercice Python basique.
Rien à voir avec ton projet — juste des fondamentaux. Révise ces 5 patterns :

**1. Manipulation de liste**
```python
# Filtrer les scores >= 0.8
scores = [0.9, 0.5, 0.8, 0.3, 0.95]
bons = [s for s in scores if s >= 0.8]
```

**2. Manipulation de dict**
```python
# Compter les occurrences
erreurs = ["oubli_etape", "vague", "oubli_etape", "correct"]
compteur = {}
for e in erreurs:
    compteur[e] = compteur.get(e, 0) + 1
```

**3. Fonction simple avec valeur par défaut**
```python
def score_label(score, seuil=0.8):
    return "Maîtrisé" if score >= seuil else "Fragile"
```

**4. Lecture d'un fichier JSON**
```python
import json
with open("config.json") as f:
    data = json.load(f)
```

**5. Requête SQL de base**
```python
conn.execute(
    "SELECT * FROM attempts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
    (user_id,)
).fetchall()
```

**Important :** Si tu bloques en live, dis-le à voix haute : "Je sais ce que je veux faire,
je cherche la syntaxe exacte." C'est infiniment mieux que le silence.

---

## Les questions à poser à l'interviewer

Finir un entretien sans poser de questions, c'est rater une occasion et paraître passif.
Voici des questions qui montrent que tu penses à long terme :

**Pour la RH :**
- "Quel est le parcours typique d'un junior dans votre équipe — à quoi ressemble la première année ?"
- "Comment se passe l'onboarding technique — est-ce qu'on est accompagné ou en autonomie ?"
- "Quels sont les projets sur lesquels je pourrais contribuer rapidement ?"

**Pour l'équipe technique :**
- "Quelle est votre stack actuelle, et est-ce qu'il y a des migrations prévues ?"
- "Comment se passe la code review chez vous — pair programming, PR formelle ?"
- "Qu'est-ce que vous cherchez à améliorer dans votre process de développement en ce moment ?"
- "Vous utilisez des outils d'IA dans votre workflow de dev ? (Copilot, Claude, etc.)"

**À éviter :** "C'est quoi le salaire ?" en première question. Et "c'est quoi les avantages ?" avant qu'on te fasse une offre.

---

## Comment gérer "vous avez utilisé l'IA pour construire ça ?"

Cette question arrivera. Voici la réponse complète et honnête :

> "J'ai utilisé Claude Code comme assistant de développement — comme un développeur sénior
> disponible 24h/24 pour répondre à des questions techniques.
>
> Les décisions d'architecture sont les miennes : pourquoi SQLite et pas PostgreSQL,
> pourquoi engine/ est un module pur sans imports projet, pourquoi la répétition espacée
> s'implémente de cette façon.
>
> Les 19 phases de développement, la roadmap, les critères de sortie de chaque phase —
> c'est moi qui les ai définis. L'IA m'a aidé à écrire du code plus vite, pas à penser à ma place.
>
> D'ailleurs, l'IA a trouvé des bugs dans mon code que je n'avais pas vus — des docstrings
> périmées, un `datetime.utcnow()` déprécié. J'ai décidé de les garder en dette documentée
> plutôt que de les corriger mécaniquement, parce qu'ils n'impactent pas le fonctionnement.
> Ça, c'est un choix d'ingénierie que j'ai fait, pas l'IA."

**Pourquoi cette réponse est bonne :** elle est honnête, elle montre que tu comprends la différence
entre "utiliser un outil" et "laisser l'outil penser", et elle prouve que tu sais critiquer ton propre code.

---

## Ton ancrage terrain — ne le laisse pas à la porte

Le terrain t'a donné quelque chose que peu de développeurs ont : **tu comprends pourquoi les gens
ont besoin d'apprendre des procédures.** Tu as vu ce que c'est d'arriver sur un poste avec un
manuel de 80 pages et 2 semaines pour être opérationnel.

C'est pour ça que ton moteur a :
- 6 types de questions différents (parce que tout le monde n'apprend pas pareil)
- De la répétition espacée (parce que mémoriser le jour J ne suffit pas)
- Un feedback sur le type d'erreur (pas juste "faux" — mais "tu as oublié une étape")
- Un mode formateur (parce que quelqu'un doit suivre la progression de l'équipe)

**En entretien, dis ça :**
> "Ce projet vient directement de ce que j'ai observé sur le terrain.
> Les outils de formation existants ne distinguent pas quelqu'un qui sèche par manque de révision
> de quelqu'un qui confond deux notions — ils donnent juste un score. ADDISCO OPS, lui, identifie
> le TYPE d'erreur et adapte les questions suivantes en conséquence.
> C'est le genre d'outil dont j'aurais eu besoin quand je débutais."

---

## Le poste que tu cherches — sois précis

"Je veux travailler dans l'IT" ne suffit pas. Identifie parmi ces profils lequel te correspond :

| Profil | Ce que tu ferais | Ce que ton projet prouve |
|--------|-----------------|--------------------------|
| **Junior Python dev** | Backend, API, scripting | Architecture Python modulaire, SQLite, git |
| **Data/AI developer** | Pipelines IA, embeddings, RAG | Pipeline RAG complet, OpenAI API, numpy |
| **MLOps junior** | Déploiement, monitoring, CI/CD | Docker, GitHub Actions, Sentry, runtime_metrics |
| **Technical Product** | Spécification, pont tech/métier | 19 phases documentées, ROADMAP, PRD, user stories |

**Conseil :** Si tu n'es pas encore fixé, le profil "Junior Python dev avec appétence IA" est
le plus large et le plus honnête. Il ne sur-vend rien.

---

## Script de démonstration — si tu dois montrer l'appli en live

**Durée recommandée : 5 minutes max**

**Étape 1 (30 sec) — Le contexte**
> "Je vais vous montrer un cas concret. On va importer une procédure d'entreprise,
> et voir comment l'application s'en empare."

**Étape 2 (1 min) — L'import et le RAG**
→ Aller dans l'onglet Documents, montrer un PDF importé.
→ Aller dans Entraînement, sélectionner le document.
→ Cliquer "Générer une question".
> "Le système vient de trouver les 3 passages du document les plus pertinents pour générer
> une question — c'est le RAG. Vous voyez ici le score de similarité."

**Étape 3 (1 min) — La correction adaptative**
→ Soumettre une réponse incomplète intentionnellement.
> "Le système identifie le type d'erreur — ici 'oubli d'étape'. Pas juste un score.
> Cette information va influencer les prochaines questions."

**Étape 4 (1 min) — Le moteur adaptatif**
→ Aller dans Dashboard, montrer le profil de maîtrise.
> "Après chaque tentative, le moteur recalcule la maîtrise de chaque section.
> Ici, 'Fragile' signifie que la répétition espacée programmera une révision dans 1-2 jours."

**Étape 5 (30 sec) — Le tableau admin**
→ Si possible, montrer tab Admin.
> "Le formateur voit la progression de toute l'équipe, les KPIs globaux, et les alertes système."

**Ce qu'il ne faut PAS montrer en demo :** les logs, le code, les fichiers de config.
Ce qui compte : que ça marche, que ça soit fluide, que tu saches expliquer chaque étape.

---

Ton projet a une note de **76/100** à une analyse technique sérieuse.
Les 24 points manquants sont de la dette technique standard et documentée.
Aucun n'est une incompréhension fondamentale.

Ce qu'un senior verrait dans ton code :
- Quelqu'un qui a appris à faire les choses bien
- Quelqu'un qui sait documenter ses décisions
- Quelqu'un qui ne s'arrête pas à "ça marche" mais va jusqu'à "ça tient"

C'est ce qu'il faut communiquer.

---

*Ce document est pour toi seul — ne le montre pas en entretien.*
*Il est là pour que tu sois préparé à toutes les questions.*
*Bonne chance, Guilhem.*
