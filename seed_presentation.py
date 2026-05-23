"""
Seed de présentation POC — TASK-084 / freeze démo.

Crée de façon idempotente :
1. Un compte admin "demo" / "Demo2026!" toujours disponible au démarrage.
2. Des learning_sessions réalistes pour user_id="default" et "demo"
   (alimente l'onglet Analytics dès le premier lancement).
3. Des tentatives pour user_id="demo" (score evolution chart non vide).

Idempotent : chaque bloc vérifie son état avant d'insérer.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from database import DB_PATH

_TODAY = datetime.utcnow()


def _days_ago(n: float) -> str:
    return (_TODAY - timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S")


# ── 1. Compte demo admin ──────────────────────────────────────────────────────

def _seed_demo_user() -> Optional[str]:
    """Crée le user 'demo' (admin) si absent. Retourne son user_id."""
    import uuid
    import bcrypt

    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", ("demo",)
        ).fetchone()
        if row:
            return row[0]
        user_id = str(uuid.uuid4())
        pw_hash = bcrypt.hashpw(b"Demo2026!", bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
            (user_id, "demo", pw_hash, "admin"),
        )
    return user_id


# ── 2. Learning sessions ──────────────────────────────────────────────────────

_SESSIONS_TEMPLATE = [
    # (days_ago_start, duration_min, total_q, completed_q, avg_score, dominant_error)
    (14.5, 18, 5, 5, 0.72, "oubli_etape"),
    (13.2, 8,  3, 3, 0.55, "reponse_vague"),
    (12.0, 22, 7, 7, 0.80, None),
    (11.1, 5,  2, 2, 0.45, "confusion_notion"),
    (9.8,  15, 4, 4, 0.68, "oubli_etape"),
    (8.5,  25, 8, 8, 0.83, None),
    (7.0,  12, 4, 4, 0.75, None),
    (5.9,  6,  2, 1, 0.40, "reponse_vague"),
    (4.3,  20, 6, 6, 0.85, None),
    (3.0,  9,  3, 3, 0.70, "oubli_etape"),
    (1.8,  28, 9, 9, 0.88, None),
    (0.5,  14, 5, 5, 0.82, None),
]


def _seed_sessions_for(user_id: str) -> int:
    """Insère les sessions demo pour user_id si aucune n'existe. Retourne le nb inséré."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        if count > 0:
            return 0

        inserted = 0
        for (d_start, dur_min, total_q, comp_q, avg_s, dom_err) in _SESSIONS_TEMPLATE:
            started  = _days_ago(d_start)
            ended    = (_TODAY - timedelta(days=d_start) + timedelta(minutes=dur_min)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            conn.execute(
                """
                INSERT INTO learning_sessions
                    (user_id, started_at, ended_at, duration_seconds,
                     total_questions, completed_questions, avg_score, dominant_error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, started, ended, dur_min * 60,
                 total_q, comp_q, avg_s, dom_err, started),
            )
            inserted += 1
    return inserted


# ── 3. Tentatives pour user_id="demo" ────────────────────────────────────────

_DEMO_ATTEMPTS = [
    # (days_ago, score, error_type, topic, pedagogy_type, q, user_ans, exp_ans)
    (14, 0.40, "oubli_etape",    "Accueil agent",    "question_directe",
     "Quel est le délai maximal pour répondre à un voyageur ?",
     "L'agent doit répondre rapidement.", "Deux minutes maximum."),
    (13, 0.70, "reponse_vague",  "Perturbations",    "cas_pratique",
     "Que faire lors d'une perturbation grave ?",
     "Prévenir la hiérarchie et aider les voyageurs.",
     "Déclencher le PMR, informer le régulateur, guider les voyageurs vers les solutions alternatives."),
    (12, 0.90, None,             "PMR",              "vrai_faux",
     "Le PMR doit être activé avant tout contact voyageur.",
     "Faux — sauf en cas de situation d'urgence immédiate.",
     "Faux — le contact voyageur prime en situation non urgente."),
    (11, 0.55, "confusion_notion","Traçabilité",     "reformulation",
     "Expliquez la traçabilité en cas d'incident.",
     "On note tout dans le registre.", "Enregistrement horodaté dans le système SATIN avec motif, mesures, résolution."),
    (9,  0.80, None,             "Accueil agent",    "question_piege",
     "Un agent peut-il refuser de renseigner un voyageur agressif ?",
     "Non, l'agent doit toujours renseigner.", "Non, mais il peut activer le signal d'alarme et demander du renfort."),
    (8,  0.85, None,             "PMR",              "consequence",
     "Quelles sont les conséquences d'un PMR non activé lors d'une évacuation ?",
     "Risque de blessure et sanctions disciplinaires.", "Risques corporels, responsabilité pénale de l'agent et procédure d'enquête interne."),
    (7,  0.75, None,             "Perturbations",    "question_directe",
     "Qui est le premier interlocuteur lors d'une perturbation réseau ?",
     "Le régulateur de la ligne.", "Le régulateur de la ligne — appel obligatoire dans les 3 minutes."),
    (5,  0.60, "oubli_etape",    "Traçabilité",      "cas_pratique",
     "Un voyageur signale un objet suspect. Décrivez votre procédure.",
     "Appeler la police et évacuer.", "Périmètre de sécurité, appel sûreté SNCF, évacuation progressive, traçabilité immédiate."),
    (4,  0.90, None,             "Accueil agent",    "vrai_faux",
     "L'agent peut utiliser son téléphone personnel pour signaler un incident.",
     "Faux — uniquement les équipements professionnels.",
     "Faux — utilisation obligatoire des équipements radio et téléphone professionnel."),
    (3,  0.88, None,             "PMR",              "reformulation",
     "Résumez le rôle du PMR en trois points.",
     "Alerte, coordination, traçabilité.",
     "1. Déclencher l'alerte réseau. 2. Coordonner les intervenants. 3. Assurer la traçabilité de l'événement."),
    (2,  0.85, None,             "Perturbations",    "question_directe",
     "Dans quel délai l'agent doit-il rédiger le compte-rendu d'incident ?",
     "Avant la fin de son service.", "Dans les 2 heures suivant la fin de l'incident, avant fin de service."),
    (1,  0.92, None,             "Traçabilité",      "cas_pratique",
     "Un voyageur se plaint d'un mauvais traitement d'un collègue. Comment traitez-vous ?",
     "Écouter, noter, transmettre au responsable.",
     "Écouter sans jugement, noter les faits dans SATIN, transmettre au chef de gare sous 1h, proposer médiation si souhaité."),
]


def _seed_attempts_for_demo(user_id: str) -> int:
    """Insère les tentatives demo pour user_id si aucune n'existe. Retourne le nb inséré."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        if count > 0:
            return 0

        doc = conn.execute("SELECT id FROM documents LIMIT 1").fetchone()
        if not doc:
            return 0
        doc_id = doc[0]

        inserted = 0
        for (days, score, err, topic, ptype, q, ua, ea) in _DEMO_ATTEMPTS:
            conn.execute(
                """
                INSERT INTO attempts
                    (user_id, document_id, question, user_answer, expected_answer,
                     correction, score, error_type, topic, pedagogy_type,
                     response_time_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, doc_id, q, ua, ea,
                    "Correction automatique simulée — données de démonstration.",
                    score, err, topic, ptype,
                    round(15 + (1 - score) * 25, 1),
                    _days_ago(days),
                ),
            )
            inserted += 1
    return inserted


# ── Entrée principale ─────────────────────────────────────────────────────────

def seed_presentation() -> None:
    """Point d'entrée — appelé par app.py au démarrage."""
    try:
        demo_uid = _seed_demo_user()
        _seed_sessions_for("default")
        _seed_sessions_for(demo_uid)
        _seed_attempts_for_demo(demo_uid)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("seed_presentation failed silently: %s", exc)


if __name__ == "__main__":
    seed_presentation()
    print("Seed présentation OK.")
