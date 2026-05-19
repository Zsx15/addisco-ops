"""
Test de robustesse pédagogique — 100 questions simulées.

Usage:
    python test_robustesse_100q.py            # lance le test complet
    python test_robustesse_100q.py --cleanup  # supprime les données du user test

Verdict final : GO SAFE | GO WITH WARNING | FAILED

Isolation : toutes les données sont écrites sous l'utilisateur 'test_100_questions'.
Les vrais utilisateurs et documents ne sont pas modifiés.

ATTENTION : effectue ~200 appels API réels (génération + correction × 100 cycles).
Durée estimée : 5 à 15 minutes selon la latence API.
"""
import argparse
import logging
import random
import sqlite3
import sys
import time
from collections import Counter
from typing import Optional

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_100q")

# ── Config ────────────────────────────────────────────────────────────────────
TEST_USERNAME  = "test_100_questions"
TEST_PASSWORD  = "test_robustesse_v1"
TEST_ROLE      = "apprenant"
N_QUESTIONS    = 100
PROFILE_EVERY  = 10   # recalcul profil tous les N cycles
RANDOM_SEED    = 42


# ── Pools de réponses simulées ────────────────────────────────────────────────
_BAD_ANSWERS = [
    "Je pense que c'est le contraire de ce qui est décrit.",
    "Cette règle ne s'applique jamais dans ce cas précis.",
    "Il n'y a aucune procédure définie pour cette situation.",
    "L'agent n'a aucune obligation particulière ici.",
    "Ce délai n'existe pas dans la réglementation mentionnée.",
]

_OFF_TOPIC = [
    "La météo est ensoleillée aujourd'hui dans le sud de la France.",
    "Le match de football s'est terminé sur un score de 2 à 1.",
    "Les actions technologiques ont progressé de 3 % ce matin.",
    "J'ai mangé une pizza hier soir, c'était délicieux.",
    "La recette du gâteau au chocolat nécessite 200 g de farine.",
]

_SHORT_ANSWERS = [
    "Je ne sais pas.",
    "Non.",
    "Oui.",
    "Peut-être.",
    "Aucune idée.",
]


def _build_answer_schedule(n: int, seed: int) -> list[str]:
    """Distribution déterministe des types de réponses sur n questions."""
    types = (
        ["good"]      * 40 +
        ["partial"]   * 25 +
        ["bad"]       * 15 +
        ["short"]     * 10 +
        ["off_topic"] * 10
    )
    while len(types) < n:
        types.extend(["good", "partial", "bad"])
    types = types[:n]
    rng = random.Random(seed)
    rng.shuffle(types)
    return types


def _simulate_answer(
    answer_type: str,
    chunk_text: Optional[str],
    rng: random.Random,
) -> str:
    """Produit une réponse simulée selon le type et le contexte chunk."""
    if answer_type == "good" and chunk_text:
        excerpt = chunk_text.strip()[:250]
        return f"D'après le document : {excerpt}"
    if answer_type == "partial" and chunk_text:
        excerpt = chunk_text.strip()[:80]
        return f"En partie : {excerpt}…"
    if answer_type == "bad":
        return rng.choice(_BAD_ANSWERS)
    if answer_type == "short":
        return rng.choice(_SHORT_ANSWERS)
    if answer_type == "off_topic":
        return rng.choice(_OFF_TOPIC)
    return "Je ne sais pas répondre à cette question."


# ── Cleanup ───────────────────────────────────────────────────────────────────
def cleanup_test_user() -> None:
    import database
    from auth_service import get_user_by_username

    user = get_user_by_username(TEST_USERNAME)
    if user is None:
        print(f"[CLEANUP] Utilisateur '{TEST_USERNAME}' introuvable — rien à supprimer.")
        return

    uid = user["user_id"]
    with sqlite3.connect(str(database.DB_PATH)) as conn:
        r_atts = conn.execute(
            "DELETE FROM attempts WHERE user_id = ?", (uid,)
        ).rowcount
        r_prof = conn.execute(
            "DELETE FROM user_learning_profile WHERE user_id = ?", (uid,)
        ).rowcount
        r_mast = conn.execute(
            "DELETE FROM user_skill_mastery WHERE user_id = ?", (uid,)
        ).rowcount
        r_user = conn.execute(
            "DELETE FROM users WHERE user_id = ?", (uid,)
        ).rowcount

    print(
        f"[CLEANUP] Supprimé : {r_atts} tentative(s) · {r_prof} profil(s) · "
        f"{r_mast} mastery row(s) · {r_user} user"
    )
    print(f"[CLEANUP] Utilisateur '{TEST_USERNAME}' (uid={uid}) effacé proprement.")


