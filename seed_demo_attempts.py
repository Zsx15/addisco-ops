"""
Pré-population de la base pour la démo.

Insère des tentatives simulées sur le document de démonstration :
- Section 1 (Posture d'accueil)       : 3 tentatives, score moyen 0.45 → Fragile, En retard
- Section 2 (Perturbations)           : 3 tentatives, score moyen 0.68 → En consolidation, En retard
- Section 3 (PMR)                     : 2 tentatives, score moyen 0.73 → En consolidation, Dans 2 jours
- Section 4 (Traçabilité)             : 3 tentatives, score moyen 0.88 → Maîtrisé, Aujourd'hui

Idempotent : sans effet si des tentatives existent déjà (count > 0).
Usage : python seed_demo_attempts.py
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("database.db")
TODAY   = datetime(2026, 5, 12)

def _days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S")


def _get_chunk_id(conn, title_fragment: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM chunks WHERE section_title LIKE ?",
        (f"%{title_fragment}%",),
    ).fetchone()
    return row[0] if row else None


_ATTEMPTS = [
    # ── Section 1 : Posture d'accueil — Fragile ──────────────────────────────
    {
        "title_fragment": "Posture",
        "score": 0.40, "error_type": "oubli_etape", "topic": "Accueil agent",
        "pedagogy_type": "question_directe", "days_ago": 3,
        "question": "Quel est le délai maximal pour répondre à un voyageur en difficulté ?",
        "user_answer": "L'agent doit répondre rapidement.",
        "expected_answer": "Deux minutes.",
        "correction": (
            "Le délai maximal est de deux minutes. "
            "Si l'agent ne dispose pas de la réponse, il oriente le voyageur "
            "vers le poste de supervision ou contacte le chef de gare par radio."
        ),
    },
    {
        "title_fragment": "Posture",
        "score": 0.50, "error_type": "reponse_vague", "topic": "Accueil agent",
        "pedagogy_type": "cas_pratique", "days_ago": 2,
        "question": "Un voyageur vous aborde alors que vous êtes en ronde active. Quelle est la procédure ?",
        "user_answer": "Je m'arrête et je l'aide.",
        "expected_answer": "L'agent s'arrête, se présente et propose son aide avant d'attendre la demande.",
        "correction": (
            "La réponse manque de précision : l'agent doit se présenter et proposer "
            "son aide proactivement, pas seulement s'arrêter."
        ),
    },
    {
        "title_fragment": "Posture",
        "score": 0.45, "error_type": "confusion_notion", "topic": "Accueil agent",
        "pedagogy_type": "vrai_faux", "days_ago": 1,
        "question": "Vrai ou Faux : en zone de fort flux, l'agent peut rester stationnaire jusqu'à 10 minutes.",
        "user_answer": "Faux, il doit bouger régulièrement.",
        "expected_answer": "Faux. La limite est de cinq minutes consécutives.",
        "correction": "Correct sur le fond, mais la durée exacte (5 minutes) n'était pas précisée.",
    },
    # ── Section 2 : Perturbations — En consolidation, En retard ──────────────
    {
        "title_fragment": "perturbations",
        "score": 0.60, "error_type": "reponse_vague", "topic": "Gestion des perturbations",
        "pedagogy_type": "question_directe", "days_ago": 5,
        "question": "Dans quel délai l'agent doit-il informer les voyageurs en cas de perturbation ?",
        "user_answer": "Dans les 3 minutes.",
        "expected_answer": "Trois minutes suivant la réception de l'alerte par l'agent.",
        "correction": (
            "Bonne réponse mais incomplète : le délai court à partir de la réception "
            "de l'alerte, pas du début de la perturbation."
        ),
    },
    {
        "title_fragment": "perturbations",
        "score": 0.70, "error_type": None, "topic": "Gestion des perturbations",
        "pedagogy_type": "cas_pratique", "days_ago": 4,
        "question": "Quels éléments doit contenir le message d'information en cas de perturbation ?",
        "user_answer": "La nature de la perturbation, le délai estimé et les alternatives disponibles.",
        "expected_answer": (
            "La nature de la perturbation, l'estimation du délai, "
            "les alternatives disponibles (train suivant, correspondance, remboursement)."
        ),
        "correction": "Réponse complète et correcte.",
    },
    {
        "title_fragment": "perturbations",
        "score": 0.75, "error_type": None, "topic": "Gestion des perturbations",
        "pedagogy_type": "reformulation", "days_ago": 4,
        "question": "Reformulez la règle concernant les estimations de délai que l'agent ne doit pas communiquer.",
        "user_answer": "L'agent ne doit pas donner de délai s'il n'est pas certain de pouvoir le garantir.",
        "expected_answer": "L'agent ne doit jamais communiquer d'estimation de durée qu'il n'est pas en mesure de garantir.",
        "correction": "Reformulation fidèle et complète.",
    },
    # ── Section 3 : PMR — En consolidation, Dans 2 jours ─────────────────────
    {
        "title_fragment": "mobilit",
        "score": 0.65, "error_type": "confusion_notion", "topic": "Assistance PMR",
        "pedagogy_type": "question_piege", "days_ago": 2,
        "question": "Un voyageur PMR arrive sans réservation préalable. L'accompagnement est-il prioritaire ?",
        "user_answer": "Oui, toujours prioritaire.",
        "expected_answer": (
            "L'accompagnement PMR est prioritaire sur toute autre mission sauf urgence de sécurité, "
            "que la réservation soit présente ou non."
        ),
        "correction": (
            "Attention au piège : la priorité s'applique indépendamment de la réservation. "
            "La réponse était correcte mais la justification manquait."
        ),
    },
    {
        "title_fragment": "mobilit",
        "score": 0.80, "error_type": None, "topic": "Assistance PMR",
        "pedagogy_type": "reformulation", "days_ago": 1,
        "question": "Reformulez la règle de délai de prise en charge d'un voyageur PMR réservé.",
        "user_answer": "L'agent doit contacter le voyageur PMR au moins 10 minutes avant le départ.",
        "expected_answer": "L'agent doit prendre contact avec le voyageur PMR au moins dix minutes avant le départ du train.",
        "correction": "Réponse correcte et précise.",
    },
    # ── Section 4 : Traçabilité — Maîtrisé ───────────────────────────────────
    {
        "title_fragment": "abilit",
        "score": 0.85, "error_type": None, "topic": "Traçabilité fin de service",
        "pedagogy_type": "consequence", "days_ago": 8,
        "question": "Quelles sont les conséquences d'un rapport d'activité non validé en fin de service ?",
        "user_answer": "Une alerte automatique est déclenchée auprès du responsable de service.",
        "expected_answer": (
            "Un rapport non validé déclenche automatiquement une alerte auprès du responsable. "
            "L'agent ne peut quitter son poste sans validation ou dérogation explicite du chef de gare."
        ),
        "correction": "Correct sur le déclenchement de l'alerte. La contrainte de départ était en plus.",
    },
    {
        "title_fragment": "abilit",
        "score": 0.90, "error_type": None, "topic": "Traçabilité fin de service",
        "pedagogy_type": "question_directe", "days_ago": 7,
        "question": "Quel document l'agent doit-il compléter en fin de service ?",
        "user_answer": "Le rapport d'activité journalier, avec les assistances PMR, incidents, réclamations et anomalies.",
        "expected_answer": (
            "Le rapport d'activité journalier incluant : assistances PMR réalisées, "
            "incidents signalés, réclamations transmises au service client, anomalies constatées."
        ),
        "correction": "Réponse complète et correcte.",
    },
    {
        "title_fragment": "abilit",
        "score": 0.88, "error_type": None, "topic": "Traçabilité fin de service",
        "pedagogy_type": "cas_pratique", "days_ago": 7,
        "question": "Un agent veut quitter son poste mais son rapport n'est pas validé. Que doit-il faire ?",
        "user_answer": "Il doit valider son rapport ou obtenir une dérogation du chef de gare avant de partir.",
        "expected_answer": (
            "L'agent ne peut quitter son poste sans avoir validé son rapport "
            "ou obtenu une dérogation explicite du chef de gare."
        ),
        "correction": "Réponse correcte et complète.",
    },
]


def seed():
    with sqlite3.connect(DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        if count > 0:
            print(f"Base non vide ({count} tentatives). Seed ignoré.")
            return

        doc = conn.execute("SELECT id FROM documents LIMIT 1").fetchone()
        if not doc:
            print("Aucun document en base. Lance d'abord l'application pour créer la base.")
            return
        doc_id = doc[0]

        inserted = 0
        skipped  = 0
        for a in _ATTEMPTS:
            chunk_id = _get_chunk_id(conn, a["title_fragment"])
            if chunk_id is None:
                print(f"  WARN: chunk non trouvé pour '{a['title_fragment']}' — ignoré")
                skipped += 1
                continue
            conn.execute(
                """
                INSERT INTO attempts
                    (document_id, chunk_id, question, user_answer, expected_answer,
                     correction, score, error_type, topic, pedagogy_type,
                     response_time_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id, chunk_id,
                    a["question"], a["user_answer"], a["expected_answer"],
                    a["correction"], a["score"], a["error_type"],
                    a["topic"], a["pedagogy_type"],
                    round(15 + a["score"] * 20, 1),
                    _days_ago(a["days_ago"]),
                ),
            )
            inserted += 1

        print(f"Seed OK : {inserted} tentatives insérées ({skipped} ignorées).")
        print("Relance l'application : streamlit run app.py")


if __name__ == "__main__":
    seed()
