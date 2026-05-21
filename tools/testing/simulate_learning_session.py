#!/usr/bin/env python
"""
simulate_learning_session.py — TASK-056A
Simulateur de session pédagogique réelle.

Simule 20 questions sur l'utilisateur Guilhem avec de vraies APIs.
Observe le comportement du moteur adaptatif : progression skills, blocages,
évolution types de questions, patterns erreurs, état final du graphe.

Usage (depuis la racine du projet) :
    python tools/testing/simulate_learning_session.py
    python tools/testing/simulate_learning_session.py --no-confirm

IMPORTANT :
- Vraies APIs OpenAI (~35-40 appels, coût réel)
- Données sauvegardées dans la vraie base Guilhem
- Aucun mock, aucune modification de runtime
"""
import argparse
import logging
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

# ── Racine du projet ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

logging.basicConfig(level=logging.WARNING)

# ── Imports projet ────────────────────────────────────────────────────────────
from ai_service import generate_question, correct_answer
from db.analytics import save_attempt
from db.skills import update_user_skill_mastery, get_user_skill_mastery
from db.profile import compute_and_save_learning_profile
from engine.skill_graph import (
    SKILL_GRAPH,
    MASTERY_THRESHOLD,
    get_session_order,
    get_blocking,
    get_full_blocking_chain,
    get_level,
    topological_order,
)
import database as _db

# ── Config ────────────────────────────────────────────────────────────────────
TARGET_USERNAME  = "Guilhem"
N_QUESTIONS      = 20
PROFILE_EVERY    = 10    # recalcul profil toutes les N tentatives
SKILLS_EVERY     = 5     # recalcul skills toutes les N tentatives
API_PAUSE_S      = 1.5   # pause entre appels API (rate limiting)
# Docs à utiliser pour la simulation (éviter doc 5 — score 0.02)
DOCUMENT_IDS     = [1, 2, 3, 4]

SEP  = "-" * 72
SEP2 = "=" * 72

# ── Types de questions et leur difficulté relative ────────────────────────────
_TYPE_DIFFICULTY = {
    "vrai_faux":        1,
    "question_directe": 2,
    "reformulation":    3,
    "cas_pratique":     4,
    "consequence":      4,
    "question_piege":   5,
}
_DIFF_LABEL = {1: "très facile", 2: "facile", 3: "moyen", 4: "difficile", 5: "très difficile"}

# ── Requêtes source variées (orientent le RAG vers des chunks différents) ─────
_SOURCE_QUERIES = [
    "procédure d'accueil et gestion des voyageurs",
    "identification des concepts clés et définitions importantes",
    "application des règles et obligations légales",
    "analyse des causes et conséquences d'une décision",
    "résolution de problèmes dans une situation complexe",
    "conformité réglementaire et normes applicables",
    "processus décisionnel et arbitrage en situation d'urgence",
    "synthèse et reformulation des points principaux",
    "mémorisation des délais, seuils et valeurs réglementaires",
    "évaluation critique d'une procédure ou d'une situation",
]

# ── Pools de réponses simulées ────────────────────────────────────────────────
_ANSWERS_CORRECTES = [
    "La procédure se déroule en plusieurs étapes précises : d'abord l'identification "
    "de la situation, puis l'application du protocole défini, enfin la validation "
    "et la traçabilité de l'action. Chaque étape respecte les délais réglementaires.",
    "Selon le document, il faut d'abord vérifier les conditions préalables, "
    "appliquer les règles en vigueur conformément à l'article concerné, "
    "puis documenter l'action réalisée dans les délais impartis.",
    "Le principe fondamental est que toute situation doit être traitée en suivant "
    "la séquence logique : diagnostic, décision, action, contrôle. "
    "La traçabilité est obligatoire à chaque étape.",
    "La règle applicable prévoit une obligation de résultat. L'agent doit "
    "identifier le problème, appliquer le protocole correspondant, informer "
    "les parties prenantes et consigner l'intervention.",
    "Conformément aux dispositions réglementaires, la procédure impose "
    "une vérification en trois temps : contrôle initial, action corrective, "
    "validation finale. Le délai maximum est fixé par la norme en vigueur.",
]

