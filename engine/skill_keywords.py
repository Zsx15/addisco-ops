"""Listes de mots-clés par skill — matching déterministe V1.1.

V1.1 : retrait des keywords trop génériques identifiés à l'audit.
  - application_regles  : "doit" retiré (ubiquitaire), remplacé par formes spécifiques
  - comprehension_proc  : "procédure", "puis", "ensuite" retirés
  - resolution_problemes: "traiter", "gérer", "en cas de" retirés
  - synthese_reformul   : "ainsi" retiré (connecteur neutre)
  - conformite_reglem   : "sécurité", "article" retirés
"""

SKILL_KEYWORDS: dict[str, list[str]] = {
    "memorisation_faits": [
        "est défini", "se définit", "correspond à", "désigne", "signifie",
        "délai de", "durée de", "nombre de", "seuil de", "valeur de",
        "dans un délai", "au maximum", "au minimum", "au moins", "au plus",
        "minutes", "heures", "jours",
    ],
    "comprehension_procedure": [
        "étape", "processus", "séquence", "protocole",
        "d'abord", "enfin", "avant de",
        "après avoir", "en premier lieu", "déroulement", "marche à suivre",
        "étapes suivantes",
    ],
    "identification_concepts": [
        "notion de", "concept de", "principe de",
        "distinguer", "différence entre", "caractéristique",
        "type de", "catégorie", "classification",
        "se définit comme", "terme technique", "vocabulaire",
    ],
    "application_regles": [
        "est tenu de", "doit impérativement", "obligatoire", "interdit", "requis",
        "conformément", "obligation de", "conforme à", "norme",
        "règlement", "en application de", "selon l'article",
        "formellement", "strictement",
    ],
    "analyse_causale": [
        "en raison de", "résulte de", "entraîne", "provoque",
        "conséquence de", "parce que", "à cause de",
        "impact de", "effet de", "facteur", "lorsque",
        "ce qui implique", "ce qui entraîne",
    ],
    "resolution_problemes": [
        "incident", "problème", "dysfonctionnement", "anomalie",
        "résoudre", "corriger", "remédier",
        "action corrective", "solution", "prise en charge",
        "en cas d'incident", "en cas d'anomalie",
        "résolution de", "procédure de secours", "face à",
    ],
    "prise_decision": [
        "décision", "choisir", "opter", "dans le cas où",
        "selon la situation", "alternative", "en fonction de",
        "arbitrage", "évaluer", "prioriser",
        "choix", "trancher",
    ],
    "evaluation_critique": [
        "vérifier", "contrôler", "valider", "inspecter",
        "exact", "incorrect", "anomalie", "conforme",
        "non conforme", "s'assurer que", "vérification",
        "correct", "inexact",
    ],
    "synthese_reformulation": [
        "en résumé", "en conclusion", "synthèse",
        "c'est-à-dire", "autrement dit", "en d'autres termes",
        "récapitulatif", "en somme", "il ressort que",
        "pour résumer", "en bref",
    ],
    "conformite_reglementaire": [
        "réglementation", "légal", "légale", "loi", "directive",
        "code de", "décret", "arrêté",
        "obligation légale", "obligation réglementaire", "mise en conformité",
        "selon l'article", "décret n°", "loi n°", "code du travail",
        "réglementation en vigueur",
    ],
}
