# ROADMAP PHASE 2 — ADDISCO OPS

## Objectif de phase

Faire passer ADDISCO OPS de MVP pédagogique fonctionnel à moteur pédagogique explicable, robuste et calibrable.

La phase 1 a permis de construire :
- RAG documentaire ;
- import PDF/DOCX/TXT ;
- chunks ;
- embeddings ;
- correction IA ;
- historique ;
- analytics ;
- dashboard ;
- profils enrichis ;
- multi-user ;
- Docker ;
- README ;
- QA ;
- guardrails architecture V1.

La phase 2 vise :
- explicabilité ;
- confiance ;
- rejet hors contexte ;
- qualité documentaire ;
- adaptativité ;
- calibration ;
- maintenance assistée.

---

## Règle mère

Petit bout → consolidation → vérification → snapshot → petit bout suivant.

Aucune tâche ne doit être lancée sans validation de la précédente.

---

## Règle de gouvernance entre tâches

À chaque fin de tâche :

1. proposer la tâche suivante ;
2. attendre validation explicite avant implémentation ;
3. ne jamais passer automatiquement à la tâche suivante ;
4. une tâche = un périmètre, pas de débordement ;
5. fin de tâche = tests + commit + snapshot + ROADMAP_PROGRESS.md mis à jour ;
6. aucune tâche ne modifie le runtime hors de son périmètre.

---

## Ordre stratégique — Phase 2

Priorité : moteur pédagogique → calibration → maintenance → admin → UX.

| Rang | Task | Titre | Statut |
|------|------|-------|--------|
| 1 | TASK-051 | Sources visibles / contexte pédagogique | DONE |
| 2 | TASK-051B | Consolidation profil pédagogique | DONE |
| 3 | TASK-052 | Score de confiance correction V1 | DONE |
| 4 | TASK-053 | Rejet hors sujet / non évaluable | DONE |
| 5 | TASK-054 | Chunk Quality Analyzer V1 | TODO |
| 6 | TASK-055 | Skill Graph Engine V1 | TODO |
| 7 | TASK-056 | Adaptive Difficulty Engine V2 | TODO |
| 8 | TASK-057 | Error Pattern Memory | TODO |
| 9 | TASK-058 | Curriculum Engine V1 | TODO |
| 10 | TASK-059 | Calibration Engine V1 | TODO |
| 11 | TASK-060 | Maintenance Assistée V1 | TODO |
| 12 | TASK-061 | Vue admin | TODO |
| 13 | TASK-062 | Rapports HTML/PDF | TODO |
| 14 | TASK-063 | UX responsive tablette | TODO |

---

## TASK-051 — Sources visibles / contexte pédagogique

STATUS : DONE — Commit `8aebae7` — Snapshot `snapshot_task051_ok`

Objectif :
Afficher à l'utilisateur le contexte utilisé par le moteur.

Livré :
- expander "Contexte RAG utilisé" avec top-k chunks ;
- rang (Source principale / Source 2 / Source 3) ;
- document source + score RAG (%) ;
- section + extrait 200 chars ;
- fallback texte brut : expander masqué.

---

## TASK-051B — Consolidation UX profil pédagogique

STATUS : DONE — Commit `f31f117` — Snapshot `snapshot_task051b_ok`

Objectif :
Séparer confiance statistique et signal pédagogique dans le profil enrichi.

Livré :
- séparation confiance statistique (volume) et signal pédagogique (écart modes) ;
- affichage côte à côte ;
- nettoyage dominant_style_label.

---

## TASK-052 — Score de confiance correction V1

STATUS : DONE — Commit `d56a087` — Snapshot `snapshot_task052_ok`

Objectif :
Afficher une confiance de correction : faible / moyenne / élevée.

Signaux utilisés :
- score RAG ;
- présence du chunk source ;
- longueur de réponse ;
- overlap lexical simple ;
- réponse vide ou trop courte.

---

## TASK-053 — Rejet hors sujet / non évaluable

STATUS : DONE — Commit `9f98dbb` — Snapshot `snapshot_task053_ok`

Objectif :
Empêcher les corrections absurdes.

Livré :
- détection réponse vide ;
- détection réponse hors contexte ;
- état non évaluable enregistré proprement ;
- scores existants préservés.

---

## TASK-054 — Chunk Quality Analyzer V1

STATUS : TODO

Objectif :
Auditer la qualité documentaire.

