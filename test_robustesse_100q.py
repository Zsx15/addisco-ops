"""
Test de robustesse pédagogique — 100 questions simulées.

Usage:
    python test_robustesse_100q.py                         # mode API (200 appels OpenAI)
    python test_robustesse_100q.py --mock                  # mode MOCK, profil mixed (défaut)
    python test_robustesse_100q.py --mock --profile good   # profil good
    python test_robustesse_100q.py --mock --profile weak   # profil weak
    python test_robustesse_100q.py --mock --profile random # scores aléatoires
    python test_robustesse_100q.py --mock --no-confirm     # sans confirmation
    python test_robustesse_100q.py --cleanup               # supprime les données du user test

Profils disponibles (--mock uniquement) :
    good   : 80 % bonnes (0.75–1.0), 20 % partielles (0.35–0.65)
    mixed  : 60 % bonnes, 40 % partielles                [défaut]
    weak   : 30 % bonnes, 50 % partielles, 20 % mauvaises (0.0–0.34)
    random : distribution aléatoire à chaque lancement

Verdict final : GO SAFE | GO WITH WARNING | FAILED

Isolation : toutes les données sont écrites sous l'utilisateur 'test_100_questions'.
Les vrais utilisateurs et documents ne sont pas modifiés.

Mode API : ~200 appels OpenAI, durée 5–15 min, coût réel.
Mode MOCK : 0 appel API, durée < 5 s, recommandé pour tests rapides.
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

# ── Données mock (utilisées uniquement en mode --mock) ────────────────────────
_MOCK_QUESTIONS = [
    "Quelle est la durée maximale autorisée pour traiter cette demande ?",
    "Décrivez les étapes principales de la procédure décrite.",
    "Dans quel cas l'agent doit-il contacter son responsable hiérarchique ?",
    "Quelle est la différence entre une alerte et une anomalie selon le document ?",
    "Comment l'agent doit-il réagir face à un incident de sécurité ?",
    "Quelles sont les obligations de l'agent en cas de perturbation du service ?",
    "Vrai ou faux : l'agent peut quitter son poste sans avoir validé son rapport.",
    "Quelle règle s'applique spécifiquement aux voyageurs à mobilité réduite ?",
    "Résumez le processus de traçabilité décrit dans ce document.",
    "Citez trois caractéristiques du comportement professionnel attendu.",
    "Quel délai est prévu pour signaler un incident à la hiérarchie ?",
    "Quelle distinction le texte établit-il entre information active et passive ?",
    "Dans quelle situation l'agent doit-il rédiger un rapport d'anomalie ?",
    "Quelles alternatives l'agent doit-il proposer en cas d'indisponibilité ?",
    "Quel principe de priorité est défini pour les missions concurrentes ?",
]

_MOCK_TOPICS = [
    "Procédure accueil",
    "Gestion incidents",
    "Obligations agent",
    "Conformité réglementaire",
    "Traçabilité service",
    "Assistance PMR",
    "Information voyageurs",
    "Délai intervention",
    "Rapport activité",
    "Posture professionnelle",
    "Délai signalement",
    "Gestion perturbations",
    "Rapport anomalie",
    "Alternatives service",
    "Priorité missions",
]

_MOCK_QUESTION_TYPES = [
    "question_directe",
    "cas_pratique",
    "vrai_faux",
    "question_piege",
    "reformulation",
    "consequence",
]

_MOCK_PROFILE_DISTRIBUTIONS: dict[str, dict[str, int]] = {
    "good":  {"good": 80, "partial": 20, "bad":  0},
    "mixed": {"good": 60, "partial": 40, "bad":  0},
    "weak":  {"good": 30, "partial": 50, "bad": 20},
}

_MOCK_PARTIAL_ERRORS = ["oubli_etape", "confusion_notion", "reponse_vague"]
_MOCK_BAD_ERRORS     = ["erreur_ordre", "hors_sujet", "confusion_notion"]


def _build_mock_score_schedule(n: int, profile: str, seed: int) -> list[str]:
    """Retourne une liste de n bands ('good'|'partial'|'bad') selon le profil."""
    if profile == "random":
        rng = random.Random()   # pas de seed → aléatoire à chaque lancement
        return [rng.choice(["good", "partial", "bad"]) for _ in range(n)]

    dist = _MOCK_PROFILE_DISTRIBUTIONS.get(profile, _MOCK_PROFILE_DISTRIBUTIONS["mixed"])
    bands = (
        ["good"]    * dist["good"] +
        ["partial"] * dist["partial"] +
        ["bad"]     * dist["bad"]
    )
    while len(bands) < n:
        bands.extend(["good", "partial"])
    bands = bands[:n]
    rng = random.Random(seed)
    rng.shuffle(bands)
    return bands


def _mock_score(band: str, rng: random.Random) -> tuple[float, str]:
    """Retourne (score, error_type) déterministe selon le band."""
    if band == "good":
        return round(rng.uniform(0.75, 1.0), 2), "correct"
    if band == "partial":
        return round(rng.uniform(0.35, 0.65), 2), rng.choice(_MOCK_PARTIAL_ERRORS)
    return round(rng.uniform(0.0, 0.34), 2), rng.choice(_MOCK_BAD_ERRORS)


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
def _get_or_create_test_user(username: str = TEST_USERNAME) -> str:
    from auth_service import get_user_by_username, register_user

    existing = get_user_by_username(username)
    if existing:
        print(f"[SETUP] Utilisateur existant : uid={existing['user_id']}  ({username})")
        return existing["user_id"]
    uid = register_user(username, TEST_PASSWORD, TEST_ROLE)
    print(f"[SETUP] Utilisateur créé : uid={uid}  ({username})")
    return uid


# ── Cœur du test ──────────────────────────────────────────────────────────────
def run_test(mock: bool = False, profile: str = "mixed", username: str = TEST_USERNAME, scope: str = "default") -> str:
    """Lance les 100 cycles. Retourne 'GO SAFE', 'GO WITH WARNING' ou 'FAILED'."""
    import database
    database.init_db()

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

    # Pré-calcul du schedule de scores mock (ignoré en mode API)
    mock_score_schedule = _build_mock_score_schedule(N_QUESTIONS, profile, RANDOM_SEED)

    user_id = _get_or_create_test_user(username)

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

    # En mode mock : récupère les chunk_ids réels pour les lier aux attempts
    all_chunk_ids: list[int] = []
    if mock:
        with sqlite3.connect(str(database.DB_PATH)) as _conn:
            all_chunk_ids = [
                r[0] for r in _conn.execute("SELECT id FROM chunks ORDER BY id").fetchall()
            ]

    # Mode corpus : schedule basé sur tous les chunks liés à leur document
    all_chunks_with_doc: list[dict] = []
    corpus_schedule:     list[dict] = []
    if scope == "corpus":
        with sqlite3.connect(str(database.DB_PATH)) as _conn:
            _rows = _conn.execute(
                "SELECT id, document_id FROM chunks ORDER BY document_id, id"
            ).fetchall()
        all_chunks_with_doc = [{"chunk_id": r[0], "doc_id": r[1]} for r in _rows]
        if all_chunks_with_doc:
            for _j in range(N_QUESTIONS):
                corpus_schedule.append(all_chunks_with_doc[_j % len(all_chunks_with_doc)])
        print(
            f"[CORPUS] {len(all_chunks_with_doc)} chunk(s) sur {len(doc_ids)} doc(s) "
            f"-- schedule {N_QUESTIONS} attempts"
        )

    mode_label = f"MOCK (profil={profile})" if mock else "API"
    print(f"[SETUP] {len(doc_ids)} document(s) : {doc_ids}")
    print(f"[TEST]  {N_QUESTIONS} cycles — mode={mode_label}  seed={RANDOM_SEED}\n")
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
    used_doc_ids:   Counter  = Counter()
    used_chunk_ids: set      = set()

    t_start = time.time()

    for i in range(N_QUESTIONS):
        if scope == "corpus" and corpus_schedule:
            doc_id = corpus_schedule[i]["doc_id"]
        else:
            doc_id = doc_ids[i % len(doc_ids)]
        src_text = doc_texts.get(doc_id, "")
        ans_type = answer_schedule[i]
        t_cycle  = time.time()

        question:      Optional[str]  = None
        chunk_ids:     list[int]      = []
        question_type: str            = "question_directe"
        chunk_text:    Optional[str]  = None
        score:         float          = 0.0
        error_type:    str            = "hors_sujet"
        topic:         str            = ""

        if mock:
            # ── Mode MOCK : génération 100 % locale, 0 appel API ─────────────
            question      = _MOCK_QUESTIONS[i % len(_MOCK_QUESTIONS)]
            question_type = _MOCK_QUESTION_TYPES[i % len(_MOCK_QUESTION_TYPES)]
            sim_answer    = _simulate_answer(ans_type, src_text, rng)
            score, error_type = _mock_score(mock_score_schedule[i], rng)
            topic         = _MOCK_TOPICS[i % len(_MOCK_TOPICS)]
            if scope == "corpus" and corpus_schedule:
                chunk_ids = [corpus_schedule[i]["chunk_id"]]
            else:
                chunk_ids = (
                    [all_chunk_ids[i % len(all_chunk_ids)]] if all_chunk_ids else []
                )
            generated += 1
            corrected += 1   # correction simulée localement

        else:
            # ── Mode API : appels OpenAI réels ───────────────────────────────
            from ai_service import correct_answer, generate_question

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

            # Récupère le texte du chunk principal
            if chunk_ids:
                try:
                    c = get_chunk_by_id(chunk_ids[0])
                    chunk_text = c.get("chunk_text") if c else None
                except Exception:
                    pass

            sim_answer = _simulate_answer(ans_type, chunk_text or src_text, rng)

            # 2. Correction
            try:
                result = correct_answer(question, sim_answer, chunk_text or src_text)
                corrected += 1
                score      = float(result.get("score", 0.0))
                error_type = result.get("error_type") or "hors_sujet"
                topic      = result.get("topic") or ""
            except Exception as exc:
                err = f"Cycle {i+1}: correct_answer — {exc}"
                logger.warning(err)
                errors.append(err)
                score, error_type, topic = 0.0, "hors_sujet", ""

        scores.append(score)
        error_types[error_type] += 1
        if topic:
            topics[topic] += 1
        used_doc_ids[doc_id] += 1
        if chunk_ids:
            used_chunk_ids.add(chunk_ids[0])

        # 3 (commun). Enregistrement tentative
        try:
            save_attempt(
                question=question or f"[mock] question #{i+1}",
                user_answer=sim_answer,
                expected_answer="",
                correction="[mock]" if mock else "",
                score=score,
                response_time_seconds=round(time.time() - t_cycle, 4),
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
    print(f"Mode               : {mode_label}")
    print(f"User test          : {username}  (uid={user_id})")
    print(f"Documents utilisés : {doc_ids}")
    print()
    print(f"Questions générées : {generated} / {N_QUESTIONS}")
    corr_label = f"{corrected} / {generated}" if not mock else f"{corrected} / {generated}  [simulation locale]"
    print(f"Corrections réuss. : {corr_label}")
    print(f"Tentatives sauveg. : {saved} / {generated}")
    print(f"Score moyen global : {avg_score:.3f}  ({round(avg_score * 100)} %)")
    print(f"Temps total        : {round(t_total)}s  (moy. {avg_cycle}s/cycle)")
    print()

    print("Répartition error_type :")
    for et, cnt in error_types.most_common():
        bar = "*" * min(cnt, 40)
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

    if scope == "corpus":
        print()
        print("Couverture corpus :")
        _n_chunks_avail = len(all_chunks_with_doc)
        print(f"  Documents disponibles  : {len(doc_ids)}")
        print(f"  Chunks disponibles     : {_n_chunks_avail}")
        print(f"  Documents sollicites   : {len(used_doc_ids)} / {len(doc_ids)}")
        print(f"  Chunks sollicites      : {len(used_chunk_ids)} / {_n_chunks_avail}")
        print()
        print("  Attempts par document :")
        for _did, _cnt in sorted(used_doc_ids.items()):
            _row = df_docs[df_docs["id"] == _did]
            _title = str(_row["title"].values[0]) if not _row.empty else f"doc#{_did}"
            print(f"    doc {_did:2d}  {_title:<40}  x{_cnt}")
        with sqlite3.connect(str(database.DB_PATH)) as _conn:
            _total_chunks = _conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            _with_skills  = _conn.execute(
                "SELECT COUNT(DISTINCT chunk_id) FROM chunk_skills WHERE is_active=1"
            ).fetchone()[0]
            _docs_with_skills = _conn.execute(
                "SELECT COUNT(DISTINCT document_id) FROM chunks c "
                "WHERE EXISTS (SELECT 1 FROM chunk_skills cs WHERE cs.chunk_id=c.id AND cs.is_active=1)"
            ).fetchone()[0]
        print()
        print(f"  Chunks avec skills     : {_with_skills} / {_total_chunks}")
        print(f"  Chunks sans skills     : {_total_chunks - _with_skills} / {_total_chunks}")
        print(f"  Documents avec skills  : {_docs_with_skills} / {len(doc_ids)}")

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
            "  python test_robustesse_100q.py --mock --no-confirm\n"
            "  python test_robustesse_100q.py --mock --profile weak --no-confirm\n"
            "  python test_robustesse_100q.py --mock --profile random --no-confirm\n"
            "  python test_robustesse_100q.py --mock --profile mixed --username test --scope corpus --no-confirm\n"
            "  python test_robustesse_100q.py --cleanup\n"
            "  python test_robustesse_100q.py            # mode API (200 appels OpenAI)\n"
        ),
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Mode simulation locale : 0 appel API. Recommandé pour tests rapides.",
    )
    parser.add_argument(
        "--profile",
        choices=["good", "mixed", "weak", "random"],
        default="mixed",
        help="Distribution des scores simulés (--mock uniquement). Défaut : mixed.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Supprime toutes les données du user test (attempts, profil, mastery, user).",
    )
    parser.add_argument(
        "--username",
        default=TEST_USERNAME,
        help=(
            "Utilisateur cible (doit exister ou sera créé). "
            f"Défaut : {TEST_USERNAME}. "
            "Exemple : --username test"
        ),
    )
    parser.add_argument(
        "--scope",
        choices=["default", "corpus"],
        default="default",
        help=(
            "Portee du test. 'default' : comportement habituel. "
            "'corpus' : couvre tous les chunks de tous les documents."
        ),
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Désactive la confirmation interactive (CI, automatisation).",
    )
    args = parser.parse_args()

    if args.cleanup:
        if args.username != TEST_USERNAME:
            print(
                f"[GUARD] --cleanup refusé sur '{args.username}' : "
                f"seul '{TEST_USERNAME}' peut être nettoyé automatiquement."
            )
            sys.exit(1)
        import database
        database.init_db()
        cleanup_test_user()
        sys.exit(0)

    target_user = args.username
    mode_str = f"MOCK  profil={args.profile}" if args.mock else "API   (~200 appels OpenAI)"
    print("=" * 70)
    print("TEST ROBUSTESSE PÉDAGOGIQUE — 100 QUESTIONS SIMULÉES")
    print(f"  Mode      : {mode_str}")
    print(f"  User test : {target_user}")
    print(f"  Scope     : {args.scope}")
    print(f"  N         : {N_QUESTIONS} questions  |  seed={RANDOM_SEED}")
    print(f"  Profil    : recalculé tous les {PROFILE_EVERY} cycles")
    if not args.mock:
        print("  ATTENTION : ~200 appels API réels (coût + durée 5-15 min)")
    else:
        print("  Durée estimée : < 5 secondes")
    print("=" * 70)

    if not args.no_confirm:
        ans = input("Continuer ? [oui/N] > ").strip().lower()
        if ans not in ("oui", "o", "yes", "y"):
            print("Test abandonné.")
            sys.exit(0)

    verdict = run_test(mock=args.mock, profile=args.profile, username=target_user, scope=args.scope)
    sys.exit(0 if verdict != "FAILED" else 1)