_ANSWERS_MOYENNES = [
    "Je crois qu'il faut suivre la procédure standard, en vérifiant les conditions "
    "et en appliquant les règles. La traçabilité est importante mais je ne me souviens "
    "pas des délais exacts.",
    "En général, il faut identifier le problème et appliquer le protocole. "
    "Je pense qu'il y a plusieurs étapes mais je ne les connais pas toutes par cœur.",
    "La règle principale est qu'on doit agir conformément aux dispositions légales. "
    "Je sais qu'il y a des délais mais je ne me rappelle plus des chiffres précis.",
    "Il me semble que la procédure implique une vérification préalable, "
    "puis une action. Je ne suis pas sûr de l'ordre exact des étapes.",
    "On doit respecter les obligations légales et documenter les actions. "
    "Je me souviens que c'est important mais les détails m'échappent.",
]

_ANSWERS_VAGUES = [
    "Ça dépend du contexte et de la situation spécifique.",
    "Il faut suivre les règles applicables.",
    "C'est une procédure standard.",
    "On applique le protocole habituel.",
    "Il y a des règles à respecter dans ce cas.",
]

_ANSWERS_NON_EVALUABLE = [
    "je ne sais pas",
    "aucune idée",
    "je ne sais pas du tout",
]

_ANSWERS_HORS_SUJET = [
    "Je pense que la météo joue un rôle important dans ce genre de décision. "
    "En hiver, les conditions climatiques changent tout.",
    "Le football est un sport très populaire en France. "
    "Les règles du jeu sont fixées par la FIFA.",
    "La gastronomie française est reconnue dans le monde entier. "
    "Les recettes varient selon les régions.",
]

# Distribution des 20 types de réponse (indices 0-19)
_RESPONSE_PLAN = [
    "moyenne",        # 0
    "vague",          # 1
    "correcte",       # 2
    "non_evaluable",  # 3
    "moyenne",        # 4
    "hors_sujet",     # 5
    "correcte",       # 6
    "vague",          # 7
    "moyenne",        # 8
    "non_evaluable",  # 9
    "correcte",       # 10
    "hors_sujet",     # 11
    "vague",          # 12
    "moyenne",        # 13
    "correcte",       # 14
    "non_evaluable",  # 15
    "moyenne",        # 16
    "hors_sujet",     # 17
    "vague",          # 18
    "correcte",       # 19
]

