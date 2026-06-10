# ADDISCO OPS — Investor Brief
### Révision métier adaptative par l'IA · B2B SaaS · Juin 2026

---

## Résumé exécutif

ADDISCO OPS est un moteur pédagogique adaptatif qui transforme les documents internes d'une organisation en sessions de révision personnalisées, pilotées par l'IA.

Le système ingère des documents métier (procédures, réglementations, guides opérationnels), les découpe en base de connaissances sémantique, génère des questions contextualisées et ajuste en continu la difficulté, le rythme et le style pédagogique selon le profil de chaque apprenant.

**Statut actuel :** prototype fonctionnel en production, 20 phases livrées, déployé sur Railway, architecture multi-utilisateurs opérationnelle, 262 tests automatisés.

---

## Le problème

Les organisations qui forment leurs collaborateurs à des procédures complexes — secteurs réglementés, opérations terrain, protocoles de sécurité — font face à trois contraintes structurelles :

**1. Le contenu est éparpillé.** Procédures PDF, guides Word, notes internes : les savoirs existent mais ne sont pas mobilisables dans un contexte pédagogique.

**2. La formation est générique.** Les LMS traditionnels délivrent le même contenu à tous. Il n'y a pas d'adaptation au niveau réel, aux lacunes identifiées, ni à la vitesse de progression de chaque apprenant.

**3. La mémorisation n'est pas suivie.** Une session de formation produit rarement une trace exploitable sur ce qui a été réellement compris, oublié ou fragile.

---

## La solution — ADDISCO OPS

ADDISCO OPS résout ces trois problèmes par un pipeline en quatre étapes :

```
Document métier  →  Base de connaissances  →  Question adaptée  →  Correction et suivi
(PDF / DOCX / TXT)   (chunks + embeddings)    (6 types, RAG)       (score + mémoire)
```

### Ce que le système fait concrètement

- **Import documentaire intelligent** : PDF, DOCX, TXT découpés automatiquement en chunks sémantiques indexés par embeddings (OpenAI text-embedding-3-small).
- **Génération de questions contextualisées** : 6 types (définition, application, diagnostic, procédure, comparaison, synthèse) générés à partir des passages les plus pertinents du corpus.
- **Correction IA avec score de confiance** : analyse de la réponse, score, explication, source citée, rejet des réponses hors sujet.
- **Moteur adaptatif calibré** : la difficulté, le biais de maîtrise et les intervalles de révision s'ajustent selon le profil en temps réel (6 seuils validés par harness de calibration dédié).
- **Répétition espacée** : les notions fragiles reviennent plus souvent — intervalles J+1 / J+7 / J+30 calculés par utilisateur.
- **Corpus multi-documents** : un formateur crée un corpus nommé, l'apprenant s'entraîne sur l'ensemble sans friction.

---

## Marché & Positionnement

### Le contexte que vous connaissez

Le premier cycle de l'IA pour l'apprentissage a produit des outils de **conversation pédagogique** — tuteurs IA, chatbots interactifs, assistants qui répondent aux questions d'un apprenant en langage naturel. Ces outils ont prouvé leur utilité sur l'engagement et l'exploration de connaissances générales.

Mais ils ont une limite structurelle pour le marché B2B : **ils ne savent pas ce que l'organisation a besoin que l'apprenant maîtrise, et ils ne peuvent pas le mesurer.**

### Le vrai marché non adressé

Le marché de la formation corporative (Corporate L&D) représente **~380 milliards de dollars par an** à l'échelle mondiale. La part concernée par la maîtrise de procédures documentées — transport, énergie, santé, BTP, industrie, services publics — est structurellement différente du marché EdTech grand public :

| | EdTech grand public | Formation corporative procédurale |
|---|---|---|
| Acheteur | L'apprenant lui-même | L'organisation (RH / Direction Formation) |
| Objectif | Exploration, curiosité | Maîtrise certifiable, conformité |
| Contenu | Générique (maths, langues) | Propriétaire (procédures internes) |
| Succès mesuré | Engagement, temps passé | Score de maîtrise, rétention à J+30 |
| Tolérance à l'erreur | Haute | Faible (sécurité, réglementation) |