Détecter :
- chunks trop longs ;
- chunks trop courts ;
- chunks ambigus ou tabulaires ;
- chunks sans skill associé ;
- chunks avec trop de skills ;
- chunks générant beaucoup d'échecs ;
- documents générant trop d'erreurs.

Sortie :
- rapport read-only ;
- aucun auto-fix ;
- recommandations.

Contraintes :
- script dans `tools/observability` ou `tools/maintenance` ;
- zéro écriture DB ;
- zéro modification runtime.

Validation :
- rapport lisible ;
- zéro écriture DB ;
- tests + py_compile OK.

---

## TASK-055 — Skill Graph Engine V1

STATUS : TODO

Objectif :
Transformer les skills isolés en graphe de dépendances pédagogiques.

Logique :
- identifier les prérequis entre skills ;
- modéliser les dépendances (skill A requis avant skill B) ;
- exposer le graphe pour orienter la progression de l'apprenant ;
- détecter les skills orphelins ou sans dépendances.

Contraintes :
- pas de ML ;
- graphe représenté en données (pas de lib graphe externe) ;
- pas de modification du moteur de question existant ;
- explicable et auditable.

Validation :
- graphe de dépendances générable ;
- skills orphelins détectés ;
- tests + py_compile OK.

---

## TASK-056 — Adaptive Difficulty Engine V2

STATUS : TODO

Objectif :
Adapter la difficulté des questions selon le profil récent de l'apprenant.

Signaux utilisés :
- score moyen récent ;
- temps de réponse ;
- régularité des sessions ;
- erreurs répétées sur le même skill ;
- stabilité du profil (momentum) ;
- historique récent vs historique global.

Contraintes :
- règles explicites, pas de ML ;
- pas de refonte interface ;
- compatible profils existants ;
- réversible.

Validation :
- cas score fort → difficulté augmentée ;
- cas erreurs répétées → difficulté réduite ;
- cas profil instable → comportement neutre ;
- tests + py_compile OK.

---

## TASK-057 — Error Pattern Memory

STATUS : TODO

Objectif :
Mémoriser les patterns d'erreurs récurrents et les utiliser pour adapter les futures questions.

Fonctions :
- détecter les types d'erreurs répétés par skill ;
- stocker le pattern (type erreur + fréquence + dernier contexte) ;
- exposer le pattern au moteur de génération de questions ;
- permettre au moteur d'éviter de reproduire les mêmes confusions.

Contraintes :
- stockage en base, pas en mémoire volatile ;
- pas d'appel API supplémentaire ;
- pas de modification des tentatives existantes ;
- read-only sur l'historique passé.

Validation :
- pattern détecté après 3+ erreurs similaires ;
- pattern influençant la prochaine question ;
- tests + py_compile OK.

---

## TASK-058 — Curriculum Engine V1

STATUS : TODO

Objectif :
Construire une progression logique par notion : fondation → entraînement → validation → révision.

Logique :
- pour chaque skill, définir une séquence pédagogique ;
- ordonnancer les chunks selon leur rôle dans la séquence ;
- proposer un plan de session ordonné par étape pédagogique ;
- détecter les gaps (skill jamais vu, fondation manquante).

Contraintes :
- basé sur les données existantes (skills, mastery, attempts) ;
- pas de refonte du moteur de répétition espacée existant ;
- pas de ML ;
- explicable.

Validation :
- plan de session séquencé générable ;
- gaps détectés ;
- tests + py_compile OK.

---

## TASK-059 — Calibration Engine V1

STATUS : TODO

Objectif :
Tester le moteur avec utilisateurs simulés, attempts synthétiques, profils attendus vs profils détectés.

Créer :
- utilisateurs simulés ;
- attempts synthétiques selon différents profils ;
- profils attendus en entrée ;
- rapport attendu vs détecté.

Contraintes :
- environnement de test isolé ;
- pas de pollution utilisateurs réels ;
- option dry-run obligatoire ;
- backup recommandé avant exécution.

Validation :
- 5 profils simulés minimum ;
- comparaison profil attendu/détecté ;
- rapport calibration clair ;
- tests + py_compile OK.

---

## TASK-060 — Maintenance Assistée V1

STATUS : TODO

Objectif :
Créer un rapport de maintenance pédagogique et structurelle.