_ANSWER_POOLS = {
    "correcte":      _ANSWERS_CORRECTES,
    "moyenne":       _ANSWERS_MOYENNES,
    "vague":         _ANSWERS_VAGUES,
    "non_evaluable": _ANSWERS_NON_EVALUABLE,
    "hors_sujet":    _ANSWERS_HORS_SUJET,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


def _score_bar(score: float, width: int = 10) -> str:
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def _pick_answer(response_type: str, index: int) -> str:
    pool = _ANSWER_POOLS[response_type]
    return pool[index % len(pool)]


def _get_user(username: str) -> Optional[tuple[str, str]]:
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(
            "SELECT user_id, role FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row:
        return row[0], row[1]
    return None


def _get_skill_mastery_dict(user_id: str) -> dict[str, float]:
    rows = get_user_skill_mastery(user_id)
    return {r["slug"]: r["mastery_score"] for r in rows}


def _count_attempts(user_id: str) -> int:
    with sqlite3.connect(_db.DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def _diff_label(q_type: str) -> str:
    d = _TYPE_DIFFICULTY.get(q_type, 0)
    return f"Lv{d} {_DIFF_LABEL.get(d, '?')}"


# ── Rapport final ─────────────────────────────────────────────────────────────

def _print_report(
    user_id:        str,
    attempts_log:   list[dict],
    mastery_before: dict[str, float],
    mastery_after:  dict[str, float],
) -> str:
    # ── 1. Progression des skills ─────────────────────────────────────────────
    _section("RAPPORT — 1. PROGRESSION DES SKILLS")
    topo = topological_order()
    print(f"\n  {'SKILL':<35}  {'AVANT':>7}  {'APRÈS':>7}  {'DELTA':>7}  BAR APRÈS")
    print(f"  {SEP}")
    for slug in topo:
        before = mastery_before.get(slug)
        after  = mastery_after.get(slug)
        delta  = (after or 0.0) - (before or 0.0)
        b_str  = f"{before:.2f}" if before is not None else "  —  "
        a_str  = f"{after:.2f}"  if after  is not None else "  —  "
        d_str  = f"{delta:+.2f}" if (before is not None and after is not None) else "  —  "
        bar    = _score_bar(after or 0.0)
        lvl    = get_level(slug)
        print(f"  Lv{lvl} {slug:<33}  {b_str:>7}  {a_str:>7}  {d_str:>7}  {bar}")

    # ── 2. État du graphe et blocages ─────────────────────────────────────────
    _section("RAPPORT — 2. ÉTAT FINAL DU SKILL GRAPH")
    n_acquis = n_pret = n_bloque = 0
    for slug in topo:
        score = mastery_after.get(slug, 0.0)
        ready = all(
            mastery_after.get(p, 0.0) >= MASTERY_THRESHOLD
            for p in SKILL_GRAPH.get(slug, [])
        )
        mastered = score >= MASTERY_THRESHOLD
        if mastered:
            icon = "[ACQUIS]"
            n_acquis += 1
        elif ready:
            icon = "[PRET]  "
            n_pret += 1
        else:
            icon = "[BLOQUE]"
            n_bloque += 1
        bar   = _score_bar(score)
        lvl   = get_level(slug)
        blocking = get_blocking(slug, mastery_after, MASTERY_THRESHOLD)
        block_str = f"  ← bloqué par: {', '.join(blocking)}" if blocking else ""
        print(f"  Lv{lvl} {icon}  {slug:<35}  {score:.2f}  {bar}{block_str}")

    print(f"\n  Acquis: {n_acquis}  |  Prêts: {n_pret}  |  Bloqués: {n_bloque}")

    # ── 3. Évolution de la difficulté ─────────────────────────────────────────
    _section("RAPPORT — 3. ÉVOLUTION DE LA DIFFICULTÉ")
    print(f"\n  {'#':>3}  {'TYPE':<20}  {'DIFFICULTÉ':<22}  SCORE  TYPE RÉPONSE")
    print(f"  {SEP}")
    for i, a in enumerate(attempts_log, 1):
        qt    = a.get("question_type", "?")
        diff  = _diff_label(qt)
        score = a.get("score")
        s_str = f"{score:.2f}" if score is not None else "  — "
        rtype = a.get("response_type", "?")
        bar   = _score_bar(score or 0.0, width=6)
        print(f"  {i:>3}  {qt:<20}  {diff:<22}  {s_str}  {bar}  [{rtype}]")

    # Tendance difficulté
    diff_scores = [
        (_TYPE_DIFFICULTY.get(a.get("question_type", ""), 0), a.get("score") or 0.0)
        for a in attempts_log
        if a.get("score") is not None
    ]
    if diff_scores:
        avg_diff  = sum(d for d, _ in diff_scores) / len(diff_scores)
        avg_score = sum(s for _, s in diff_scores) / len(diff_scores)
        print(f"\n  Difficulté moyenne : {avg_diff:.1f}/5")
        print(f"  Score moyen        : {avg_score:.2f}")

    # ── 4. Patterns d'erreurs ─────────────────────────────────────────────────
    _section("RAPPORT — 4. PATTERNS D'ERREURS")
    error_types = [a["error_type"] for a in attempts_log if a.get("error_type")]
    counter     = Counter(error_types)
    if counter:
        print(f"\n  {'ERROR TYPE':<30}  OCCURRENCES  BAR")
        print(f"  {SEP}")
        for et, n in counter.most_common():
            bar = "█" * n
            print(f"  {et:<30}  {n:>11}  {bar}")
    else:
        print("\n  Aucun pattern d'erreur détecté (tentatives non évaluables ou correctes).")

    # ── 5. Ordre de session recommandé post-simulation ────────────────────────
    _section("RAPPORT — 5. ORDRE DE SESSION RECOMMANDÉ (ÉTAT FINAL)")
    order = get_session_order(mastery_after, MASTERY_THRESHOLD)
    print(f"\n  {'RANG':>4}  {'SKILL':<35}  ÉTAT        SCORE  LABEL")
    print(f"  {SEP}")
    for i, slug in enumerate(order, 1):
        score    = mastery_after.get(slug, 0.0)
        mastered = score >= MASTERY_THRESHOLD
        ready    = all(
            mastery_after.get(p, 0.0) >= MASTERY_THRESHOLD
            for p in SKILL_GRAPH.get(slug, [])
        )
        tag = "[REVISER] " if mastered else ("[APPRENDRE]" if ready else "[BLOQUE]   ")
        print(f"  {i:>4}  {slug:<35}  {tag}  {score:.2f}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    _section("VERDICT GLOBAL")
    n_attempts = len(attempts_log)
    n_errors   = sum(1 for a in attempts_log if a.get("error_type") not in (None, "", "correct", "non_evaluable"))
    n_non_eval = sum(1 for a in attempts_log if a.get("error_type") == "non_evaluable")

    if n_attempts < N_QUESTIONS:
        verdict = "FAILED"
        detail  = f"Seulement {n_attempts}/{N_QUESTIONS} attempts créés."
    elif n_bloque >= 5:
        verdict = "GO WITH WARNING"
        detail  = f"{n_bloque} skills encore bloqués en fin de session."
    else:
        verdict = "GO SAFE"
        detail  = (
            f"{n_attempts} attempts, {n_non_eval} non-évaluables, "
            f"{n_acquis} skills acquis, {n_pret} prêts, {n_bloque} bloqués."
        )

    icon = {"GO SAFE": "OK", "GO WITH WARNING": "WARNING", "FAILED": "FAILED"}.get(verdict)
    print(f"\n  [{icon}]  {verdict}")
    print(f"          {detail}\n")
    print(SEP2)
    return verdict


# ── Simulation ────────────────────────────────────────────────────────────────

def run_simulation(user_id: str, no_confirm: bool) -> None:
    attempts_before = _count_attempts(user_id)
    mastery_before  = _get_skill_mastery_dict(user_id)

    print(f"\n{SEP2}")
    print(f"  SIMULATE LEARNING SESSION — TASK-056A")
    print(f"  Utilisateur : {TARGET_USERNAME}  ({user_id})")
    print(f"  Attempts existants : {attempts_before}")
    print(f"  Questions à générer : {N_QUESTIONS}")
    print(f"  Documents utilisés : {DOCUMENT_IDS}")
    print(f"  APIs : vraies (OpenAI) — ~35-40 appels")
    print(SEP2)

    if not no_confirm:
        print(f"\n  ATTENTION : cette simulation va :")
        print(f"  - créer {N_QUESTIONS} attempts réels pour {TARGET_USERNAME}")
        print(f"  - appeler l'API OpenAI ~{N_QUESTIONS * 2} fois (coût réel)")
        print(f"  - modifier user_skill_mastery et le profil pédagogique")
        answer = input("\n  Continuer ? [oui/N] : ").strip().lower()
        if answer not in ("oui", "o", "yes", "y"):
            print("  Annulé.")
            return

    attempts_log: list[dict] = []
    scores_by_type: dict[str, list[float]] = defaultdict(list)

    # ── Boucle principale ─────────────────────────────────────────────────────
    print(f"\n  Début de la simulation...\n")
    print(f"  {'#':>3}  {'TYPE_Q':<18}  {'SCORE':>6}  {'ERROR_TYPE':<20}  RÉPONSE")
    print(f"  {SEP}")

    for i in range(N_QUESTIONS):
        query         = _SOURCE_QUERIES[i % len(_SOURCE_QUERIES)]
        response_type = _RESPONSE_PLAN[i]
        answer_text   = _pick_answer(response_type, i)
        attempt_data: dict = {"response_type": response_type}

        # ── Génération de question ─────────────────────────────────────────
        try:
            question, chunk_ids, q_type, rag_chunks = generate_question(
                source_text  = query,
                document_ids = DOCUMENT_IDS,
                user_id      = user_id,
            )
            attempt_data["question_type"] = q_type
            chunk_id  = chunk_ids[0] if chunk_ids else None
            doc_id    = rag_chunks[0].get("document_id") if rag_chunks else None
            source    = rag_chunks[0].get("chunk_text", query)[:500] if rag_chunks else query
        except Exception as e:
            print(f"  {i+1:>3}  [ERREUR génération] {e}")
            attempts_log.append(attempt_data)
            continue

        time.sleep(API_PAUSE_S)

        # ── Correction ────────────────────────────────────────────────────
        try:
            result = correct_answer(question, answer_text, source)
            score      = float(result.get("score", 0.0))
            error_type = result.get("error_type", "")
            topic      = result.get("topic", "")
            correction = result.get("correction", "")
            expected   = result.get("expected_answer", "")
        except Exception as e:
            score      = 0.0
            error_type = "hors_sujet"
            topic      = ""
            correction = ""
            expected   = ""
            print(f"  {i+1:>3}  [ERREUR correction] {e}")

        attempt_data.update({
            "score":      score,
            "error_type": error_type,
            "topic":      topic,
        })

        # ── Sauvegarde attempt ────────────────────────────────────────────
        try:
            save_attempt(
                question              = question,
                user_answer           = answer_text,
                expected_answer       = expected,
                correction            = correction,
                score                 = score,
                response_time_seconds = API_PAUSE_S * 2,
                error_type            = error_type,
                topic                 = topic,
                pedagogy_type         = q_type,
                document_id           = doc_id,
                chunk_id              = chunk_id,
                user_id               = user_id,
            )
        except Exception as e:
            print(f"  {i+1:>3}  [ERREUR save_attempt] {e}")

        attempts_log.append(attempt_data)
        scores_by_type[q_type].append(score)

        # Affichage progression
        diff  = _diff_label(q_type)
        s_str = f"{score:.2f}"
        rshort = response_type[:10]
        bar   = _score_bar(score, width=6)
        print(
            f"  {i+1:>3}  {q_type:<18}  {s_str:>6}  "
            f"{(error_type or ''):<20}  [{rshort:<10}]  {bar}"
        )

        # ── Recalcul périodique des skills ────────────────────────────────
        if (i + 1) % SKILLS_EVERY == 0:
            try:
                update_user_skill_mastery(user_id)
                m = _get_skill_mastery_dict(user_id)
                fragile = [s for s, v in m.items() if v < 0.6]
                print(
                    f"\n  [Skills] Recalcul après Q{i+1} — "
                    f"{sum(1 for v in m.values() if v >= MASTERY_THRESHOLD)} acquis, "
                    f"{len(fragile)} fragiles\n"
                )
            except Exception as e:
                print(f"  [Skills] Erreur recalcul : {e}")

        # ── Recalcul périodique du profil ─────────────────────────────────
        if (i + 1) % PROFILE_EVERY == 0:
            try:
                compute_and_save_learning_profile(user_id)
                print(f"  [Profil] Recalcul après Q{i+1}\n")
            except Exception as e:
                print(f"  [Profil] Erreur recalcul : {e}")

        time.sleep(API_PAUSE_S)

    # ── Recalcul final ────────────────────────────────────────────────────────
    print(f"\n  [Final] Recalcul skills et profil...")
    try:
        update_user_skill_mastery(user_id)
        compute_and_save_learning_profile(user_id)
    except Exception as e:
        print(f"  [Final] Erreur : {e}")

    mastery_after = _get_skill_mastery_dict(user_id)

    # ── Rapport ───────────────────────────────────────────────────────────────
    _print_report(user_id, attempts_log, mastery_before, mastery_after)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulateur de session pédagogique réelle — TASK-056A."
    )
    parser.add_argument(
        "--no-confirm", action="store_true",
        help="Lancer sans confirmation interactive"
    )
    args = parser.parse_args()

    result = _get_user(TARGET_USERNAME)
    if not result:
        print(f"[ERREUR] Utilisateur '{TARGET_USERNAME}' introuvable en base.")
        sys.exit(1)

    user_id, role = result
    print(f"[OK] Utilisateur trouvé : {TARGET_USERNAME} ({user_id})  rôle={role}")

    run_simulation(user_id, no_confirm=args.no_confirm)


if __name__ == "__main__":
    main()