Le chat IA pédagogique répond bien à la colonne de gauche. **ADDISCO OPS cible entièrement la colonne de droite.**

### Pourquoi maintenant

Trois conditions sont réunies en 2026 que aucun acteur EdTech traditionnel ne pouvait adresser avant :

1. **Les LLM sont assez bons pour corriger des réponses métier** — la correction IA sur du contenu procédural, ancrée dans la source, est fiable à un niveau exploitable en entreprise.
2. **Les embeddings rendent tout corpus interrogeable** — n'importe quelle organisation peut transformer ses PDF internes en base de connaissances sémantique sans data scientists.
3. **Le coût d'infrastructure est devenu négligeable** — un déploiement qui coûtait 200k€/an il y a cinq ans tourne aujourd'hui sur Railway pour quelques dizaines d'euros par mois.

### Positionnement face au chat IA pédagogique

Le chat IA pédagogique est un excellent **point d'entrée** dans l'apprentissage : il engage, il répond, il explique. Mais il ne crée pas de maîtrise vérifiable sur un corpus propriétaire.

ADDISCO OPS n'est pas un concurrent du chat IA pédagogique — c'est sa **suite logique pour le B2B** :

```
Chat IA pédagogique     →    ADDISCO OPS
Exploration libre            Maîtrise ciblée
Contenu générique            Corpus propriétaire
Conversation éphémère        Mémoire d'erreur persistante
Engagement subjectif         Score de rétention mesurable
Aucune trace formateur       Dashboard formateur + export PDF
```

L'investisseur qui a déjà misé sur le chat IA pédagogique a validé que les LLM peuvent enseigner. ADDISCO OPS est la brique qui **transforme cette capacité en valeur mesurable pour une organisation**.

### Secteurs d'entrée prioritaires

Les secteurs où la maîtrise de procédures est critique, documentée et non négociable :

- **Transport & mobilité** — protocoles sécurité, réglementations, gestes métier.
- **Énergie & industrie** — procédures de maintenance, consignes de sécurité.
- **Santé** — protocoles de soin, gestion des risques, conformité.
- **Services publics & administration** — règlementation, guides opérationnels.

Ces secteurs partagent une caractéristique clé : **ils ont déjà le contenu**. La friction n'est pas de créer des formations, elle est de les rendre efficaces et mesurables.

---

## Différenciation technique

| Critère | LMS traditionnel | Chat IA pédagogique | ADDISCO OPS |
|---|---|---|---|
| Source documentaire propriétaire | ✓ | ✗ | **✓** |
| Adaptation au niveau individuel | ✗ | partiel | **✓** |
| Répétition espacée sur contenu interne | ✗ | ✗ | **✓** |
| Profil pédagogique par apprenant | ✗ | ✗ | **✓** |
| Score de maîtrise mesurable | ✗ | ✗ | **✓** |
| Mémoire d'erreur persistante | ✗ | ✗ | **✓** |
| Explainability moteur (auditabilité) | ✗ | ✗ | **✓** |
| Dashboard formateur / cohorte | ✓ | ✗ | **✓** |
| Correction ancrée dans la source | ✗ | ✗ | **✓** |

La différence principale avec le chat IA pédagogique n'est pas l'engagement — c'est la **maîtrise vérifiable**. Le chat répond. ADDISCO OPS mesure ce qui reste.

---

## État actuel — Traction technique

Le prototype a franchi 20 phases de développement incrémental en production réelle :