Détecter :
- chunks faibles (repris de TASK-054 avec enrichissement) ;
- skills morts (jamais atteints) ;
- skills trop larges (trop de chunks) ;
- documents problématiques (trop d'erreurs) ;
- dérives de scores ;
- anomalies attempts ;
- findings guardrails récurrents.

Contraintes :
- read-only ;
- aucune correction automatique ;
- pas d'appel API ;
- rapport clair avec verdict GO SAFE / WARNING / FAILED.

Validation :
- rapport maintenance lisible ;
- verdict généré ;
- py_compile OK.

---

## TASK-061 — Vue admin

STATUS : TODO

Objectif :
Supervision utilisateurs, documents, stats globales, alertes et état système.

Fonctions :
- liste des utilisateurs avec rôle et activité récente ;
- activation / désactivation d'un compte ;
- liste des documents avec statut d'indexation ;
- stats globales (tentatives, scores, utilisateurs actifs) ;
- alertes système visibles (chunks faibles, skills morts, erreurs guardrails).

Contraintes :
- rôle admin requis ;
- pas de modification du moteur pédagogique ;
- interface Streamlit dans l'onglet existant admin ou nouveau tab.

Validation :
- liste utilisateurs visible et actionnable ;
- stats globales affichées ;
- tests + py_compile OK.

---

## TASK-062 — Rapports HTML/PDF

STATUS : TODO

Objectif :
Générer un bilan pédagogique par apprenant et par cohorte.

Contenu du rapport :
- progression sur la période ;
- skills maîtrisés / en cours / non vus ;
- points forts et axes d'amélioration ;
- historique des sessions.

Contraintes :
- export HTML en premier (léger, sans dépendance lourde) ;
- PDF en second si pertinent ;
- pas de dépendance externe lourde (reportlab évité si possible) ;
- générateur dans `tools/` ou via onglet Streamlit.

Validation :
- rapport HTML générable en un clic ;
- données correctes ;
- tests + py_compile OK.

---

## TASK-063 — UX responsive tablette

STATUS : TODO

Objectif :
Optimiser l'affichage tablette, plein écran, mode démonstration.

Fonctions :
- layout adapté aux petits écrans (colonnes réduites) ;
- mode présentation plein écran ;
- navigation simplifiée pour démo.

Contraintes :
- pas de modification du moteur pédagogique ;
- pas de bibliothèque CSS externe ;
- uniquement `app.py` et les fichiers `tabs/`.

Validation :
- rendu tablette testé ;
- mode présentation opérationnel ;
- tests + py_compile OK.

---

## Tâches déplacées (non supprimées)

Ces tâches étaient prévues dans la version précédente de la roadmap.
Elles sont conservées ici pour traçabilité mais ne font plus partie de l'ordre de priorité actuel.

### [Déplacée] Adaptive Next Question V1

Objectif original :
Adapter la prochaine question après une erreur.

Logique :
- même skill si échec ;
- difficulté réduite si score faible ;
- mode étape par étape si oubli d'étape ;
- analogie si profil analogique efficace ;
- reformulation si réponse vague.

Note : la logique d'adaptation est reprise et enrichie dans TASK-056 (Adaptive Difficulty Engine V2) et TASK-057 (Error Pattern Memory).

---

### [Déplacée] Health Score Projet

Objectif original :
Créer un score synthétique de santé projet.

Indicateurs :
- findings guardrails ;
- tests OK/KO ;
- taille fichiers ;
- fonctions longues ;
- qualité chunks ;
- stabilité Docker ;
- smoke tests ;
- couverture QA.

Note : la logique est reprise et enrichie dans TASK-060 (Maintenance Assistée V1).

---

## À reporter

Ne pas lancer maintenant :
- PostgreSQL ;
- React ;
- FastAPI ;
- workers ;
- Redis ;
- microservices ;
- scaling distribué ;
- déploiement public.

Ces éléments ne viennent qu'après stabilisation de la phase 2.

---

## Définition de fin de phase 2

La phase 2 est terminée quand le moteur peut démontrer :

1. Une question générée depuis un document.
2. La source visible.
3. Une correction avec confiance.
4. Un rejet hors contexte si nécessaire.
5. Une qualité documentaire auditée (Chunk Quality Analyzer).
6. Un graphe de compétences actif (Skill Graph).
7. Une difficulté adaptative en fonction du profil.
8. Une mémoire des patterns d'erreurs.
9. Un curriculum ordonné par notion.
10. Une calibration simulée validée.
11. Une maintenance assistée opérationnelle.
12. Une vue admin fonctionnelle.
13. Un rapport pédagogique exportable.
