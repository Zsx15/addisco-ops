\# ROADMAP PHASE 2 — ADDISCO OPS



\## Objectif de phase



Faire passer ADDISCO OPS de MVP pédagogique fonctionnel à moteur pédagogique explicable, robuste et calibrable.



La phase 1 a permis de construire :

\- RAG documentaire ;

\- import PDF/DOCX/TXT ;

\- chunks ;

\- embeddings ;

\- correction IA ;

\- historique ;

\- analytics ;

\- dashboard ;

\- profils enrichis ;

\- multi-user ;

\- Docker ;

\- README ;

\- QA ;

\- guardrails architecture V1.



La phase 2 vise :

\- explicabilité ;

\- confiance ;

\- rejet hors contexte ;

\- qualité documentaire ;

\- adaptativité ;

\- calibration ;

\- maintenance assistée.



\---



\## Règle mère



Petit bout → consolidation → vérification → snapshot → petit bout suivant.



Aucune tâche ne doit être lancée sans validation de la précédente.



\---



\## TASK-051 — Sources visibles / contexte pédagogique



Objectif :

Afficher à l’utilisateur le contexte utilisé par le moteur.



À afficher :

\- document source ;

\- section si disponible ;

\- chunk utilisé ;

\- extrait exact ;

\- score RAG si disponible ;

\- top-k chunks si pertinent.



Contraintes :

\- pas de refactor RAG massif ;

\- pas de modification DB si évitable ;

\- UI simple ;

\- expander Streamlit propre ;

\- compatible gros utilisateur `test`.



Validation :

\- question générée avec source visible ;

\- correction toujours fonctionnelle ;

\- dashboard non impacté ;

\- py\_compile OK ;

\- tests OK.



\---



\## TASK-052 — Score de confiance correction V1



Objectif :

Afficher une confiance de correction : faible / moyenne / élevée.



Signaux possibles :

\- score RAG ;

\- présence du chunk source ;

\- longueur de réponse ;

\- overlap lexical simple ;

\- cohérence réponse/question ;

\- réponse vide ou trop courte.



Contraintes :

\- déterministe ;

\- zéro appel API supplémentaire ;

\- pas de diagnostic médical ;

\- pas de refactor correction.



Validation :

\- confiance affichée ;

\- cas réponse correcte ;

\- cas réponse vague ;

\- cas réponse trop courte ;

\- tests OK.



\---



\## TASK-053 — Rejet hors sujet / non évaluable



Objectif :

Empêcher les corrections absurdes.



Le moteur doit pouvoir dire :

\- réponse hors contexte ;

\- réponse insuffisante ;

\- non évaluable ;

\- reformulation demandée.



Contraintes :

\- pas de suppression de tentative ;

\- enregistrer proprement l’état si pertinent ;

\- ne pas casser les scores existants ;

\- logique explicable.



Validation :

\- réponse vide détectée ;

\- réponse hors sujet détectée ;

\- réponse normale corrigée ;

\- tests OK.



\---



\## TASK-054 — Chunk Quality Analyzer V1



Objectif :

Auditer la qualité documentaire.



Détecter :

\- chunks trop longs ;

\- chunks trop courts ;

\- chunks ambigus ;

\- chunks sans skill ;

\- chunks avec trop de skills ;

\- chunks générant beaucoup d’échecs ;

\- documents générant trop d’erreurs.



Sortie :

\- rapport read-only ;

\- aucun auto-fix ;

\- recommandations.



Validation :

\- script tools/observability ou tools/maintenance ;

\- rapport lisible ;

\- zéro écriture DB ;

\- tests/py\_compile OK.



\---



\## TASK-055 — Adaptive Next Question V1



Objectif :

Adapter la prochaine question après une erreur.



Logique :

\- même skill si échec ;

\- difficulté réduite si score faible ;

\- mode étape par étape si oubli d’étape ;

\- analogie si profil analogique efficace ;

\- reformulation si réponse vague.



Contraintes :

\- règles simples ;

\- pas de ML ;

\- pas de grosse refonte interface ;

\- explicable.



Validation :

\- cas erreur procédure ;

\- cas réponse vague ;

\- cas réussite ;

\- tests OK.



\---



\## TASK-056 — Calibration Engine V1



Objectif :

Créer des parcours synthétiques sans appel API pour tester la robustesse pédagogique.



Créer :

\- utilisateurs simulés ;

\- attempts synthétiques ;

\- profils attendus ;

\- parcours aléatoires ;

\- rapport attendu vs détecté.



Contraintes :

\- environnement de test ;

\- pas de pollution utilisateurs réels ;

\- option dry-run ;

\- backup recommandé.



Validation :

\- 5 profils simulés minimum ;

\- comparaison profil attendu/détecté ;

\- rapport calibration ;

\- tests OK.



\---



\## TASK-057 — Maintenance Assistée V1



Objectif :

Créer un rapport de maintenance pédagogique et structurelle.



Détecter :

\- chunks faibles ;

\- skills morts ;

\- skills trop larges ;

\- documents problématiques ;

\- dérives de scores ;

\- anomalies attempts ;

\- findings guardrails récurrents.



Contraintes :

\- read-only ;

\- aucune correction automatique ;

\- pas d’appel API ;

\- rapport clair.



Validation :

\- rapport maintenance ;

\- verdict GO SAFE / WARNING / FAILED ;

\- py\_compile OK.



\---



\## TASK-058 — Health Score Projet



Objectif :

Créer un score synthétique de santé projet.



Indicateurs :

\- findings guardrails ;

\- tests OK/KO ;

\- taille fichiers ;

\- fonctions longues ;

\- qualité chunks ;

\- stabilité Docker ;

\- smoke tests ;

\- couverture QA.



Sortie :

\- score global /100 ;

\- sous-scores ;

\- recommandations prioritaires.



Validation :

\- script lançable ;

\- rapport clair ;

\- pas de modification runtime.



\---



\## À reporter



Ne pas lancer maintenant :

\- PostgreSQL ;

\- React ;

\- FastAPI ;

\- workers ;

\- Redis ;

\- microservices ;

\- scaling distribué ;

\- déploiement public.



Ces éléments ne viennent qu’après stabilisation de la phase 2.



\---



\## Définition de fin de phase 2



La phase 2 est terminée quand le moteur peut démontrer :



1\. Une question générée depuis un document.

2\. La source visible.

3\. Une correction avec confiance.

4\. Un rejet hors contexte si nécessaire.

5\. Une adaptation pédagogique.

6\. Un profil utilisateur enrichi.

7\. Un dashboard formateur.

8\. Une calibration simulée.

9\. Une maintenance assistée.

10\. Un rapport santé projet.