| Indicateur | Valeur |
|---|---|
| Tests automatisés | 262 (zéro régression) |
| Score audit système (read-only) | 99 / 100 |
| Phases livrées | 20 |
| Déploiement actuel | Railway (Docker, HTTPS, healthcheck) |
| Multi-utilisateurs | Oui (bcrypt, rôles, sessions) |
| Feedback utilisateur collecté | Oui (pertinence question + satisfaction session) |
| Seuils moteur | Calibrés par harness dédié (500 sessions simulées) |
| CI/CD | GitHub Actions (py_compile 100 fichiers, tests) |
| Monitoring | Sentry + métriques LLM (latence, coût, taux d'erreur) |

Ce niveau de maturité technique dépasse ce qu'on attend d'un POC. Le produit est **démontrable en conditions réelles dès aujourd'hui**.

---

## Modèle économique — Vision B2B SaaS

**Cible principale :** organisations dont les collaborateurs doivent maîtriser des procédures documentées — transport, énergie, santé, BTP, industrie réglementée, services publics.

**Proposition de valeur :** réduire le temps de montée en compétence, améliorer la rétention des procédures critiques, donner aux formateurs une visibilité sur les lacunes réelles de chaque apprenant.

### Modèles de revenus envisagés

| Modèle | Détail |
|---|---|
| **SaaS par siège** | Facturation mensuelle par utilisateur actif (formateur + apprenants) |
| **Licence corpus** | Par nombre de documents ingérés / volume de connaissances gérées |
| **Intégration on-premise** | Pour les organisations avec contraintes souverainité des données (Docker, PostgreSQL) |
| **Module formateur** | Dashboard cohorte + export rapports pédagogiques (déjà implémenté) |

**Pricing indicatif (SaaS) :** 15–40 € / utilisateur / mois selon volume et fonctionnalités. Un déploiement de 50 apprenants génère 9 000–24 000 € ARR par client.

---

## Feuille de route — Prochaine phase

La prochaine phase de développement (ai-v4, initialisée) cible :

1. **PostgreSQL + pgvector** — scalabilité production, recherche vectorielle native.
2. **API REST** — permettre l'intégration dans des SI existants (SIRH, LMS legacy).
3. **Tableau de bord formateur enrichi** — suivi de cohorte, comparaison, export PDF automatique.
4. **Onboarding guidé** — réduire le time-to-value pour un nouveau client.
5. **Tests utilisateurs réels** — sessions humaines instrumentées, feedback qualitatif collecté.

---

## Profil fondateur

Guilhem Marcelino — ASCT SNCF, reconversion vers IT / Innovation.

**Ce qui est inhabituel ici :** ce projet n'a pas été construit par un développeur. Il a été construit par un opérateur terrain qui connaît de l'intérieur le problème de la maîtrise des procédures en environnement contraint.

- Compréhension directe du besoin utilisateur (formation aux procédures en contexte opérationnel).
- Maîtrise de la démarche produit : 20 phases, gouvernance stricte, tests systématiques, architecture documentée.
- Méthode de développement : orchestration d'outils IA (Claude Code, ChatGPT) — assumé et transparent, preuve que le levier IA peut être utilisé par des profils non techniques pour produire un produit réel.
- Approche : incrémentale, rigoreuse, pilotée par les données (calibration, simulation, audit automatisé).

**Ce que ça signifie pour l'investisseur :** le fondateur comprend l'utilisateur final parce qu'il l'est. Il a construit le produit dans les mêmes contraintes que ses futurs clients.

---

## Ce que nous cherchons

À ce stade, nous cherchons :

- **Un partenaire ou investisseur amorçage** pour financer la phase de tests utilisateurs réels, le passage PostgreSQL et le développement commercial initial.
- **Un accès à un premier client pilote** — organisation prête à tester le produit sur un corpus de procédures internes réelles contre engagement de feedback structuré.
- **Conseil go-to-market** — identification des canaux d'acquisition B2B adaptés (RH, Direction Formation, DSI).

**Ce que nous n'avons pas encore :** clients payants, chiffre d'affaires. Ce que nous avons : un produit fonctionnel, une architecture solide, un marché identifié, et un fondateur qui comprend le problème par l'expérience.

---

## Pour aller plus loin

| | |
|---|---|
| Demo live | Railway (disponible sur demande) |
| Code source | GitHub — architecture 20 phases, 262 tests |
| Contact | marcelino.guilhem@gmail.com |

---

*Document préparé pour entretien investisseur — Juin 2026*
*ADDISCO OPS — Moteur pédagogique adaptatif B2B*