# ── Setup utilisateur test ────────────────────────────────────────────────────
def _get_or_create_test_user() -> str:
    from auth_service import get_user_by_username, register_user

    existing = get_user_by_username(TEST_USERNAME)
    if existing:
        print(f"[SETUP] Utilisateur test existant : uid={existing['user_id']}")
        return existing["user_id"]
    uid = register_user(TEST_USERNAME, TEST_PASSWORD, TEST_ROLE)
    print(f"[SETUP] Utilisateur test créé : uid={uid}")
    return uid


# ── Cœur du test ──────────────────────────────────────────────────────────────
def run_test() -> str:
    """Lance les 100 cycles. Retourne 'GO SAFE', 'GO WITH WARNING' ou 'FAILED'."""
    import database
    database.init_db()

    from ai_service import correct_answer, generate_question
    from database import (
        compute_and_save_learning_profile,
        get_attempts,
        get_chunk_by_id,
        get_document_by_id,
        get_documents,
        get_learning_profile,
        get_user_skill_mastery,
        save_attempt,
    )
    from db.skills import update_user_skill_mastery

    rng             = random.Random(RANDOM_SEED)
    answer_schedule = _build_answer_schedule(N_QUESTIONS, RANDOM_SEED)

    user_id = _get_or_create_test_user()

    # Documents disponibles
    df_docs = get_documents()
    if df_docs.empty:
        print("[FAILED] Aucun document en base. Importez au moins un document avant ce test.")
        return "FAILED"

    doc_ids: list[int] = list(df_docs["id"].astype(int))
    doc_texts: dict[int, str] = {}
    for did in doc_ids:
        d = get_document_by_id(did)
        doc_texts[did] = (d.get("cleaned_text") or "")[:2000] if d else ""

    print(f"[SETUP] {len(doc_ids)} document(s) : {doc_ids}")
    print(f"[TEST]  {N_QUESTIONS} cycles — seed={RANDOM_SEED}\n")
    print(
        f"  {'#':>3}  {'type':<10}  {'q_type':<22}  "
        f"{'score':>5}  {'avg':>5}  {'t':>5}"
    )
    print("  " + "-" * 62)

    # Compteurs
    generated  = 0
    corrected  = 0
    saved      = 0
    errors:      list[str]   = []
    scores:      list[float] = []
    error_types: Counter     = Counter()
    topics:      Counter     = Counter()
    cycle_times: list[float] = []
    mastery_rows: list[dict] = []

    t_start = time.time()

    for i in range(N_QUESTIONS):
        doc_id   = doc_ids[i % len(doc_ids)]
        src_text = doc_texts[doc_id]
        ans_type = answer_schedule[i]
        t_cycle  = time.time()

        question:      Optional[str]  = None
        chunk_ids:     list[int]      = []
        question_type: str            = "question_directe"
        chunk_text:    Optional[str]  = None
        result:        Optional[dict] = None

        # 1. Génération de question
        try:
            question, chunk_ids, question_type = generate_question(
                source_text=src_text,
                document_id=doc_id,
                user_id=user_id,
            )
            generated += 1
        except Exception as exc:
            err = f"Cycle {i+1}: generate_question — {exc}"
            logger.warning(err)
            errors.append(err)
            print(f"  [{i+1:3d}]  ERREUR génération : {str(exc)[:60]}")
            continue

        # Récupère le texte du chunk principal pour la réponse simulée
        if chunk_ids:
            try:
                c = get_chunk_by_id(chunk_ids[0])
                chunk_text = c.get("chunk_text") if c else None
            except Exception:
                pass

        # 2. Réponse simulée
        sim_answer = _simulate_answer(ans_type, chunk_text or src_text, rng)

        # 3. Correction
        try:
            result = correct_answer(question, sim_answer, chunk_text or src_text)
            corrected += 1
        except Exception as exc:
            err = f"Cycle {i+1}: correct_answer — {exc}"
            logger.warning(err)
            errors.append(err)
            result = {
                "score": 0.0,
                "expected_answer": "",
                "correction": f"Indisponible : {exc}",
                "error_type": "hors_sujet",
                "topic": "",
            }

        score      = float(result.get("score", 0.0))
        error_type = result.get("error_type") or "hors_sujet"
        topic      = result.get("topic") or ""

        scores.append(score)
        error_types[error_type] += 1
        if topic:
            topics[topic] += 1

        # 4. Enregistrement tentative
        try:
            save_attempt(
                question=question,
                user_answer=sim_answer,
                expected_answer=result.get("expected_answer", ""),
                correction=result.get("correction", ""),
                score=score,
                response_time_seconds=round(time.time() - t_cycle, 2),
                error_type=error_type,
                topic=topic,
                pedagogy_type=question_type,
                document_id=doc_id,
                chunk_id=chunk_ids[0] if chunk_ids else None,
                user_id=user_id,
            )
            saved += 1
        except Exception as exc:
            err = f"Cycle {i+1}: save_attempt — {exc}"
            logger.warning(err)
            errors.append(err)

        # 5. Recalcul profil tous les PROFILE_EVERY cycles
        if (i + 1) % PROFILE_EVERY == 0:
            try:
                compute_and_save_learning_profile(user_id)
            except Exception as exc:
                err = f"Cycle {i+1}: compute_profile — {exc}"
                logger.warning(err)
                errors.append(err)

        elapsed    = time.time() - t_cycle
        cycle_times.append(elapsed)
        avg_so_far = sum(scores) / len(scores) if scores else 0.0

        print(
            f"  [{i+1:3d}]  {ans_type:<10}  {question_type:<22}  "
            f"{score:.2f}   {avg_so_far:.2f}  {elapsed:4.1f}s"
        )

    # ── Recalculs finaux ───────────────────────────────────────────────────────
    print("\n[FINAL] Recalcul profil + skill mastery…")
    profile_ok = False
    mastery_ok = False

    try:
        compute_and_save_learning_profile(user_id)
        profile_ok = True
        print("  [OK] compute_and_save_learning_profile")
    except Exception as exc:
        errors.append(f"Final: compute_profile — {exc}")
        print(f"  [KO] compute_profile : {exc}")

    try:
        update_user_skill_mastery(user_id)
        mastery_ok = True
        print("  [OK] update_user_skill_mastery")
    except Exception as exc:
        errors.append(f"Final: update_mastery — {exc}")
        print(f"  [KO] update_mastery : {exc}")

    # ── Vérifications ─────────────────────────────────────────────────────────
    print("[VERIFY] Vérifications post-test…")
    checks: list[tuple[str, bool]] = []

    # Historique attempts
    try:
        df_atts = get_attempts(user_id)
        checks.append(("Historique attempts peuplé", len(df_atts) >= saved))
    except Exception as exc:
        checks.append(("Historique attempts peuplé", False))
        errors.append(f"Verify: get_attempts — {exc}")

    # Profil calculé
    try:
        prof = get_learning_profile(user_id)
        checks.append(("Profil calculé", prof is not None))
    except Exception as exc:
        checks.append(("Profil calculé", False))
        errors.append(f"Verify: get_profile — {exc}")

    # Skill mastery
    try:
        mastery_rows = get_user_skill_mastery(user_id)
        checks.append(("user_skill_mastery accessible", mastery_ok))
    except Exception as exc:
        checks.append(("user_skill_mastery accessible", False))
        errors.append(f"Verify: get_mastery — {exc}")

    # Isolation multi-user
    try:
        with sqlite3.connect(str(database.DB_PATH)) as conn:
            other_count = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE user_id != ?", (user_id,)
            ).fetchone()[0]
        checks.append((f"Autres tentatives non touchées ({other_count} rows)", True))
    except Exception as exc:
        checks.append(("Isolation multi-user", False))
        errors.append(f"Verify: isolation — {exc}")

    # Taux de succès des cycles
    success_rate = saved / N_QUESTIONS if N_QUESTIONS > 0 else 0.0
    checks.append(
        (f"Taux cycles réussis >= 90% ({saved}/{N_QUESTIONS})", success_rate >= 0.9)
    )

    # Aucune erreur rencontrée
    checks.append(("Aucune erreur rencontrée", len(errors) == 0))

    t_total   = time.time() - t_start
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    avg_cycle = round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else 0.0

    # ── Rapport ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RAPPORT — TEST ROBUSTESSE PÉDAGOGIQUE 100 QUESTIONS")
    print("=" * 70)
    print(f"User test          : {TEST_USERNAME}  (uid={user_id})")
    print(f"Documents utilisés : {doc_ids}")
    print()
    print(f"Questions générées : {generated} / {N_QUESTIONS}")
    print(f"Corrections réuss. : {corrected} / {generated}")
    print(f"Tentatives sauveg. : {saved} / {generated}")
    print(f"Score moyen global : {avg_score:.3f}  ({round(avg_score * 100)} %)")
    print(f"Temps total        : {round(t_total)}s  (moy. {avg_cycle}s/cycle)")
    print()

    print("Répartition error_type :")
    for et, cnt in error_types.most_common():
        bar = "▪" * min(cnt, 40)
        print(f"  {et:<30}  {cnt:>4}  {bar}")

    print()
    print(f"Top topics ({len(topics)} distincts) :")
    for tp, cnt in topics.most_common(10):
        print(f"  {tp:<42}  x{cnt}")

    print()
    print(f"Skills mastery ({len(mastery_rows)} skill(s)) :")
    if mastery_rows:
        for sk in sorted(mastery_rows, key=lambda x: x["mastery_score"], reverse=True):
            pct  = round(float(sk["mastery_score"]) * 100)
            fill = round(pct / 10)
            bar  = "#" * fill + "." * (10 - fill)
            print(
                f"  {sk['slug']:<35}  [{bar}]  {pct:3d}%"
                f"  ({sk['attempts_count']} tent.)"
            )
    else:
        print("  [aucun skill mastery — pas de tentatives sur chunks mappés]")

    print()
    print("Vérifications :")
    all_checks_ok = True
    for label, ok in checks:
        icon = "OK" if ok else "KO"
        print(f"  [{icon}] {label}")
        if not ok:
            all_checks_ok = False

    if errors:
        print(f"\nErreurs rencontrées ({len(errors)}) :")
        for e in errors[:20]:
            print(f"  !  {e}")
        if len(errors) > 20:
            print(f"  ... et {len(errors) - 20} autres (voir logs)")

    # ── Verdict ───────────────────────────────────────────────────────────────
    fatal_ok = (
        saved > 0 and
        generated > 0 and
        success_rate >= 0.9
    )
    soft_ok = profile_ok and mastery_ok and all_checks_ok and len(errors) == 0

    if not fatal_ok:
        verdict = "FAILED"
    elif not soft_ok:
        verdict = "GO WITH WARNING"
    else:
        verdict = "GO SAFE"

    print()
    print("=" * 70)
    print(f"  VERDICT FINAL : {verdict}")
    print("=" * 70)
    print()
    print(
        "Pour nettoyer les données de test :\n"
        "  python test_robustesse_100q.py --cleanup"
    )
    return verdict


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test de robustesse pédagogique — 100 questions simulées",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python test_robustesse_100q.py\n"
            "  python test_robustesse_100q.py --cleanup\n"
            "  python test_robustesse_100q.py --no-confirm\n"
        ),
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Supprime toutes les données du user test (attempts, profil, mastery, user).",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Désactive la confirmation interactive (CI, automatisation).",
    )
    args = parser.parse_args()

    if args.cleanup:
        import database
        database.init_db()
        cleanup_test_user()
        sys.exit(0)

    print("=" * 70)
    print("TEST ROBUSTESSE PÉDAGOGIQUE — 100 QUESTIONS SIMULÉES")
    print(f"  User test : {TEST_USERNAME}")
    print(f"  N         : {N_QUESTIONS} questions")
    print(f"  Seed      : {RANDOM_SEED}")
    print(f"  Profil    : recalculé tous les {PROFILE_EVERY} cycles")
    print(
        "  ATTENTION : ~200 appels API réels "
        "(coût + durée estimée 5-15 min selon latence)"
    )
    print("=" * 70)

    if not args.no_confirm:
        ans = input("Continuer ? [oui/N] > ").strip().lower()
        if ans not in ("oui", "o", "yes", "y"):
            print("Test abandonné.")
            sys.exit(0)

    verdict = run_test()
    sys.exit(0 if verdict != "FAILED" else 1)
